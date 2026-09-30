#!/usr/bin/env python3
"""Steps 1-4: parse MeSH files, select new topical descriptors (2006-2016),
assign provenance classes, build matchable surface forms and the synonym-pair set.

Inputs (raw/): desc2017.xml.gz, desc2026.xml.gz, d2005..d2016.bin (ASCII MeSH), replace2005..2016.txt
Outputs (temp/): mesh_all_2017.json (light table of every 2017 descriptor),
                 candidates.json (all 2006-2016 topical candidates with provenance class + forms),
                 flow_step1_4.json (selection-flow counts)
                 mesh_synonym_pairs.json (workspace root)
"""
from __future__ import annotations

import gzip
import itertools
import json
import random
import re
import resource
import sys
from collections import Counter, defaultdict
from pathlib import Path

from loguru import logger
from lxml import etree
from wordfreq import zipf_frequency

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw"
TEMP = ROOT / "temp"
TEMP.mkdir(exist_ok=True)
(ROOT / "logs").mkdir(exist_ok=True)

logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "s01_mesh.log", rotation="30 MB", level="DEBUG")

resource.setrlimit(resource.RLIMIT_AS, (12 * 1024**3, 12 * 1024**3))

import os
EST_MIN, EST_MAX = 2006, 2016
# Widening (plan failure scenario): AII_TAG=w1 AII_YEARS=2004,2005 AII_SNAPSHOT=desc2017.xml.gz
#                                   AII_TAG=w2 AII_YEARS=2017,2018 AII_SNAPSHOT=desc2019.xml.gz
TAG = os.environ.get("AII_TAG", "")
SUF = f"_{TAG}" if TAG else ""
EST_YEARS = [int(y) for y in os.environ["AII_YEARS"].split(",")] if os.environ.get("AII_YEARS") else list(range(EST_MIN, EST_MAX + 1))
SNAPSHOT = os.environ.get("AII_SNAPSHOT", "desc2017.xml.gz")
GENERIC_ZIPF = 4.0
PAIR_CAP_POS = 40          # max positive pairs per descriptor
SIB_NEG_PER_DESC = 4       # sibling-descriptor hard negatives per descriptor
SEED = 20260928


def _txt(el, path: str) -> str | None:
    x = el.find(path)
    return x.text.strip() if x is not None and x.text else None


def _date(el, tag: str) -> str | None:
    d = el.find(tag)
    if d is None:
        return None
    return f"{_txt(d, 'Year')}-{_txt(d, 'Month')}-{_txt(d, 'Day')}"


def parse_desc_xml(path: Path, full: bool) -> dict[str, dict]:
    """Stream-parse a MeSH descriptor XML file. full=False only keeps UI + name."""
    out: dict[str, dict] = {}
    with gzip.open(path, "rb") as fh:
        for _, el in etree.iterparse(fh, events=("end",), tag="DescriptorRecord"):
            ui = _txt(el, "DescriptorUI")
            name = _txt(el, "DescriptorName/String")
            if not full:
                out[ui] = {"name": name}
            else:
                concepts = []
                for c in el.iterfind("ConceptList/Concept"):
                    terms = []
                    for t in c.iterfind("TermList/Term"):
                        terms.append({
                            "s": _txt(t, "String"),
                            "permuted": t.get("IsPermutedTermYN") == "Y",
                            "lex": t.get("LexicalTag"),
                            "cpt_pref": t.get("ConceptPreferredTermYN") == "Y",
                            "thes": [x.text for x in t.iterfind("ThesaurusIDlist/ThesaurusID") if x.text],
                        })
                    rels = [{"rel": r.get("RelationName"), "c1": _txt(r, "Concept1UI"), "c2": _txt(r, "Concept2UI")}
                            for r in c.iterfind("ConceptRelationList/ConceptRelation")]
                    concepts.append({
                        "cui": _txt(c, "ConceptUI"),
                        "preferred": c.get("PreferredConceptYN") == "Y",
                        "name": _txt(c, "ConceptName/String"),
                        "terms": terms,
                        "rels": rels,
                    })
                out[ui] = {
                    "ui": ui,
                    "name": name,
                    "cls": el.get("DescriptorClass"),
                    "est": _date(el, "DateEstablished"),
                    "created": _date(el, "DateCreated"),
                    "hn": (_txt(el, "HistoryNote") or "").replace("\n", " ").strip(),
                    "pmn": (_txt(el, "PublicMeSHNote") or "").replace("\n", " ").strip(),
                    "prev_idx": [x.text for x in el.iterfind("PreviousIndexingList/PreviousIndexing") if x.text],
                    "trees": [x.text for x in el.iterfind("TreeNumberList/TreeNumber") if x.text],
                    "concepts": concepts,
                }
            el.clear()
            while el.getprevious() is not None:
                del el.getparent()[0]
    return out


def parse_ascii(path: Path) -> tuple[dict[str, set[str]], dict[str, str]]:
    """ASCII MeSH d{YEAR}.bin -> (lower-cased term -> {UI}, UI -> MH)."""
    term2ui: dict[str, set[str]] = defaultdict(set)
    ui2mh: dict[str, str] = {}
    mh, terms, ui = None, [], None
    with path.open("r", encoding="latin-1") as fh:
        for line in fh:
            if line.startswith("*NEWRECORD"):
                if ui:
                    ui2mh[ui] = mh
                    for t in terms + [mh]:
                        if t:
                            term2ui[t.lower()].add(ui)
                mh, terms, ui = None, [], None
            elif line.startswith("MH = "):
                mh = line[5:].strip()
            elif line.startswith("ENTRY = ") or line.startswith("PRINT ENTRY = "):
                terms.append(line.split(" = ", 1)[1].split("|")[0].strip())
            elif line.startswith("UI = "):
                ui = line[5:].strip()
    if ui:
        ui2mh[ui] = mh
        for t in terms + [mh]:
            if t:
                term2ui[t.lower()].add(ui)
    return term2ui, ui2mh


def parse_replace(path: Path) -> list[tuple[str, str]]:
    pairs, old = [], None
    for line in path.read_text(encoding="latin-1").splitlines():
        if line.startswith("MH OLD = "):
            old = re.sub(r"\s*(#\s*)?\[[A-Z]?\]\s*$", "", line[9:]).replace("#", "").strip()
        elif line.startswith("MH NEW = ") and old:
            pairs.append((old, line[9:].strip()))
            old = None
    return pairs


def uninvert(s: str) -> str | None:
    """'Carcinoma, Hepatocellular' -> 'Hepatocellular Carcinoma'. Only single ', ' inversions."""
    parts = s.split(", ")
    if len(parts) == 1:
        return s
    if len(parts) == 2:
        # not an inversion when the head is numeric ('46, XX ...') or the comma separates numbers ('Interleukin-4, 13 ...')
        if re.fullmatch(r"[\d\W]+", parts[0]) or (parts[0][-1:].isdigit() and parts[1][:1].isdigit()):
            return s
        return f"{parts[1]} {parts[0]}"
    return None  # multi-comma inversions are ambiguous


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.lower().replace("-", " ")).strip()


SPECIAL = re.compile(r"[\[\]\(\)\{\};:\"/\\+*?=<>&]")


def build_forms(rec: dict) -> dict:
    pref = next((c for c in rec["concepts"] if c["preferred"]), rec["concepts"][0])
    surface, excluded, acronyms, originals = [], [], [], []
    seen = set()
    for t in pref["terms"]:
        if t["permuted"] or not t["s"]:
            continue
        originals.append(t["s"])
        is_acr = t["lex"] in ("ABB", "ACR", "ABX")
        nat = uninvert(t["s"])
        if is_acr:
            acronyms.append(t["s"])
        if nat is None:
            excluded.append({"form": t["s"], "reason": "multi_comma_inversion"})
            continue
        key = norm(nat)
        if key in seen:
            continue
        seen.add(key)
        words = key.split()
        if is_acr and len(nat) < 5:
            excluded.append({"form": nat, "reason": "short_acronym"})
        elif len(nat) < 4:
            excluded.append({"form": nat, "reason": "too_short"})
        elif SPECIAL.search(nat):
            excluded.append({"form": nat, "reason": "special_characters"})
        elif len(words) == 1 and zipf_frequency(words[0], "en") >= GENERIC_ZIPF:
            excluded.append({"form": nat, "reason": f"generic_word_zipf>={GENERIC_ZIPF}"})
        else:
            surface.append(nat)
    narrower = []
    for c in rec["concepts"]:
        if c["preferred"]:
            continue
        for t in c["terms"]:
            if not t["permuted"] and t["s"]:
                narrower.append(t["s"])
    return {"surface_forms": surface, "excluded_forms": excluded, "acronyms": acronyms,
            "original_terms": originals, "narrower_concept_terms": narrower, "pref_concept": pref}


PAREN_YEAR = re.compile(r"\b((?:19|20)\d\d)\s*\(\s*((?:19|20)\d\d)")
RENAME_RE = re.compile(r"\b(see|was|use|under)\b.*\b(19|20)\d\d-(19|20)\d\d")
HN_REF = re.compile(r"\b(was|use|see|under)\s+(?:under\s+)?([A-Za-z0-9][^;]*?)\s+(?:19|20)\d\d-(?:19|20)\d\d")


def history_rename(hn: str, own_terms: set[str]) -> str | None:
    """Clear rename: 'was X yyyy-yyyy', or use/see/under pointing at one of the record's own terms.
    'use BROADER HEADING yyyy-yyyy' is ordinary previous indexing (kept, not a rename)."""
    if not RENAME_RE.search(hn):
        return None
    for m in HN_REF.finditer(hn):
        verb, head = m.group(1).lower(), norm(re.sub(r"\s*\((NM|SCR)\)\s*$", "", m.group(2).strip(" ,")))
        if verb == "was" or head in own_terms:
            return f"{verb} {m.group(2)[:80]}"
    return None


@logger.catch(reraise=True)
def main() -> None:
    logger.info(f"Parsing {SNAPSHOT} (full)")
    d17 = parse_desc_xml(RAW / SNAPSHOT, full=True)
    logger.info(f"{SNAPSHOT} records: {len(d17)}")
    logger.info("Parsing desc2026 (UIs only)")
    d26 = parse_desc_xml(RAW / "desc2026.xml.gz", full=False)
    logger.info(f"desc2026 records: {len(d26)}")

    flow: list[dict] = [{"step": f"{SNAPSHOT} descriptors (all classes){' [widening ' + TAG + ']' if TAG else ''}", "n": len(d17)}]
    cand = {ui: r for ui, r in d17.items() if r["cls"] == "1"}
    flow.append({"step": "DescriptorClass == 1 (topical)", "n": len(cand)})
    cand = {ui: r for ui, r in cand.items() if r["est"] and int(r["est"][:4]) in EST_YEARS}
    flow.append({"step": f"DateEstablished year in {EST_YEARS}", "n": len(cand)})
    by_year = Counter(int(r["est"][:4]) for r in cand.values())
    flow[-1]["by_year"] = dict(sorted(by_year.items()))
    cand = {ui: r for ui, r in cand.items() if r["trees"] and not all(t[0] in "VZ" for t in r["trees"])}
    flow.append({"step": "has tree numbers and not all in V/Z branches", "n": len(cand)})
    logger.info(f"Candidates: {len(cand)} by year {dict(sorted(by_year.items()))}")

    # prior-year ASCII files
    ascii_files = {y: RAW / f"d{y}.bin" for y in range(min(EST_YEARS) - 1, max(EST_YEARS) + 1)}
    available = {y: p for y, p in ascii_files.items() if p.exists()}
    logger.info(f"ASCII MeSH years available: {sorted(available)}")
    replaced_new: dict[int, set[str]] = {}
    replaced_pairs: dict[int, list] = {}
    for y in EST_YEARS:
        p = RAW / f"replace{y}.txt"
        if p.exists():
            pr = parse_replace(p)
            replaced_pairs[y] = pr
            replaced_new[y] = {n.lower() for _, n in pr}

    forms = {ui: build_forms(r) for ui, r in cand.items()}
    prov: dict[str, dict] = {ui: {"reasons": []} for ui in cand}

    # A: parenthetical prior year in notes
    for ui, r in cand.items():
        est_y = int(r["est"][:4])
        for note in (r["hn"], r["pmn"]):
            for m in PAREN_YEAR.finditer(note):
                if int(m.group(2)) < est_y:
                    prov[ui]["reasons"].append(f"A:parenthetical_year:{m.group(0)}")
                    break

    # B/C: need per-year ASCII; process one year at a time to bound memory
    for y in sorted({int(r["est"][:4]) for r in cand.values()}):
        uis = [ui for ui, r in cand.items() if int(r["est"][:4]) == y]
        before_years = [y - 1]
        t_prev, ui2mh_prev = parse_ascii(available[y - 1]) if (y - 1) in available else ({}, {})
        t_cur, ui2mh_cur = parse_ascii(available[y]) if y in available else ({}, {})
        deleted = {ui2mh_prev[u].lower() for u in set(ui2mh_prev) - set(ui2mh_cur)} if ui2mh_cur else set()
        for ui in uis:
            f = forms[ui]
            terms_l = {t.lower() for t in f["original_terms"]} | {norm(s) for s in f["surface_forms"]}
            homes = set()
            for t in terms_l:
                homes |= {u for u in t_prev.get(t, set()) if u != ui}
                if ui not in ui2mh_cur and ui2mh_cur:
                    homes |= {u for u in t_cur.get(t, set()) if u != ui}
            if homes:
                prov[ui]["reasons"].append(
                    f"B:promoted_term_from:{','.join(sorted(homes))[:80]}"
                    f"({'/'.join(sorted({ui2mh_prev.get(h) or ui2mh_cur.get(h) or '?' for h in homes}))[:120]})")
            if terms_l & deleted:
                prov[ui]["reasons"].append(f"C:deleted_descriptor_name_reused:{sorted(terms_l & deleted)[:3]}")
            if cand[ui]["name"].lower() in replaced_new.get(y, set()):
                olds = [o for o, n in replaced_pairs[y] if n.lower() == cand[ui]["name"].lower()]
                prov[ui]["reasons"].append(f"C:replace_file_new_heading_for:{olds[:3]}")
            hr = history_rename(cand[ui]["hn"], {norm(t) for t in terms_l})
            if hr:
                prov[ui]["reasons"].append(f"C:history_note_rename:{hr}")
            elif RENAME_RE.search(cand[ui]["hn"]):
                prov[ui]["reasons"].append(f"D:history_note_broader_heading:{cand[ui]['hn'][:120]}")
        logger.info(f"year {y}: {len(uis)} candidates, prior terms={len(t_prev)}, deleted names={len(deleted)}")
        del t_prev, t_cur, ui2mh_prev, ui2mh_cur

    rows = []
    for ui, r in cand.items():
        reasons = prov[ui]["reasons"]
        if any(x.startswith("A:") for x in reasons):
            pc = "PRIOR_EXPLICIT"
        elif any(x.startswith("B:") for x in reasons):
            pc = "PROMOTED_TERM"
        elif any(x.startswith("C:") for x in reasons):
            pc = "RENAMED"
        elif r["prev_idx"] or re.search(r"indexed under", r["pmn"], re.I):
            pc = "PRIOR_IMPLICIT"
        else:
            pc = "NO_PRIOR"
        f = forms[ui]
        rows.append({
            "concept_id": f"mesh:{ui}", "descriptor_ui": ui, "preferred_term": r["name"],
            "surface_forms": f["surface_forms"], "excluded_forms": f["excluded_forms"],
            "acronyms": f["acronyms"], "original_terms": f["original_terms"],
            "narrower_concept_terms": f["narrower_concept_terms"],
            "tree_numbers": r["trees"], "tree_branch_primary": r["trees"][0][0],
            "date_established": r["est"], "mesh_year_established": int(r["est"][:4]),
            "history_note": r["hn"], "public_mesh_note": r["pmn"], "previous_indexing": r["prev_idx"],
            "provenance_class": pc, "provenance_reasons": reasons,
            "chemical_flag": any(t.startswith("D") for t in r["trees"]),
            "still_in_mesh_2026": ui in d26,
        })
    pc_counts = Counter(x["provenance_class"] for x in rows)
    logger.info(f"Provenance classes: {dict(pc_counts)}")
    keep = [x for x in rows if x["provenance_class"] in ("PRIOR_IMPLICIT", "NO_PRIOR")]
    flow.append({"step": "provenance filter (drop PRIOR_EXPLICIT, PROMOTED_TERM, RENAMED)", "n": len(keep),
                 "class_counts": dict(pc_counts)})
    keep_m = [x for x in keep if x["surface_forms"]]
    flow.append({"step": "non-empty matchable surface-form set", "n": len(keep_m),
                 "dropped_empty_forms": len(keep) - len(keep_m)})
    logger.info(f"Kept after provenance: {len(keep)}; with matchable forms: {len(keep_m)}")

    (TEMP / f"candidates{SUF}.json").write_text(json.dumps(rows, indent=1))
    (TEMP / f"flow_step1_4{SUF}.json").write_text(json.dumps(flow, indent=1))
    if TAG:
        return  # synonym-pair set is built from the main 2006-2016 pool only
    light = {ui: {"name": r["name"], "trees": r["trees"], "cls": r["cls"], "est": r["est"]} for ui, r in d17.items()}
    (TEMP / "mesh_all_2017.json").write_text(json.dumps(light))

    # ---------------- synonym pair set ----------------
    rng = random.Random(SEED)
    tree2ui = {}
    for ui, r in light.items():
        for t in r["trees"]:
            tree2ui[t] = ui
    parent_children: dict[str, list[str]] = defaultdict(list)
    for t, ui in tree2ui.items():
        if "." in t:
            parent_children[t.rsplit(".", 1)[0]].append(ui)
    pos, neg = [], []
    for x in keep_m:
        ui = x["descriptor_ui"]
        rec = d17[ui]
        f = forms[ui]
        pref = f["pref_concept"]
        terms = []
        seen = set()
        for t in pref["terms"]:
            if t["permuted"] or not t["s"]:
                continue
            nat = uninvert(t["s"]) or t["s"]
            k = norm(nat)
            if k in seen:
                continue
            seen.add(k)
            terms.append((nat, t["lex"] in ("ABB", "ACR", "ABX"), t["s"]))
        combos = list(itertools.combinations(terms, 2))
        rng.shuffle(combos)
        for a, b in combos[:PAIR_CAP_POS]:
            pos.append({"term_a": a[0], "term_b": b[0], "label": 1,
                        "pair_type": "acronym_expansion" if (a[1] ^ b[1]) else "synonym",
                        "descriptor_ui": ui, "descriptor_ui_b": ui, "orig_a": a[2], "orig_b": b[2]})
        pref_term = rec["name"]
        pref_nat = uninvert(pref_term) or pref_term
        seen_neg = {norm(pref_nat)}
        for c in rec["concepts"]:
            if c["preferred"]:
                continue
            rel = next((r["rel"] for cc in rec["concepts"] for r in cc["rels"] if c["cui"] in (r["c1"], r["c2"])), None)
            for t in c["terms"]:
                if t["permuted"] or not t["s"]:
                    continue
                if norm(uninvert(t["s"]) or t["s"]) in seen_neg:
                    continue   # inverted and natural-order spellings of the same term
                seen_neg.add(norm(uninvert(t["s"]) or t["s"]))
                neg.append({"term_a": pref_nat, "term_b": uninvert(t["s"]) or t["s"], "label": 0,
                            "pair_type": f"non_preferred_concept_{(rel or 'NRW').lower()}",
                            "descriptor_ui": ui, "descriptor_ui_b": ui, "orig_a": pref_term, "orig_b": t["s"]})
        sibs = set()
        for t in rec["trees"]:
            if "." in t:
                sibs |= {u for u in parent_children[t.rsplit(".", 1)[0]] if u != ui}
        sibs = sorted(sibs)
        rng.shuffle(sibs)
        for s in sibs[:SIB_NEG_PER_DESC]:
            sn = light[s]["name"]
            neg.append({"term_a": pref_nat, "term_b": uninvert(sn) or sn, "label": 0,
                        "pair_type": "sibling_descriptor", "descriptor_ui": ui, "descriptor_ui_b": s,
                        "orig_a": pref_term, "orig_b": sn})
    # global safety net: one entry per unordered, case/hyphen-insensitive term pair (first occurrence kept)
    seen_pairs: set = set()
    kept = {"positive": [], "negative": []}
    for lab, lst in (("positive", pos), ("negative", neg)):
        for x in lst:
            k = frozenset((norm(x["term_a"]), norm(x["term_b"])))
            if len(k) < 2 or k in seen_pairs:
                continue
            seen_pairs.add(k)
            kept[lab].append(x)
    pos, neg = kept["positive"], kept["negative"]
    logger.info(f"Pairs: {len(pos)} positive, {len(neg)} negative; types {Counter(p['pair_type'] for p in pos + neg)}")
    (TEMP / "pairs_raw.json").write_text(json.dumps({"positive": pos, "negative": neg}))


if __name__ == "__main__":
    main()
