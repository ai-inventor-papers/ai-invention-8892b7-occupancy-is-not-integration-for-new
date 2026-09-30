"""Shared phrase cleaning, normalisation and Schwartz-Hearst acronym extraction."""
from __future__ import annotations

import re
import unicodedata

STOP_MODIFIERS = {
    "novel", "new", "proposed", "our", "significant", "different", "various", "several", "present", "current",
    "previous", "high", "low", "other", "such", "same", "many", "few", "more", "most", "less", "further",
    "first", "second", "third", "main", "major", "important", "specific", "particular", "certain",
    "possible", "potential", "overall", "total", "recent", "additional", "respective", "corresponding",
    "similar", "given", "large", "small", "good", "better", "best", "higher", "lower", "greater", "key",
    "effective", "efficient", "simple", "useful", "typical", "common", "whole", "entire", "both", "each",
    "every", "all", "any", "some", "this", "that", "these", "those", "its", "their", "his", "her", "we",
    "existing", "conventional", "traditional", "standard", "relevant", "appropriate", "considerable",
    "substantial", "strong", "weak", "positive", "negative", "significantly", "relatively", "very",
    "much", "only", "own", "certain", "individual", "separate", "distinct", "numerous", "multiple",
}
GREEK = {"α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon", "ζ": "zeta", "η": "eta",
         "θ": "theta", "κ": "kappa", "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "π": "pi", "ρ": "rho",
         "σ": "sigma", "τ": "tau", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega", "Δ": "delta",
         "Γ": "gamma", "Ω": "omega", "Φ": "phi", "Ψ": "psi", "Σ": "sigma", "Λ": "lambda", "Θ": "theta"}
BRIT = {"tumour": "tumor", "behaviour": "behavior", "colour": "color", "haemoglobin": "hemoglobin",
        "anaemia": "anemia", "oestrogen": "estrogen", "paediatric": "pediatric", "optimisation": "optimization",
        "modelling": "modeling", "characterisation": "characterization", "organisation": "organization",
        "localisation": "localization", "stabilisation": "stabilization", "polarisation": "polarization",
        "haemorrhage": "hemorrhage", "leukaemia": "leukemia", "oesophageal": "esophageal", "fibre": "fiber",
        "centre": "center", "aluminium": "aluminum", "sulphur": "sulfur", "sulphate": "sulfate",
        "analyse": "analyze", "ageing": "aging", "labour": "labor", "neighbour": "neighbor",
        "haematopoietic": "hematopoietic", "anaesthesia": "anesthesia", "ischaemic": "ischemic",
        "oedema": "edema", "foetal": "fetal", "caesarean": "cesarean", "programme": "program"}
UNIT_RE = re.compile(r"^(\d+([.,]\d+)?|[a-z]?\d+[a-z]{0,3}|mg|kg|ml|mm|cm|nm|μm|km|hz|khz|mhz|ghz|kda|ppm|%|°c|°)$", re.I)
HYPHEN_RE = re.compile(r"[‐-―−/_]+|-")
SPACE_RE = re.compile(r"\s+")
NONWORD_EDGE = re.compile(r"^[^\w]+|[^\w+)\]]+$")


def plural_to_singular(w: str) -> str:
    """Tiny rule-based singulariser for the head token (keeps keys deterministic across processes)."""
    if len(w) <= 3 or not w.isalpha():
        return w
    if w.endswith(("ss", "us", "is", "ics", "sis", "xis")):
        return w
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ches", "shes", "xes", "zes", "sses")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def normalise(surface: str) -> str:
    s = unicodedata.normalize("NFKC", surface)
    for g, name in GREEK.items():
        if g in s:
            s = s.replace(g, f" {name} ")
    s = s.lower()
    s = HYPHEN_RE.sub(" ", s)
    s = s.replace("'s ", " ").replace("’s ", " ")
    s = re.sub(r"[\"“”‘’`,;:!?]", " ", s)
    s = SPACE_RE.sub(" ", s).strip()
    toks = [BRIT.get(t, t) for t in s.split(" ") if t]
    if not toks:
        return ""
    toks[-1] = plural_to_singular(toks[-1])
    return " ".join(toks)


def clean_chunk(tokens: list[tuple[str, str, str]]) -> list[str] | None:
    """tokens: list of (text, pos, tag). Strips leading determiners/numbers/stop-modifiers.
    Returns token texts or None if the chunk should be dropped."""
    # drop parenthesised material, e.g. "centipede (Chilopoda) community" -> "centipede community"
    if any(t[0] in ("(", ")", "[", "]") for t in tokens):
        kept, depth = [], 0
        for tok in tokens:
            if tok[0] in ("(", "["):
                depth += 1
                continue
            if tok[0] in (")", "]"):
                depth = max(0, depth - 1)
                continue
            if depth == 0:
                kept.append(tok)
        tokens = kept
    i = 0
    while i < len(tokens):
        t, pos, tag = tokens[i]
        tl = t.lower()
        if pos in ("DET", "PRON", "NUM", "PUNCT", "SYM", "ADP", "CCONJ", "PART", "AUX", "SCONJ") or tag == "POS" \
                or tl in STOP_MODIFIERS or UNIT_RE.match(tl):
            i += 1
            continue
        break
    toks = tokens[i:]
    while toks and (toks[-1][1] in ("PUNCT", "SYM", "PART") or toks[-1][2] == "POS"):
        toks = toks[:-1]
    if not toks or len(toks) > 6:
        return None
    words = [t for t, _, _ in toks]
    if not any(any(c.isalpha() for c in w) and len(w) > 1 for w in words):
        return None
    if all(UNIT_RE.match(w.lower()) or not any(c.isalpha() for c in w) for w in words):
        return None
    if toks[-1][1] not in ("NOUN", "PROPN", "X", "ADJ"):
        return None
    if any(t[1] == "PRON" for t in toks):
        return None
    return words


# ---------------- Schwartz & Hearst (2003) abbreviation definitions ----------------
PAREN_RE = re.compile(r"\(([^()]{1,20})\)")


def _valid_short(sf: str) -> bool:
    if len(sf) < 2 or len(sf) > 10 or len(sf.split()) > 2:
        return False
    if not any(c.isalpha() for c in sf):
        return False
    if not sf[0].isalnum() or sf.endswith("."):
        return False
    if not any(c.isupper() for c in sf):
        return False
    return True


def _best_long_form(sf: str, lf: str) -> str | None:
    s_idx = len(sf) - 1
    l_idx = len(lf) - 1
    while s_idx >= 0:
        c = sf[s_idx].lower()
        if not c.isalnum():
            s_idx -= 1
            continue
        while (l_idx >= 0 and lf[l_idx].lower() != c) or (s_idx == 0 and l_idx > 0 and lf[l_idx - 1].isalnum()):
            l_idx -= 1
        if l_idx < 0:
            return None
        l_idx -= 1
        s_idx -= 1
    l_idx = lf.rfind(" ", 0, l_idx + 1) + 1
    return lf[l_idx:]


def schwartz_hearst(sentence: str) -> list[tuple[str, str]]:
    """Return (short_form, long_form) pairs defined as 'long form (SF)' in a sentence."""
    out = []
    for m in PAREN_RE.finditer(sentence):
        sf = m.group(1).strip()
        sf = sf.split(";")[0].split(",")[0].strip()
        if not _valid_short(sf):
            continue
        before = sentence[:m.start()].rstrip()
        words = before.split()
        if not words:
            continue
        max_words = min(len(sf) + 5, len(sf) * 2)
        cand = " ".join(words[-max_words:])
        lf = _best_long_form(sf, cand)
        if not lf:
            continue
        lf = lf.strip()
        n_lf = len(lf.split())
        if lf and len(lf) > len(sf) and n_lf <= max_words and sf.lower() not in lf.lower().split():
            lf = NONWORD_EDGE.sub("", lf)
            if lf and lf[0].isalnum():
                out.append((sf, lf))
    return out
