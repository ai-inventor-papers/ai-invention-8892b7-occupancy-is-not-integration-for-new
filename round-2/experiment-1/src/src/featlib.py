"""Phrase-level lexical features, computed identically for D2, D4a and frame phrases, and the embedding store."""
from __future__ import annotations

import json
import re
from collections import Counter

import numpy as np

from common import WORK, normalise

GENERIC_HEADS = set("""
method approach system study analysis model effect technique process result data application performance
problem framework algorithm structure property function behavior mechanism strategy design development
evaluation investigation measurement characterization assessment comparison scheme procedure tool technology
theory concept factor parameter condition feature role impact influence change increase decrease level rate
value number amount type form kind case example group set part area region field domain aspect issue question
task work research paper article review report experiment test trial observation simulation computation
calculation estimation prediction detection identification classification recognition representation
formulation solution implementation optimization control management treatment therapy intervention outcome
response activity interaction relationship relation correlation association difference similarity distribution
pattern trend variation variability dynamics evolution growth formation generation production synthesis
preparation modification improvement enhancement reduction limitation challenge advantage benefit risk cost
quality efficiency accuracy capability ability potential status state phase stage step period time year
condition environment material sample specimen object component element unit device instrument equipment
network model technique protocol platform service product resource information knowledge evidence finding
estimate measure index indicator score metric criterion standard principle rule law equation expression term
""".split())
PREP = {"ADP"}
DET = {"DET"}
CONJ = {"CCONJ", "SCONJ"}
VERB = {"VERB", "AUX"}
GREEK_RE = re.compile(r"[Ͱ-Ͽ]|\b(alpha|beta|gamma|delta|epsilon|kappa|lambda|sigma|theta|omega|mu|pi|tau|phi|psi|chi)\b")
SYMBOL_RE = re.compile(r"[^\w\s\-/.,()']")
NONLATIN_RE = re.compile(r"[^\x00-\x7fÀ-ɏͰ-Ͽ‐-―]")
BOILER_RE = re.compile(r"©|all rights reserved|elsevier|springer|wiley|periodical|copyright|\blicensee\b|published by")


def is_acronym_token(t: str) -> bool:
    letters = [c for c in t if c.isalpha()]
    if not letters or len(t) > 6:
        return False
    up = sum(c.isupper() for c in letters)
    return up >= 2 or (up >= 1 and len(letters) <= 3 and t[0].isupper() and any(c.isdigit() for c in t))


class LexicalFeaturizer:
    """Fit the POS-pattern vocabulary on D2-train only; then transform any phrase."""

    def __init__(self) -> None:
        import spacy
        from spacy.lang.en.stop_words import STOP_WORDS
        from wordfreq import zipf_frequency
        self.nlp = spacy.load("en_core_web_sm", disable=["parser", "ner", "lemmatizer"])
        self.stop = STOP_WORDS
        self.zipf = zipf_frequency
        self.patterns: list[str] = []
        self._pos_cache: dict[str, list[str]] = {}

    def pos(self, keys: list[str]) -> None:
        todo = [k for k in dict.fromkeys(keys) if k not in self._pos_cache]
        for k, doc in zip(todo, self.nlp.pipe(todo, batch_size=1024)):
            self._pos_cache[k] = [t.pos_ for t in doc]

    def fit_patterns(self, keys: list[str], top: int = 25) -> None:
        self.pos(keys)
        c = Counter("_".join(self._pos_cache[k]) for k in keys)
        self.patterns = [p for p, _ in c.most_common(top)]

    def names(self) -> list[str]:
        return (["lx_n_tokens", "lx_n_chars", "lx_stop_share", "lx_first_prep", "lx_first_det", "lx_first_conj",
                 "lx_first_verb", "lx_last_prep", "lx_last_det", "lx_last_conj", "lx_last_verb", "lx_head_pos",
                 "lx_acronym", "lx_has_digit", "lx_has_greek_symbol", "lx_zipf_min", "lx_zipf_mean",
                 "lx_generic_head", "lx_key_malformed"] + [f"lx_pos_{p}" for p in self.patterns] + ["lx_pos_OTHER"])

    def transform(self, key: str, surface_forms: list[str] | None = None, acronyms: list[str] | None = None) -> list[float]:
        """key: the normalised phrase key (lower case). surface_forms keep case for the acronym flag."""
        if key not in self._pos_cache:
            self.pos([key])
        pos = self._pos_cache[key]
        toks = key.split()
        n = max(1, len(toks))
        stop_share = sum(t in self.stop for t in toks) / n
        f0 = pos[0] if pos else ""
        fl = pos[-1] if pos else ""
        noun_idx = [i for i, p in enumerate(pos) if p in ("NOUN", "PROPN")]
        head_pos = (noun_idx[-1] + 1) / max(1, len(pos)) if noun_idx else 0.0
        sfs = list(surface_forms or []) + [key]
        acro = float(bool(acronyms) or any(is_acronym_token(t) for s in sfs for t in re.split(r"[\s\-/]+", s)))
        zs = [self.zipf(t, "en") for t in toks] or [0.0]
        head = toks[-1] if toks else ""
        malformed = float(bool(key) and (not key[0].isalnum() or bool(NONLATIN_RE.search(key)) or bool(BOILER_RE.search(key))))
        pat = "_".join(pos)
        onehot = [float(pat == p) for p in self.patterns] + [float(pat not in self.patterns)]
        return [float(len(toks)), float(len(key)), stop_share, float(f0 in PREP), float(f0 in DET), float(f0 in CONJ),
                float(f0 in VERB), float(fl in PREP), float(fl in DET), float(fl in CONJ), float(fl in VERB), head_pos,
                acro, float(any(c.isdigit() for c in key)), float(bool(GREEK_RE.search(" ".join(sfs)) or SYMBOL_RE.search(key))),
                float(min(zs)), float(np.mean(zs)), float(head in GENERIC_HEADS), malformed] + onehot


class EmbStore:
    """String -> row lookup into cache/emb/{name}.npy (float16, L2-normalised)."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.strings = json.loads((WORK / "emb" / f"{name}_strings.json").read_text())
        self.idx = {s: i for i, s in enumerate(self.strings)}
        self.mat = np.asarray(np.load(WORK / "emb" / f"{name}.npy"))
        self.extra: dict[str, np.ndarray] = {}

    def get(self, strings: list[str]) -> np.ndarray:
        miss = [s for s in strings if s not in self.idx and s not in self.extra]
        if miss:
            raise KeyError(f"{self.name}: {len(miss)} strings not embedded, e.g. {miss[:3]}")
        return np.stack([self.mat[self.idx[s]].astype(np.float32) if s in self.idx else self.extra[s] for s in strings]) \
            if strings else np.zeros((0, self.mat.shape[1]), dtype=np.float32)

    def has(self, s: str) -> bool:
        return s in self.idx or s in self.extra

    def add(self, strings: list[str], M: np.ndarray) -> None:
        for s, v in zip(strings, M):
            self.extra[s] = v.astype(np.float32)


def emb_text(s: str) -> str:
    """The exact string given to the encoders for a phrase: normalised key (lower case, hyphens as spaces)."""
    return normalise(s) or s.lower().strip()
