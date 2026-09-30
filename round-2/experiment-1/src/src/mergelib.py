"""Pair features for the variant merger (used by s4 training, s5 linker gate and s7 frame merging)."""
from __future__ import annotations

import re

import numpy as np
from rapidfuzz import fuzz

from common import _best_long_form, match_form, normalise
from featlib import EmbStore, emb_text

PAIR_NAMES = ["cos_minilm", "cos_specter2", "char3_jaccard", "token_jaccard", "fz_token_set", "fz_token_sort", "fz_ratio",
              "norm_equal", "head_equal", "containment", "len_ratio", "abs_diff_ntok", "digit_mismatch", "acronym_match"]
DIGITS = re.compile(r"\d+")


def _char3(s: str) -> set:
    s = f"  {s} "
    return {s[i:i + 3] for i in range(len(s) - 2)}


def _is_short(s: str) -> bool:
    t = s.strip()
    if " " in t or len(t) > 8 or len(t) < 2:
        return False
    up = sum(c.isupper() for c in t)
    return up >= 2 or len(t) <= 5


def acronym_match(a: str, b: str) -> float:
    for s, l in ((a, b), (b, a)):
        if _is_short(s) and len(l.split()) >= 2:
            letters = [c.lower() for c in s if c.isalnum()]
            init = [w[0].lower() for w in re.split(r"[\s\-/]+", l) if w]
            if letters == init[:len(letters)] and len(letters) == len(init):
                return 1.0
            try:
                if _best_long_form(s, l) is not None:
                    return 1.0
            except IndexError:
                pass
    return 0.0


class PairFeaturizer:
    def __init__(self, mini: EmbStore | None = None, spec: EmbStore | None = None) -> None:
        self.mini = mini or EmbStore("minilm")
        self.spec = spec or EmbStore("specter2")

    def _key(self, x: str) -> str:
        """Embedding key: emb_text(x); strings that are already emb_text forms (index targets) are used as-is,
        because textnorm.normalise is not idempotent for a few spellings (e.g. 'analyse' -> 'analyze')."""
        k = emb_text(x)
        if self.mini.has(k) and self.spec.has(k):
            return k
        return x if (self.mini.has(x) and self.spec.has(x)) else k

    def lexical(self, a: str, b: str) -> list[float]:
        na, nb = normalise(a), normalise(b)
        ma, mb = match_form(a), match_form(b)
        ta, tb = set(ma.split()), set(mb.split())
        ca, cb = _char3(ma), _char3(mb)
        cj = len(ca & cb) / len(ca | cb) if ca | cb else 0.0
        tj = len(ta & tb) / len(ta | tb) if ta | tb else 0.0
        head = float(bool(ma) and bool(mb) and ma.split()[-1] == mb.split()[-1])
        cont = float((ta < tb) or (tb < ta))
        lr = min(len(na), len(nb)) / max(1, max(len(na), len(nb)))
        dn = abs(len(na.split()) - len(nb.split()))
        dm = float(set(DIGITS.findall(na)) != set(DIGITS.findall(nb)))
        return [cj, tj, fuzz.token_set_ratio(na, nb) / 100, fuzz.token_sort_ratio(na, nb) / 100, fuzz.ratio(na, nb) / 100,
                float(na == nb or ma == mb), head, cont, lr, float(dn), dm, acronym_match(a, b)]

    def features(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        if not pairs:
            return np.zeros((0, len(PAIR_NAMES)), dtype=np.float32)
        A = [self._key(a) for a, _ in pairs]
        B = [self._key(b) for _, b in pairs]
        cm = np.einsum("ij,ij->i", self.mini.get(A), self.mini.get(B))
        cs = np.einsum("ij,ij->i", self.spec.get(A), self.spec.get(B))
        lex = np.array([self.lexical(a, b) for a, b in pairs], dtype=np.float32)
        return np.concatenate([cm[:, None], cs[:, None], lex], axis=1).astype(np.float32)
