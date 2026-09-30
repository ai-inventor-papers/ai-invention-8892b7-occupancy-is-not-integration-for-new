#!/usr/bin/env python3
"""Numbers-of-record audit (iteration 5, FIX slot): every number and verdict the
paper can cite is re-read / recomputed from its source file and diffed against
iter_5/gen_strat/current_report.md. Emits the flag record, the report-drift list,
paper-ready tables (only those passing audit_tables.py), cases.md, and
eval_out.json (exp_eval_sol_out). CPU only, $0, read-only on every dependency.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
import re
import resource
import subprocess
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

WS = Path(__file__).resolve().parent
sys.path.insert(0, str(WS))
(WS / "logs").mkdir(exist_ok=True)
(WS / "results").mkdir(exist_ok=True)
(WS / "tables").mkdir(exist_ok=True)
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(str(WS / "logs" / "run.log"), rotation="30 MB", level="DEBUG")
resource.setrlimit(resource.RLIMIT_AS, (24 * 1024 ** 3, 24 * 1024 ** 3))

import audit_core as AC  # noqa: E402
from registry import CLAIMS  # noqa: E402

SEED = 20260929
SEED_BLIND = 20260930  # fresh draw used for the reported (blind) M5 after the detector fix; see README
KNOWN_DRIFT = {  # the plan's known-drift list (gate: recall must be 100%)
    "K01_rq1_rescue_summary": "RQ1 rescue in the summary paragraph (line ~7)",
    "K02_learned_heading": "'What we have learned' heading rescues RQ1 (line ~867)",
    "K03_fig_methodology": "fig_methodology description (rescued R1, OR 3.14, placement)",
    "K04_26of27": "'26 of 27' robustness (lines ~486 note vs ~551)",
    "K05_primary_CT_p": "primary CT p 0.48 vs 0.85",
    "K06_83pct": "'83% single-paper'",
    "K08_table20": "Table 20's 1.14 / 1.09",
    "K09_or_31x": "'3.1x more likely'",
    "K10_neg_plac_matching": "NEG/PLAC/matching descriptions",
    "K11_k2_mesh": "'k = 2 replicates on ... MeSH'",
    "K12_mesh_leadlag": "'directionally consistent' MeSH lead-lag",
    "K14_establishment": "'host-native partners predict establishment' while EST_bin is null",
}
EXTRA_KNOWN = {"K13_constraint_mixed": "Table 20c constraint row mixes pooled-panel screen with event-study held-out (review item)"}
BLOCK_ORDER = ["D2", "MeSH", "RQ1", "descriptive", "adopter", "data"]


# ============================================================ helpers
def sha(s: str | bytes) -> str:
    return hashlib.sha256(s if isinstance(s, bytes) else s.encode()).hexdigest()


def find_rep(lines: list[str], hint: int, regex: str) -> tuple[int, str] | None:
    """Locate a reported number by regex; the match nearest the hint line wins."""
    rx = re.compile(regex)
    best = None
    for i, l in enumerate(lines):
        m = rx.search(l)
        if m:
            d = abs(i + 1 - hint)
            if best is None or d < best[0]:
                best = (d, i + 1, m.group(1))
    return (best[1], best[2]) if best else None


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        if v != 0 and (abs(v) < 1e-3 or abs(v) >= 1e6):
            return f"{v:.3e}"
        return f"{v:.6g}"
    return str(v)


# ============================================================ step 0: freeze the universe
def build_universe(lines: list[str], hypo_text: str) -> dict:
    toks = []
    for i, l in enumerate(lines):
        for t in AC.tokenize_line(l, i + 1):
            toks.append(dict(line=t.line, col=t.col, text=t.text, kind=t.kind))
    reg = []
    for c in CLAIMS:
        rv = find_rep(lines, c["rep"][0], c["rep"][1]) if c["rep"] else None
        hv = None
        if c.get("hyp"):
            m = re.search(c["hyp"], hypo_text)
            hv = m.group(1) if m else None
        reg.append(dict(id=c["id"], block=c["block"], report_line=rv[0] if rv else None, report_value=rv[1] if rv else None,
                        hyp_value=hv, src=c["src"], alt=[a[1] for a in c["alt"]]))
    verdict_words = [(i + 1, w) for i, l in enumerate(lines) for w in re.findall(
        r"\b(CONFIRMED|DEAD|GRAFTING|NEITHER|REPLICATED|NULL|MIXED|TRIGGERED|NOT MET|PASS|FAIL|SUPPORT|NOT SUPPORTED|R1_DEAD)\b", l)]
    return dict(tokens=toks, registry=reg, verdict_words=verdict_words)


def freeze(lines: list[str], hypo_text: str) -> dict:
    uni = build_universe(lines, hypo_text)
    uni_json = json.dumps(uni, sort_keys=True, ensure_ascii=False)
    spec = dict(
        artifact="gen_art_evaluation_8 (iteration 5, FIX slot): numbers-of-record audit",
        frozen_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        note="Frozen before any source file is opened: universe of cited numbers, match rule, flag taxonomy, known-drift list, "
             "seeded-injection design. Sources are only read after this file is written.",
        report=AC.REPORT_REL, report_sha256=sha((AC.RUN_ROOT / AC.REPORT_REL).read_bytes()),
        hypothesis=AC.HYPO_REL, hypothesis_sha256=sha((AC.RUN_ROOT / AC.HYPO_REL).read_bytes()),
        universe_sha256=sha(uni_json), n_report_tokens=len(uni["tokens"]),
        n_report_tokens_by_kind=dict(Counter(t["kind"] for t in uni["tokens"])),
        n_registry_claims=len(uni["registry"]), n_verdict_words=len(uni["verdict_words"]),
        match_rule=AC.MATCH_RULE, flags=AC.FLAG_DEFS, known_drift=KNOWN_DRIFT, extra_known=EXTRA_KNOWN,
        severity_grades={"VERDICT-CHANGING": "the correct number/verdict changes a significance side, a CI-excludes-null statement or a decision-rule outcome",
                         "NUMBER-ONLY": "value differs but no conclusion changes", "WORDING": "definition/label/scope wording"},
        tiers={"R": "re-read from a summary JSON/CSV", "C": "recomputed from row-level files or from primitive quantities (Holm, IVW, counts, prevalences)"},
        seeded_injection=dict(seed=SEED, n_per_type=10, types=["digit_change", "ci_bound_swap", "estimator_fold_relabel", "verdict_flip"],
                              target_recall=0.95, blind="the detector receives only the perturbed text"),
        independent_rederivation=dict(n_sample=50, min_per_block=8, plus="all headline/verdict-bearing numbers", seed=SEED),
    )
    (WS / "results" / "audit_universe.json").write_text(uni_json)
    (WS / "results" / "audit_spec.json").write_text(json.dumps(spec, indent=2, ensure_ascii=False))
    spec["_audit_spec_sha256"] = sha((WS / "results" / "audit_spec.json").read_bytes())
    logger.info(f"FROZEN universe sha256 {spec['universe_sha256'][:16]} ({len(uni['tokens'])} tokens, {len(uni['registry'])} claims) at {spec['frozen_utc']}")
    return dict(spec=spec, universe=uni)


# ============================================================ step 1: evaluate registry claims
def source_value(spec: str):
    import checks
    if spec.startswith("recompute:"):
        return checks.RECOMPUTE[spec.split(":", 1)[1]]()
    return AC.read_source(spec)


TIERC_IRR = {  # headline IRR rows recomputed from primitives b, se and the row-level SD of A_cont
    "d2.scr.cop.irr": ("screen", "irr"), "d2.scr.cop.lo": ("screen", "lo"), "d2.scr.cop.hi": ("screen", "hi"),
    "d2.ho.cop.irr": ("heldout", "irr"), "d2.ho.cop.irr_sum": ("heldout", "irr"), "d2.ho.cop.lo": ("heldout", "lo"), "d2.ho.cop.hi": ("heldout", "hi"),
    "g4.R2.irr": ("mesh", "irr"), "g4.R2.irr_sum": ("mesh", "irr"), "g4.R2.lo": ("mesh", "lo"), "g4.R2.hi": ("mesh", "hi"),
}


def _prune(d, fes, y="Y_strict"):
    """Drop FE groups with all-zero outcome or a single event until stable (PPML separation / singletons)."""
    while True:
        n = len(d)
        for f in fes:
            d = d[d.groupby(f)[y].transform("sum") > 0]
            d = d[d.groupby(f)[y].transform("size") > 1]
        if len(d) == n:
            return d


def tierc_irr(which: str, part: str) -> tuple[float, str]:
    """IRR/SD recomputed as exp(b * SD(A_cont)) with SD over the reconstructed co-primary estimation sample
    (row-level events, concept + e + d FE groups pruned for all-zero outcomes and singletons); CI from b +- 1.96 se."""
    import pandas as pd
    z = 1.959963984540054
    if which == "screen":
        m = AC.load_json("round-3/experiment-7/src/results/d2_summary.json")["coprimary_fe_concept_plus_e_plus_d"]["A_cont"]
        ev = pd.read_parquet(AC.RUN_ROOT / "round-3/experiment-7/src/results/screen_events_with_outcomes.parquet",
                             columns=["concept_id", "d", "e", "fold", "MAIN", "kw5", "A_cont", "Y_strict"])
        ev = ev[(ev.fold == "screen") & ev.MAIN & ev.kw5].dropna(subset=["A_cont", "Y_strict"])
        b, se = m["b"], m["se"]
        src = "exp_7 screen_events_with_outcomes.parquet"
    elif which == "heldout":
        r = [x for x in AC.load_csv("round-4/evaluation-2/src/results/heldout_robustness.csv")
             if x["spec"] == "PRIMARY (MAIN)" and x["fe"] == "secondary"][0]
        b, se = float(r["b_A"]), float(r["se_A"])
        ev = pd.read_parquet(AC.RUN_ROOT / "round-4/evaluation-2/src/results/g_features_heldout_coprimary.parquet",
                             columns=["concept_id", "d", "e", "MAIN", "kw5", "A_cont", "Y_strict"])
        ev = ev[ev.MAIN & ev.kw5].dropna(subset=["A_cont", "Y_strict"])
        src = "art_WZ8fbLn79nCq g_features_heldout_coprimary.parquet"
    else:
        a = AC.load_json("round-4/experiment-9/src/results/g4_models.json")["rows"]["R2"]["row"]["A_cont"]
        b, se = a["b"], a["se"]
        ev = pd.read_parquet(AC.RUN_ROOT / "round-4/experiment-9/src/results/outcomes_mesh.parquet",
                             columns=["concept_id", "d", "e", "MESH_MAIN", "A_cont", "Y_strict"])
        ev = ev[ev.MESH_MAIN].dropna(subset=["A_cont", "Y_strict"])
        src = "art_XGdzjWgi-a88 outcomes_mesh.parquet"
    p = _prune(ev, ["concept_id", "e", "d"])
    sd = float(p.A_cont.std())
    val = {"irr": math.exp(b * sd), "lo": math.exp((b - z * se) * sd), "hi": math.exp((b + z * se) * sd)}[part]
    return val, f"exp(b*SD) with SD over the reconstructed estimation sample (N={len(p)}, G={p.concept_id.nunique()}) of {src}"


def evaluate_claim(c: dict, lines: list[str], hypo_text: str) -> dict:
    out = dict(id=c["id"], block=c["block"], claim=c["claim"], fold_label=c["fold"], estimator=c["estimator"], artifact=c["art"],
               tier=c["tier"], headline=c["headline"], known=c.get("known") or "")
    rv = find_rep(lines, c["rep"][0], c["rep"][1]) if c["rep"] else None
    hv = None
    if c.get("hyp"):
        m = re.search(c["hyp"], hypo_text)
        hv = m.group(1) if m else None
    out.update(report_line=rv[0] if rv else "", report_value=rv[1] if rv else "", hyp_value=hv or "")
    out["source"] = c["src"] or ""
    sv, err = None, ""
    if c["src"]:
        try:
            sv = source_value(c["src"])
        except (KeyError, IndexError, FileNotFoundError, ValueError, TypeError, StopIteration) as e:
            err = f"{type(e).__name__}: {e}"
            logger.warning(f"source read failed for {c['id']}: {err}")
    out["source_value"] = sv if not isinstance(sv, str) else sv
    out["source_error"] = err
    out["recomputed"] = ""
    out["recompute_method"] = "recompute function (row-level / primitives)" if (c["src"] or "").startswith("recompute:") else "re-read"
    if c["id"] in TIERC_IRR:
        try:
            v, how = tierc_irr(*TIERC_IRR[c["id"]])
            out["recomputed"], out["recompute_method"] = v, how
        except (KeyError, FileNotFoundError, ValueError, TypeError) as e:
            out["recompute_method"] = f"tier-C recompute failed: {e}"
            out["tier"] = "R"
    compare_str = out["report_value"]
    rep = AC.parse_reported(compare_str) if compare_str else None
    kind = c["kind"]
    if rep is not None and rep.is_pct and kind == "cont":
        kind = "pct"
    if kind == "pctval":
        kind = "cont"

    def m(val) -> bool:
        return rep is not None and isinstance(val, (int, float)) and AC.match_value(rep, float(val), kind, c.get("holm"), c.get("sign", "signed"))

    flag, alt_used = None, ""
    if rep is None:
        flag = "MISSING_IN_REPORT"
        agrees = None
    elif c["src"] and not err and m(sv):
        flag = "OK"
    else:
        for cat, aspec in c["alt"]:
            try:
                av = source_value(aspec)
            except (KeyError, IndexError, FileNotFoundError, ValueError, TypeError) as e:
                logger.warning(f"alt read failed {c['id']}: {e}")
                continue
            if m(av):
                flag, alt_used = cat, f"{aspec} = {fmt(av)}"
                if cat == "OK":
                    out["source"], out["source_value"] = aspec, av
                break
        if flag is None:
            flag = "NOT_TRACEABLE" if (not c["src"] or err) else "DRIFT_VALUE"
    if c["tier"] == "C" and out["recomputed"] != "" and rep is not None and flag == "OK":
        if not m(out["recomputed"]):
            flag = "DRIFT_VALUE"
            alt_used = f"tier-C recompute disagrees: {fmt(out['recomputed'])}"
    # where the text is only in the hypothesis, still check the hypothesis value
    hyp_ok = ""
    if hv:
        hr = AC.parse_reported(hv)
        if hr is not None and sv is not None and isinstance(sv, (int, float)):
            hk = "pct" if (hr.is_pct and c["kind"] == "cont") else ("cont" if c["kind"] == "pctval" else c["kind"])
            hyp_ok = str(AC.match_value(hr, float(sv), hk, c.get("holm"), c.get("sign", "signed")))
    if flag == "MISSING_IN_REPORT" and not hv and c["src"]:
        out["note"] = "number of record (artifact output) never stated in the report"
    else:
        out["note"] = ""
    out.update(flag=flag, alt_match=alt_used, hyp_agrees=hyp_ok, replacement=c.get("replacement") or "",
               traced=bool((c["src"] and not err) or flag == "OK"))
    return out


# ============================================================ step 2: verdicts and assertions
def evaluate_verdicts(lines: list[str]) -> list[dict]:
    import checks
    rows = []
    for r in checks.verdict_rules():
        row = dict(iteration=r["it"], rule=r["rule"], rule_quote=r["quote"], rule_recorded=bool(r["quote"]) or r["outcome"] != "RULE_NOT_RECORDED",
                   outcome_from_rule=r["outcome"], inputs=r["inputs"], source=r["src"], report_line="", report_statement="")
        if r["outcome"] == "RULE_NOT_RECORDED":
            row.update(status="RULE_NOT_RECORDED", flag="RULE_NOT_RECORDED")
            rows.append(row)
            continue
        hit = find_rep(lines, r["report_hint"], r["report_regex"]) if r["report_regex"] else None
        expected = r.get("equiv", {}).get(r["outcome"], r["outcome"])
        if hit:
            row.update(report_line=hit[0], report_statement=hit[1])
            ok = hit[1].strip().lower() == str(expected).strip().lower()
        else:
            ok = False
            row.update(report_line=r["report_hint"], report_statement="verdict statement not found (changed or removed)")
        if r.get("rescue_lines"):
            # R1: the rule's outcome string must appear; the rescue sentences are the drift lines
            res = []
            for hint, rx in r["rescue_lines"]:
                h = find_rep(lines, hint, "(" + rx + ")")
                if h:
                    res.append(h[0])
            row["rescue_lines"] = res
            row["report_line"] = ";".join(str(x) for x in res) if not hit else hit[0]
            row["report_statement"] = "R1_DEAD / 'volume/churn correlates' never stated; persistent-neighbour row headlined" if not hit else hit[1]
        row.update(status="MATCH" if ok else "MISMATCH", flag="OK" if ok else "VERDICT_DRIFT")
        rows.append(row)
    return rows


def evaluate_vcells(lines: list[str]) -> list[dict]:
    import checks
    out = []
    for v in checks.verdict_cells():
        hit = find_rep(lines, v["hint"], v["rx"])
        exp = str(v["expected"])
        if not hit:
            out.append(dict(id=v["id"], report_line=v["hint"], reported="(statement not found)", expected=exp, flag="VERDICT_DRIFT", source=v["src"]))
            continue
        rep = hit[1].strip()
        if v["mode"] == "passfail":
            ok = ("FAIL" in rep) == (exp == "FAIL") and (("PASS" in rep) == (exp == "PASS"))
        elif v["mode"] == "ci":
            ok = rep.lower() == exp.lower()
        else:
            ok = rep == exp
        out.append(dict(id=v["id"], report_line=hit[0], reported=rep, expected=exp, flag="OK" if ok else "VERDICT_DRIFT", source=v["src"]))
    return out


FOLD_OF_CLAIM = {"CONFIRMATORY": "heldout", "SCREEN": "screen", "MESH": "mesh"}


def clause_folds(line: str, value: str) -> set[str]:
    """fold words in the clause that carries the value: table row cells before it, or the sentence up to it."""
    pos = line.find(value)
    if pos < 0:
        return set()
    if line.lstrip().startswith("|"):
        return fold_label_of(line[:pos])
    m_after = re.match(r"\s*\(([^)]{0,25})\)", line[pos + len(value):])
    after = m_after.group(1) if m_after else ""
    if fold_label_of(after):
        return fold_label_of(after)
    before = line[:pos]
    cut = max(before.rfind(". "), before.rfind("; "), before.rfind(", "), before.rfind(" vs "), before.rfind("compared to"))
    return fold_label_of(before[cut + 1:])


def fold_check(claims: list[dict], lines: list[str]) -> list[dict]:
    out = []
    for c in claims:
        if not c["report_line"] or c["flag"] != "OK":
            continue
        want = FOLD_OF_CLAIM.get(c["fold_label"])
        if not want:
            continue
        got = clause_folds(lines[int(c["report_line"]) - 1], c["report_value"])
        if got and want not in got:
            out.append(dict(id=c["id"], report_line=c["report_line"], expected_fold=want, clause_folds=sorted(got), flag="WRONG_FOLD"))
    return out


def evaluate_assertions(lines: list[str]) -> list[dict]:
    import checks
    out = []
    for a in checks.assertions():
        hit = find_rep(lines, a["hint"], "(" + a["pattern"] + ")")
        fired = hit is not None
        flag = a["flag"] if (fired and not a["supported"]) else "OK"
        out.append(dict(id=a["id"], report_line=hit[0] if hit else "", report_text=hit[1] if hit else "", statement_present=fired,
                        supported_by_source=a["supported"], flag=flag, correct_text=a["correct"], source=a["src"], known=a.get("known") or "",
                        severity=a.get("severity") or ""))
    return out


# ============================================================ step 3: auto-scan of every report token
_INDEX: dict[str, AC.ArtifactIndex] = {}


def get_index(art: str) -> AC.ArtifactIndex:
    if art not in _INDEX:
        t0 = time.time()
        _INDEX[art] = AC.build_index(art)
        logger.debug(f"indexed {art}: {len(_INDEX[art].values)} values from {_INDEX[art].n_files} files in {time.time() - t0:.1f}s")
    return _INDEX[art]


ART_ITER = {a: int(re.search(r"iter_(\d)", p).group(1)) for a, p in AC.ARTIFACTS.items()}
FOLDER_TO_ART = {p.split("/")[-1] + f"@{ART_ITER[a]}": a for a, p in AC.ARTIFACTS.items()}


def line_artifacts(lines: list[str]) -> dict[int, list[str]]:
    secs = AC.sections(lines)
    out: dict[int, list[str]] = {}
    for s, e, h in secs:
        it = AC.iteration_of_line(lines, s)
        text = "\n".join(lines[s - 1:e])
        arts = set(re.findall(r"\[ARTIFACT:(art_[A-Za-z0-9_\-]+)\]", text)) & set(AC.ARTIFACTS)
        for fold in re.findall(r"(gen_art_[a-z]+_\d)", text):
            key = f"{fold}@{it}"
            if key in FOLDER_TO_ART:
                arts.add(FOLDER_TO_ART[key])
        for a in re.findall(r"\b(art_[A-Za-z0-9_\-]{12})", text):
            if a in AC.ARTIFACTS:
                arts.add(a)
        if not arts:
            arts = {a for a, i in ART_ITER.items() if (it == 0 or i <= it)}
        for ln in range(s, e + 1):
            out[ln] = sorted(arts)
    for ln in range(1, len(lines) + 1):
        out.setdefault(ln, sorted(AC.ARTIFACTS))
    return out


FOLD_WORDS = {"heldout": ("held-out", "held_out", "heldout"), "screen": ("screen",), "mesh": ("mesh",)}


def fold_label_of(line: str) -> set[str]:
    ll = line.lower()
    return {k for k, ws in FOLD_WORDS.items() if any(w in ll for w in ws)}


def ctx_folds(ctx: str) -> set[str]:
    cl = ctx.lower()
    return {k for k, ws in FOLD_WORDS.items() if any(w in cl for w in ws)}


CI_RX = re.compile(r"([−\-+]?\d[\d,]*\.?\d*)\s*%?\s*\[([−\-+]?\d[\d,]*\.?\d*)%?,\s*([−\-+]?\d[\d,]*\.?\d*)%?\]")


def _fkey(ctx: str) -> str:
    """file-level key of a hit context (the source file)."""
    return ctx.split("::", 1)[0]


def colocate(rows: list[dict], lines: list[str], window: int = 2) -> None:
    """A token is co-located if one of its hit files is also hit by >= 2 OTHER tokens within +-window lines of the same section.
    Tokens with no such consensus nearby are left unjudged; traced tokens whose files share nothing with the consensus are NOT_COLOCATED."""
    sec_of = {}
    for s0, e0, _ in AC.sections(lines):
        for ln in range(s0, e0 + 1):
            sec_of[ln] = s0
    toks = [r for r in rows if r["status"] == "TRACED_AUTO" and r["sig"] >= 2]
    by_line = defaultdict(list)
    for r in toks:
        by_line[r["line"]].append(r)
    for r in toks:
        cnt = Counter()
        for ln in range(r["line"] - window, r["line"] + window + 1):
            if sec_of.get(ln) != sec_of.get(r["line"]):
                continue
            for o in by_line.get(ln, []):
                if o is r:
                    continue
                for f in o["_files"]:
                    cnt[f] += 1
        consensus = {f for f, n in cnt.items() if n >= 2}
        if consensus and not (r["_files"] & consensus):
            r["status"] = "NOT_COLOCATED"


def autoscan(lines: list[str], line_arts: dict[int, list[str]]) -> list[dict]:
    rows = []
    for i, l in enumerate(lines):
        ln = i + 1
        if ln >= _ref_start(lines):
            break
        toks = [t for t in AC.tokenize_line(l, ln) if t.kind == "num"]
        if not toks:
            continue
        idx = [get_index(a) for a in line_arts.get(ln, [])]
        folds = fold_label_of(l)
        for t in toks:
            hits = AC.locate(t.rep, idx, cap=3000) if idx else []
            status = "TRACED_AUTO" if hits else "UNTRACED"
            if hits and len(folds) == 1 and "|" not in l[:2]:
                fl = next(iter(folds))
                hf = [ctx_folds(h) for h in hits]
                labelled = [f for f in hf if f]
                if labelled and len(labelled) == len(hf) and not any(fl in f for f in labelled):
                    status = "FOLD_LABEL_CONFLICT"
            rows.append(dict(line=ln, col=t.col, token=t.text, sig=t.rep.sig, status=status,
                             n_hits=len(hits), example_hit=hits[0] if hits else "", _files={_fkey(h) for h in hits}))
        for m in CI_RX.finditer(l.translate(AC.MINUS)):
            try:
                x, lo, hi = (float(g.replace(",", "")) for g in m.groups())
            except ValueError:
                continue
            p = AC.parse_reported(m.group(1).translate(AC.MINUS))
            tol = 0.5 * 10 ** (-(p.decimals if p else 2)) + 1e-9
            if lo > hi + tol or not (lo - tol <= x <= hi + tol):
                rows.append(dict(line=ln, col=m.start(), token=m.group(0), sig=0, status="CI_INCONSISTENT", n_hits=0, example_hit="", _files=set()))
    colocate(rows, lines)
    for r in rows:
        r.pop("_files", None)
    return rows


def _ref_start(lines: list[str]) -> int:
    for i, l in enumerate(lines):
        if l.strip() == "## References":
            return i + 1
    return len(lines) + 1


# ============================================================ detector (used on the real report and on seeded copies)
def run_detector(lines: list[str], hypo_text: str, line_arts: dict[int, list[str]]) -> dict:
    claims = [evaluate_claim(c, lines, hypo_text) for c in CLAIMS]
    verdicts = evaluate_verdicts(lines)
    asserts = evaluate_assertions(lines)
    vcells = evaluate_vcells(lines)
    folds = fold_check(claims, lines)
    scan = autoscan(lines, line_arts)
    flagged: dict[int, set[str]] = defaultdict(set)
    for c in claims:
        if c["report_line"] and c["flag"] not in ("OK", "MISSING_IN_REPORT"):
            flagged[int(c["report_line"])].add(f"claim:{c['id']}:{c['flag']}")
    # a registry claim whose anchor vanished from the report is itself a detected change
    for c in claims:
        if c["flag"] == "MISSING_IN_REPORT" and CLAIM_BY_ID[c["id"]]["rep"] and not c["hyp_value"]:
            flagged[-1].add(f"anchor_lost:{c['id']}")
    for v in verdicts:
        if v["flag"] == "VERDICT_DRIFT":
            for ln in (v.get("rescue_lines") or ([v["report_line"]] if v["report_line"] else [])):
                flagged[int(ln)].add(f"verdict:{v['rule']}")
    for a in asserts:
        if a["flag"] != "OK" and a["report_line"]:
            flagged[int(a["report_line"])].add(f"assert:{a['id']}:{a['flag']}")
    for v in vcells:
        if v["flag"] != "OK":
            flagged[int(v["report_line"])].add(f"vcell:{v['id']}")
    for f in folds:
        flagged[int(f["report_line"])].add(f"fold:{f['id']}")
    for s in scan:
        if s["status"] in ("UNTRACED", "CI_INCONSISTENT", "FOLD_LABEL_CONFLICT", "NOT_COLOCATED") and (s["sig"] >= 2 or s["status"] != "UNTRACED"):
            flagged[s["line"]].add(f"scan:{s['status']}:{s['token']}")
    return dict(claims=claims, verdicts=verdicts, asserts=asserts, vcells=vcells, folds=folds, scan=scan, flagged=flagged)


CLAIM_BY_ID = {c["id"]: c for c in CLAIMS}


# ============================================================ severity grading and drift list
def p_side(v) -> bool | None:
    try:
        return float(v) < 0.05
    except (TypeError, ValueError):
        return None


def grade(c: dict) -> str:
    if c["flag"] in ("VERDICT_DRIFT",):
        return "VERDICT-CHANGING"
    if CLAIM_BY_ID[c["id"]]["kind"] == "p":
        r = AC.parse_reported(c["report_value"]) if c["report_value"] else None
        if r is not None and isinstance(c["source_value"], float) and (r.value < 0.05) != (c["source_value"] < 0.05):
            return "VERDICT-CHANGING"
    if c["flag"] == "WRONG_DEFINITION":
        return "WORDING" if not c["headline"] else "VERDICT-CHANGING"
    if c["headline"] and c["flag"] in ("NOT_TRACEABLE", "WRONG_ESTIMATOR", "DRIFT_VALUE", "WRONG_FOLD"):
        return "VERDICT-CHANGING" if c["id"].startswith(("rq1.persist.sum",)) else "NUMBER-ONLY"
    return "NUMBER-ONLY"


def drift_list(det: dict, lines: list[str]) -> list[dict]:
    rows = []
    for c in det["claims"]:
        if c["report_line"] and c["flag"] not in ("OK", "MISSING_IN_REPORT"):
            correct = c["replacement"] or (fmt(c["source_value"]) if c["source_value"] not in (None, "") else "remove (no source)")
            rows.append(dict(line=c["report_line"], report_text=lines[int(c["report_line"]) - 1].strip()[:300], reported=c["report_value"],
                             correct_text=correct, flag=c["flag"], severity=grade(c), source=c["source"] or c["alt_match"],
                             claim_id=c["id"], known=c["known"]))
    for v in det["verdicts"]:
        if v["flag"] == "VERDICT_DRIFT":
            for ln in v.get("rescue_lines") or [v["report_line"]]:
                if not ln:
                    continue
                rows.append(dict(line=ln, report_text=lines[int(ln) - 1].strip()[:300], reported=v["report_statement"],
                                 correct_text=f"{v['outcome_from_rule']} under the frozen rule: {v['inputs']}. RQ1 sentence: 'Structural precursors of sustained uptake are volume/churn correlates.'"
                                 if "R1" in v["rule"] else v["outcome_from_rule"],
                                 flag="VERDICT_DRIFT", severity="VERDICT-CHANGING", source=v["source"], claim_id="rule:" + v["rule"],
                                 known="K01_rq1_rescue_summary" if int(ln) < 20 else ("K02_learned_heading" if "R1" in v["rule"] else "")))
    for v in det.get("vcells", []):
        if v["flag"] != "OK":
            rows.append(dict(line=v["report_line"], report_text=lines[int(v["report_line"]) - 1].strip()[:300], reported=v["reported"], correct_text=v["expected"],
                             flag="VERDICT_DRIFT", severity="VERDICT-CHANGING", source=v["source"], claim_id=v["id"], known=""))
    for f in det.get("folds", []):
        rows.append(dict(line=f["report_line"], report_text=lines[int(f["report_line"]) - 1].strip()[:300], reported=",".join(f["clause_folds"]),
                         correct_text=f"fold label should be {f['expected_fold']}", flag="WRONG_FOLD", severity="NUMBER-ONLY", source="", claim_id=f["id"], known=""))
    for a in det["asserts"]:
        if a["flag"] != "OK":
            sev = a["severity"] or ("VERDICT-CHANGING" if a["flag"] == "VERDICT_DRIFT" else "WORDING")
            rows.append(dict(line=a["report_line"], report_text=lines[int(a["report_line"]) - 1].strip()[:300], reported=a["report_text"],
                             correct_text=a["correct_text"], flag=a["flag"], severity=sev, source=a["source"], claim_id=a["id"], known=a["known"]))
    rows.sort(key=lambda r: (int(r["line"]), r["claim_id"]))
    return rows


# ============================================================ seeded-error injection (M5)
LABEL_SWAPS = [("held-out", "screen"), ("Held-out", "Screen"), ("screen", "held-out"), ("Screen", "Held-out"),
               ("co-primary", "primary"), ("Co-primary", "Primary"), ("pooled panel", "event study"), ("pooled-panel", "event-study"),
               ("event study", "pooled panel"), ("MeSH", "main")]
VERDICT_SWAPS = [("CONFIRMED", "DEAD"), ("DEAD", "CONFIRMED"), ("GRAFTING", "NEITHER"), ("NEITHER", "GRAFTING"), ("REPLICATED", "NOT REPLICATED"),
                 ("NULL", "SUPPORTED"), ("MIXED", "BROKERAGE"), ("TRIGGERED", "NOT TRIGGERED"), ("NOT MET", "MET"), ("PASS", "FAIL"),
                 ("host-vocabulary", "artefact"), ("YES", "NO")]


def perturb(lines: list[str], clean_flagged: set[int], ref_start: int, rng: random.Random) -> list[dict]:
    num_lines = [i + 1 for i, l in enumerate(lines[:ref_start - 1]) if any(t.kind == "num" and t.rep.sig >= 2 for t in AC.tokenize_line(l, i + 1))]
    cands = [ln for ln in num_lines if ln not in clean_flagged and not lines[ln - 1].startswith("| ---")]
    ci_lines = [ln for ln in cands if CI_RX.search(lines[ln - 1].translate(AC.MINUS))]
    lab_lines = [ln for ln in cands if any(a in lines[ln - 1] for a, _ in LABEL_SWAPS)]
    ver_lines = [i + 1 for i, l in enumerate(lines[:ref_start - 1]) if (i + 1) not in clean_flagged and any(re.search(rf"\b{re.escape(a)}\b", l) for a, _ in VERDICT_SWAPS)]
    used: set[int] = set()
    perts = []

    def pick(pool):
        pool = [p for p in pool if p not in used]
        ln = rng.choice(pool)
        used.add(ln)
        return ln

    for _ in range(10):  # digit change
        ln = pick(cands)
        toks = [t for t in AC.tokenize_line(lines[ln - 1], ln) if t.kind == "num" and t.rep.sig >= 2]
        t = rng.choice(toks)
        digs = [k for k, ch in enumerate(t.text) if ch.isdigit()]
        k = rng.choice(digs[1:] if len(digs) > 1 else digs)
        new_d = str((int(t.text[k]) + rng.choice([1, 2, 3, 4, 5, 6, 7, 8, 9])) % 10)
        new_tok = t.text[:k] + new_d + t.text[k + 1:]
        l = lines[ln - 1]
        perts.append(dict(type="digit_change", line=ln, old=t.text, new=new_tok, text=l[:t.col] + l[t.col:].replace(t.text, new_tok, 1)))
    for _ in range(10):  # CI-bound swap
        ln = pick(ci_lines)
        l = lines[ln - 1]
        m = CI_RX.search(l.translate(AC.MINUS))
        s0, e0 = m.span()
        seg = l[s0:e0]
        mm = re.search(r"\[([^,\]]+),\s*([^\]]+)\]", seg)
        new_seg = seg[:mm.start()] + f"[{mm.group(2)}, {mm.group(1)}]" + seg[mm.end():]
        perts.append(dict(type="ci_bound_swap", line=ln, old=seg, new=new_seg, text=l[:s0] + new_seg + l[e0:]))
    for _ in range(10):  # estimator / fold relabel
        ln = pick(lab_lines)
        l = lines[ln - 1]
        opts = [(a, b) for a, b in LABEL_SWAPS if a in l]
        a, b = rng.choice(opts)
        perts.append(dict(type="estimator_fold_relabel", line=ln, old=a, new=b, text=l.replace(a, b, 1)))
    for _ in range(10):  # verdict flip
        ln = pick(ver_lines)
        l = lines[ln - 1]
        opts = [(a, b) for a, b in VERDICT_SWAPS if re.search(rf"\b{re.escape(a)}\b", l)]
        a, b = rng.choice(opts)
        perts.append(dict(type="verdict_flip", line=ln, old=a, new=b, text=re.sub(rf"\b{re.escape(a)}\b", b, l, count=1)))
    return perts


def seeded_injection(lines, hypo_text, line_arts, clean_det, seed: int = SEED, tag: str = "") -> dict:
    rng = random.Random(seed)
    clean_flag_lines = {ln for ln in clean_det["flagged"] if ln > 0}
    clean_reasons = {ln: set(v) for ln, v in clean_det["flagged"].items()}
    perts = perturb(lines, clean_flag_lines, _ref_start(lines), rng)
    scratch = list(lines)
    for p in perts:
        scratch[p["line"] - 1] = p["text"]
    (WS / "results" / f"seeded_report_scratch{tag}.md").write_text("\n".join(scratch))
    (WS / "results" / f"seeded_perturbations_SEALED{tag}.json").write_text(json.dumps(perts, indent=1, ensure_ascii=False))
    det = run_detector(scratch, hypo_text, line_arts)  # blind: sees only the perturbed text
    new_by_line = {ln: set(v) - clean_reasons.get(ln, set()) for ln, v in det["flagged"].items()}
    lost = det["flagged"].get(-1, set()) - clean_reasons.get(-1, set())
    lost_ids = {x.split(":", 1)[1] for x in lost}
    for p in perts:
        hit = bool(new_by_line.get(p["line"]))
        via_anchor = [cid for cid in lost_ids if CLAIM_BY_ID[cid]["rep"] and abs(CLAIM_BY_ID[cid]["rep"][0] - p["line"]) <= 3]
        p["detected"] = hit or bool(via_anchor)
        p["reasons"] = sorted(new_by_line.get(p["line"], set())) + [f"anchor_lost:{x}" for x in via_anchor]
    flagged_unpert = sorted(ln for ln, v in new_by_line.items() if v and ln > 0 and ln not in {p["line"] for p in perts})
    by_type = defaultdict(list)
    for p in perts:
        by_type[p["type"]].append(p["detected"])
    return dict(seed=seed, perturbations=perts, recall=sum(p["detected"] for p in perts) / len(perts),
                recall_by_type={k: sum(v) / len(v) for k, v in by_type.items()},
                new_flags_on_unperturbed_lines=flagged_unpert)


# ============================================================ paper-ready tables (cells carry their source)
def cell(display, src=None, kind="cont", check="value", needle=None):
    return dict(display=display, src=src, kind=kind, check=check, needle=needle)


def T(display):  # plain text cell, nothing to verify
    return cell(display, check="literal")


def num_cell(spec: str, kind: str = "cont", nd: int = 3) -> dict:
    v = source_value(spec)
    if kind == "count":
        d = f"{int(round(v)):,}"
    elif kind == "p":
        d = f"{v:.2g}" if v < 0.001 else (f"{v:.4f}" if v < 0.01 else f"{v:.3f}")
    elif kind == "pct":
        d = f"{100 * v:.1f}%"
    else:
        d = f"{v:.{nd}f}"
    return cell(d, spec, kind)


def ci_cells(lo_spec: str, hi_spec: str, nd: int = 3) -> tuple[dict, dict]:
    return num_cell(lo_spec, nd=nd), num_cell(hi_spec, nd=nd)


def build_tables(det: dict, m11: list[dict], verdicts: list[dict]) -> dict[str, list[dict]]:
    import checks
    from registry import P2, P3, P3T, P4, P5, P5X, P7, P8, P9, A2, P1E
    TB: dict[str, list[dict]] = {}
    RQ1V = next(v for v in verdicts if v["rule"].startswith("R1 dead"))

    # ---- T_design: final design as executed
    TB["T_design"] = [
        dict(construct=T("E_up (emergence label)"), definition=T("sustained-uptake onset label; POST-HOC primary promoted in iteration 2; confirmation only via the iteration-4 sealed fold"),
             source=cell("art_zw_JJGsUFSnd results/r1/verdict_heldout.json", P3 + "/r1/verdict_heldout.json", check="text", needle="E_up is a POST-HOC primary label")),
        dict(construct=T("A_cont (host anchoring)"), definition=T("mean pre-entry host share of the entry-year partners (exact OpenAlex subfield x block profiles); continuous primary after fallback 6"),
             source=cell("art_2Cd2JJypeGuA results/d2_summary.json", P7 + "/d2_summary.json", check="text", needle="A_cont (mean host share of partners' pre-entry works)")),
        dict(construct=T("CT (co-transfer)"), definition=T("share of entry partners that were origin companions in [e-5, e-1]"),
             source=cell("art_2Cd2JJypeGuA results/d2_summary.json", P7 + "/d2_summary.json", check="text", needle="co-transfer")),
        dict(construct=T("Y_strict (outcome)"), definition=T("W2 = [e+1, e+5] host papers by author-disjoint newcomers (count; PPML, concept-clustered)"),
             source=cell("art_2Cd2JJypeGuA results/d2_prereg.json", P7 + "/d2_prereg.json", check="text", needle="Y_strict")),
        dict(construct=T("EST_bin (binary establishment)"), definition=T("iteration-1 establishment: >= 5 W2 newcomer papers and presence in >= 3 of 5 W2 years; NULL on held-out (co-primary p 0.165)"),
             source=cell("art_WZ8fbLn79nCq results/heldout_post.json", P2 + "/heldout_post.json", check="text", needle="EST_bin")),
        dict(construct=T("Persistent-neighbour closure (R1b)"), definition=T("triadic closure among top-20 neighbours present in both y and y-1; secondary Holm-family row"),
             source=cell("art_zw_JJGsUFSnd results/tables/r1_holm_decisions.csv", P3T + "/r1_holm_decisions.csv", check="text", needle="closure_persist")),
        dict(construct=T("Folds"), definition=T("sha1 concept fold: MAIN 202 screen / 100 held-out (426-concept frame); each sealed fold opened once in iteration 4 behind hash-checked runners"),
             source=cell("art_htO_gJuUn6Pr results/main_population_hydrated.json", P5X + "/main_population_hydrated.json", check="text", needle="sha1")),
        dict(construct=T("MeSH second population"), definition=T("191 MeSH concepts never screened for D2; G4 covers biomedicine -> biomedicine host entries only"),
             source=cell("art_XGdzjWgi-a88 README.md", "round-4/experiment-9/src/README.md", check="text", needle="biomedicine → biomedicine")),
        dict(construct=T("Adopter design"), definition=T("W2 newcomer adopters vs exact-matched risk-set controls on bins (prior works, team size, host activity, first year); conditional logit m2 is the pre-declared primary"),
             source=cell("art_FZ2OCJwV6xHs results/match_balance.json", P5 + "/match_balance.json", check="text", needle="team_bin")),
        dict(construct=T("RQ1 status"), definition=T(f"{RQ1V['outcome_from_rule']}: {RQ1V['inputs']}. Structural precursors of sustained uptake are volume/churn correlates."),
             source=cell("art_zw_JJGsUFSnd results_note.md", "round-4/evaluation-3/src/results_note.md", check="text", needle="R1_DEAD")),
    ]
    # ---- T_flow: population flow
    RB = P7 + "/d2_robustness.csv"
    TB["T_flow"] = [
        dict(step=T("Concept frame (hydrated)"), n=num_cell("recompute:n_frame_concepts", "count"), unit=T("concepts"), note=T("SENS: all 426")),
        dict(step=T("MAIN screen fold"), n=num_cell("recompute:n_main_screen", "count"), unit=T("concepts"), note=T("sha1 fold")),
        dict(step=T("MAIN held-out fold"), n=num_cell("recompute:n_main_heldout", "count"), unit=T("concepts"), note=T("opened once, iteration 4")),
        dict(step=T("D2 screen MAIN entries (>= 5 partners)"), n=num_cell(P4 + "/rooting.json::screen/n_entries", "count"), unit=T("entries"), note=T("184 concepts")),
        dict(step=T("D2 screen co-primary estimation sample"), n=num_cell(RB + "::csv:spec=PRIMARY (MAIN);fe=secondary|N", "count"), unit=T("entries"),
             note=num_cell(RB + "::csv:spec=PRIMARY (MAIN);fe=secondary|G", "count")),
        dict(step=T("D2 screen primary estimation sample"), n=num_cell(RB + "::csv:spec=PRIMARY (MAIN);fe=primary|N", "count"), unit=T("entries"),
             note=num_cell(RB + "::csv:spec=PRIMARY (MAIN);fe=primary|G", "count")),
        dict(step=T("D2 held-out events"), n=num_cell(P2 + "/heldout_post.json::n_events", "count"), unit=T("entries"), note=num_cell(P2 + "/heldout_post.json::n_concepts", "count")),
        dict(step=T("D2 held-out co-primary sample"), n=num_cell(P2 + "/heldout_post.json::flags/secondary/N", "count"), unit=T("entries"), note=num_cell(P2 + "/heldout_post.json::flags/secondary/G", "count")),
        dict(step=T("MeSH events after F6 widening"), n=num_cell(P9 + "/events_mesh_summary.json::chosen/events", "count"), unit=T("entries"), note=num_cell(P9 + "/events_mesh_summary.json::widening_steps/2/concepts", "count")),
        dict(step=T("MeSH co-primary (R2) sample"), n=num_cell(P9 + "/g4_summary.json::R2/N", "count"), unit=T("entries"), note=num_cell(P9 + "/g4_summary.json::R2/G", "count")),
        dict(step=T("Adopter pairs (W2 newcomers)"), n=num_cell(P5 + "/frame_summary.json::primary/adopters/n_adopter_pairs_total", "count"), unit=T("pairs"),
             note=num_cell(P5 + "/frame_summary.json::primary/adopters/share_adopter_pairs_career_new_corpus", "pct")),
        dict(step=T("Adopter measurable pairs (prior corpus work)"), n=num_cell(P5 + "/frame_summary.json::primary/adopters/n_adopter_pairs_measurable_corpus", "count"), unit=T("pairs"), note=T("")),
        dict(step=T("Adopter matched strata"), n=num_cell(P5 + "/mechanism_results.json::descriptives/n_strata", "count"), unit=T("strata"),
             note=num_cell(P5 + "/mechanism_results.json::descriptives/n_concepts", "count")),
        dict(step=T("RQ1 held-out E_up onsets"), n=num_cell(P3T + "/r1_n_flow.csv::csv:step=n_onsets|value", "count"), unit=T("onsets"), note=T("")),
        dict(step=T("RQ1 held-out matched (after fallback)"), n=num_cell(P3T + "/r1_n_flow.csv::csv:step=n_matched|value", "count"), unit=T("onsets"),
             note=num_cell(P3T + "/r1_n_flow.csv::csv:step=n_matched_before_fallback|value", "count")),
    ]
    # ---- T_decision
    TB["T_decision"] = []
    for v in verdicts:
        q = v["rule_quote"]
        TB["T_decision"].append(dict(
            iteration=T(str(v["iteration"])), rule=T(v["rule"]),
            quote=cell(q[:400] + ("..." if len(q) > 400 else ""), checks.STRAT[v["iteration"]], check="text", needle=q[:120]) if q else T("RULE_NOT_RECORDED in gen_strat"),
            outcome=T(v["outcome_from_rule"]), inputs=T(v["inputs"]), report=T(f"{v['status']} (line {v['report_line']})"), source=T(v["source"])))
    # ---- T_caveats (grafting inferential caveats, held-out)
    HP = P2 + "/heldout_post.json"
    TB["T_caveats"] = [
        dict(test=T("CRV1 p (co-primary A_cont)"), heldout=num_cell(HP + "::flags/secondary/p_A", "p"), source=T("art_WZ8fbLn79nCq results/heldout_post.json")),
        dict(test=T("Holm p (A, CT)"), heldout=num_cell("recompute:holm_heldout_coprimary", "p"), source=T("recomputed from heldout_post.json")),
        dict(test=T("Wild-cluster bootstrap p"), heldout=num_cell(HP + "::flags/secondary/p_wild_A", "p"), source=T("heldout_post.json")),
        dict(test=T("Nativeness-permutation p (500 draws)"), heldout=num_cell(HP + "::nativeness_permutation_placebo/secondary/perm_p_two_sided_z", "p"), source=T("heldout_post.json")),
        dict(test=T("Placebo-calibrated p (screen SD)"), heldout=num_cell(HP + "::flags/secondary/p_placebo_cal_screenSD", "p"), source=T("heldout_post.json")),
        dict(test=T("Placebo-calibrated p (held-out SD)"), heldout=num_cell(HP + "::flags/secondary/p_placebo_cal_heldoutSD", "p"), source=T("heldout_post.json")),
        dict(test=T("Within-concept A-shuffle permutation p (200 draws; borderline)"), heldout=num_cell(A2 + "/audit_perm.json::perm_p_two_sided", "p"), source=T("audit/audit_perm.json")),
        dict(test=T("CRV1 rejection rate under null shuffles (anti-conservative)"), heldout=num_cell(A2 + "/audit_perm.json::share_crv1_p_lt_0.05", "pct"), source=T("audit/audit_perm.json")),
        dict(test=T("Shuffled-z SD (nominal 1)"), heldout=num_cell(A2 + "/audit_perm.json::z_sd", nd=2), source=T("audit/audit_perm.json")),
        dict(test=T("EST_bin LPM A_cont p (co-primary FE)"), heldout=num_cell(HP + "::EST_bin_LPM/secondary/p/A_cont", "p"), source=T("heldout_post.json EST_bin_LPM")),
        dict(test=T("EST_bin LPM A_cont p (primary FE)"), heldout=num_cell(HP + "::EST_bin_LPM/primary/p/A_cont", "p"), source=T("heldout_post.json EST_bin_LPM")),
        dict(test=T("Primary FE IRR/SD (G 30, inconclusive)"), heldout=num_cell(HP + "::flags/primary/irr_sd_A", nd=2), source=T("heldout_post.json")),
        dict(test=T("Primary heterogeneity screen vs held-out p"), heldout=num_cell(HP + "::flags/primary/heterogeneity_screen_vs_heldout/p", "p"), source=T("heldout_post.json")),
        dict(test=T("Co-primary heterogeneity screen vs held-out p"), heldout=num_cell(HP + "::flags/secondary/heterogeneity_screen_vs_heldout/p", "p"), source=T("heldout_post.json")),
        dict(test=T("Held-out spec-robustness rows significant (of 7)"), heldout=num_cell("recompute:heldout_robust_sig", "count"), source=T("recount of heldout_robustness.csv")),
        dict(test=T("G1 multi-team IRR/SD (held-out)"), heldout=num_cell(GHR_ + "::csv:row=G1-multi (co-primary FE);var=A_cont|irr_sd", nd=2), source=T("g_heldout_rows.csv")),
        dict(test=T("G1 multi-team p (held-out)"), heldout=num_cell(GHR_ + "::csv:row=G1-multi (co-primary FE);var=A_cont|p", "p"), source=T("g_heldout_rows.csv")),
        dict(test=T("G2a NATIVE Holm p (held-out)"), heldout=num_cell(GHR_ + "::csv:row=G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3));var=NAT|p_holm_G", "p"), source=T("g_heldout_rows.csv")),
        dict(test=T("G2a ADJACENT Holm p (held-out)"), heldout=num_cell(GHR_ + "::csv:row=G2a NATIVE+ADJACENT (native>=0.3, adjacent [0.05,0.3));var=ADJ|p_holm_G", "p"), source=T("g_heldout_rows.csv")),
        dict(test=T("G3(iii) venue-ASJC control (citation-independent)"), heldout=T("NOT ESTIMABLE (coverage ~12%; degenerate on screen, fails on held-out)"), source=T("g_heldout_rows.csv G3(iii) rows empty")),
        dict(test=T("Screen co-primary single-paper share (1,344 / 1,544)"), heldout=num_cell("recompute:single_paper_share_coprimary", "pct"), source=T("recount of d2_robustness.csv N")),
        dict(test=T("OOS deviance change on held-out (descriptive)"), heldout=num_cell(HP + "::oos/deviance_diff_with_minus_controls", nd=2), source=T("heldout_post.json oos")),
    ]
    # ---- T_rooting (type x rooting)
    RJ = P4 + "/rooting.json"
    TB["T_rooting"] = []
    for typ in ["BROAD", "LOCALISED"]:
        TB["T_rooting"].append(dict(
            type=T(typ), entries_per_concept=num_cell(RJ + f"::screen/descriptives/occupancy/{typ}/all_main_entries_per_concept", nd=1),
            EST_rate=num_cell(RJ + f"::screen/descriptives/{typ}/EST_rate/est", nd=2), raw_A_cont=num_cell(RJ + f"::screen/descriptives/{typ}/A_cont_mean/est", nd=3),
            CT=num_cell(RJ + f"::screen/descriptives/{typ}/CT_mean/est", nd=3),
            PPML_A_irr_sd=num_cell(RJ + f"::screen/model_iii_ppml/{typ}/irr_per_sd", nd=2),
            PPML_lo=num_cell(RJ + f"::screen/model_iii_ppml/{typ}/ci/0", nd=2), PPML_hi=num_cell(RJ + f"::screen/model_iii_ppml/{typ}/ci/1", nd=2)))
    TB["T_rooting"] += [
        dict(type=T("BROAD - LOCALISED raw A_cont (screen)"), entries_per_concept=T(""), EST_rate=T(""),
             raw_A_cont=num_cell(RJ + "::screen/descriptives/diff_BROAD_minus_LOCALISED/A_cont/diff"), CT=num_cell(RJ + "::screen/descriptives/diff_BROAD_minus_LOCALISED/CT/diff"),
             PPML_A_irr_sd=T("interaction p"), PPML_lo=num_cell(RJ + "::screen/model_iii_ppml/interaction_p", "p"), PPML_hi=T("exploratory")),
        dict(type=T("Adjusted (host x year FE) screen"), entries_per_concept=T(""), EST_rate=T(""),
             raw_A_cont=num_cell(RJ + "::screen/model_i_Acont/coef", nd=4), CT=num_cell(RJ + "::screen/model_ii_CT/coef"), PPML_A_irr_sd=T("BROAD higher host share: FAILED"), PPML_lo=T(""), PPML_hi=T("")),
        dict(type=T("Adjusted (host x year FE) held-out"), entries_per_concept=T(""), EST_rate=T(""),
             raw_A_cont=num_cell(RJ + "::heldout/model_i_Acont/coef", nd=4), CT=num_cell(RJ + "::heldout/model_ii_CT/coef"), PPML_A_irr_sd=T("BROAD lower CT: REPLICATED"),
             PPML_lo=num_cell(RJ + "::heldout/model_ii_CT/ci/0"), PPML_hi=num_cell(RJ + "::heldout/model_ii_CT/ci/1")),
    ]
    # ---- T_rq1
    PP, ES, IV = P3T + "/r1_pooled_panel_screen_vs_heldout.csv", P3T + "/r1_event_study_screen_vs_heldout.csv", P3T + "/r1_iv_synthesis_descriptive.csv"
    TB["T_rq1"] = []
    for row in ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "wmz", "effsize"]:
        TB["T_rq1"].append(dict(
            row=T(row), estimator=T("pooled panel"),
            screen=num_cell(PP + f"::csv:row={row}|coef_screen") if row not in ("effsize",) else T("-"),
            heldout=num_cell(PP + f"::csv:row={row}|coef_heldout"), lo=num_cell(PP + f"::csv:row={row}|ci_heldout_lo"), hi=num_cell(PP + f"::csv:row={row}|ci_heldout_hi"),
            holm=num_cell(f"recompute:holm_rq1_{row}", "p") if row in ("closure", "closure_resT", "closure_persist") else T("-"),
            decision=T(next((r["decision"] for r in AC.load_csv(P3T + "/r1_holm_decisions.csv") if r["row"] == row and r["estimator"] == "pooled_panel"), "descriptive"))))
    for row in ["closure", "closure_resT", "closure_persist", "constraint", "xc_excess", "wmz", "effsize"]:
        TB["T_rq1"].append(dict(
            row=T(row), estimator=T("event study"), screen=num_cell(ES + f"::csv:row={row}|S_screen"), heldout=num_cell(ES + f"::csv:row={row}|S_heldout"),
            lo=num_cell(ES + f"::csv:row={row}|ci_heldout_lo"), hi=num_cell(ES + f"::csv:row={row}|ci_heldout_hi"),
            holm=num_cell(HD_ + "::csv:row=constraint|p_one_holm", "p") if row == "constraint" else T("-"),
            decision=T("DEAD" if row == "constraint" else "descriptive")))
    for row in ["closure", "closure_resT", "closure_persist", "constraint"]:
        TB["T_rq1"].append(dict(row=T(row), estimator=T("IVW screen+held-out (descriptive)"), screen=T("-"), heldout=num_cell(IV + f"::csv:row={row}|S_pooled"),
                                lo=num_cell(IV + f"::csv:row={row}|ci_lo"), hi=num_cell(IV + f"::csv:row={row}|ci_hi"), holm=T("-"), decision=T("DESCRIPTIVE, NOT A DECISION")))
    TB["T_rq1"] += [
        dict(row=T("H-matched subset closure_resT (n 11)"), estimator=T("event study"), screen=T("-"), heldout=num_cell(P3T + "/r1_n_flow.csv::csv:step=H_matched_S_closure_resT|value"),
             lo=T("-0.933"), hi=T("-0.133"), holm=T("-"), decision=T("sensitivity")),
        dict(row=T("Balance: H SMD at k=0"), estimator=T("matching"), screen=T("-"), heldout=num_cell(P3T + "/r1_balance_smd.csv::csv:covariate=H;k=0|smd", nd=2),
             lo=T(""), hi=T(""), holm=T("-"), decision=T("imperfect")),
        dict(row=T("Covariates with |SMD| > 0.25 (of 11)"), estimator=T("matching"), screen=T("-"), heldout=num_cell("recompute:rq1_smd_flag_count", "count"),
             lo=T(""), hi=T(""), holm=T("-"), decision=T("")),
        dict(row=T("Event-study controls that are screen concepts (of 25)"), estimator=T("matching"), screen=T("-"),
             heldout=num_cell(P3T + "/r1_n_flow.csv::csv:step=controls_from_screen|value", "count"), lo=T(""), hi=T(""), holm=T("-"), decision=T("fallback fired")),
        dict(row=T("RQ1 VERDICT"), estimator=T("frozen kill rule (iteration-4 strategy)"), screen=T("-"), heldout=T(RQ1V["outcome_from_rule"]), lo=T(""), hi=T(""),
             holm=T(""), decision=T("Structural precursors of sustained uptake are volume/churn correlates")),
    ]
    # ---- T_adopter
    EN, VC, SUP = P5 + "/enrichment.json", P5 + "/vocab_class.json", P5 + "/supplementary.json"

    def orow(label, base, term, note=""):
        return dict(exposure=T(label), OR=num_cell(base + f"/terms/{term}/OR", nd=2), lo=num_cell(base + f"/terms/{term}/OR_ci95_boot/0", nd=2),
                    hi=num_cell(base + f"/terms/{term}/OR_ci95_boot/1", nd=2), note=T(note))
    TB["T_adopter"] = [
        orow("E_any, pre-declared primary m2", EN + "::m2", "E_any", "prevalence 0.79 vs 0.61; risk ratio ~1.30; NOT '3.1x more likely'"),
        orow("E_any, m1 (not primary)", EN + "::m1", "E_any", "value the report printed"),
        orow("E_neg (frequency-matched negative-control concepts), m2", EN + "::m2", "E_neg"),
        orow("E_plac (partners of another concept's entry into the same host), m_plac", EN + "::m_plac", "E_plac"),
        orow("E_swap", EN + "::m_swap", "E_swap"),
        orow("E_for (FOREIGN partners)", VC + "::m_voc", "E_for"), orow("E_adj (ADJACENT)", VC + "::m_voc", "E_adj"), orow("E_nat (NATIVE)", VC + "::m_voc", "E_nat"),
        orow("E_any x A_cont interaction", P5 + "/interaction.json::m_int", "E_any_x_zA"),
        dict(exposure=T("Robustness: 1:3 matched"), OR=num_cell(SUP + "::one_to_three_matched/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Robustness: expanded frame (no concept cap)"), OR=num_cell(SUP + "::expanded_frame_no_concept_cap/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Robustness: Physics/Astro"), OR=num_cell(SUP + "::field_Physics_Astro/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Robustness: CS"), OR=num_cell(SUP + "::field_CS/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Robustness: single-paper entries"), OR=num_cell(SUP + "::single_paper_entries/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Robustness: multi-paper entries"), OR=num_cell(SUP + "::multi_paper_entries/terms/E_any/OR", nd=2), lo=T(""), hi=T(""), note=T("")),
        dict(exposure=T("Post-hoc origin-subfield check: partner OR given origin"), OR=num_cell(SUP + "::origin_subfield_check/primary/partner_given_origin/terms/E_any/OR", nd=2),
             lo=T(""), hi=T(""), note=T("post-hoc")),
        dict(exposure=T("Native/foreign exposure ratio"), OR=num_cell(P5 + "/ratios.json::native_vs_foreign/ratio", nd=2), lo=num_cell(P5 + "/ratios.json::native_vs_foreign/ci95_boot/0", nd=2),
             hi=num_cell(P5 + "/ratios.json::native_vs_foreign/ci95_boot/1", nd=2), note=T("")),
        dict(exposure=T("Coverage: adopter pairs without prior corpus work (excluded)"), OR=num_cell(P5 + "/frame_summary.json::primary/adopters/share_adopter_pairs_career_new_corpus", "pct"),
             lo=T(""), hi=T(""), note=T("of 21,941 pairs; exposure is corpus-only (0 OpenAlex credits spent: api_results.json)")),
        dict(exposure=T("Reading"), OR=T("consistent with absorptive capacity OR topical proximity"), lo=T(""), hi=T(""), note=T("Jia, Wang & Szymanski 2017 local interest drift is the rival")),
    ]
    # ---- T_mesh
    RM = "round-4/experiment-9/src/README.md"
    G4 = P9 + "/g4_summary.json"
    TB["T_mesh"] = [
        dict(item=T("Scope caveat 1 (verbatim)"), value=cell("G4 therefore speaks to **biomedicine → biomedicine** entries only.", RM, check="text", needle="G4 therefore speaks to **biomedicine → biomedicine** entries only."), n=T("")),
        dict(item=T("Coverage rule removes share of partner-qualified entries"), value=num_cell(P9 + "/events_mesh_summary.json::removed_by_coverage_among_kw/share", "pct"), n=T("")),
        dict(item=T("Declared kw5 + coverage-0.50 design events (F6 widening fired)"), value=num_cell(P9 + "/events_mesh_summary.json::widening_steps/0/events", "count"),
             n=num_cell(P9 + "/events_mesh_summary.json::widening_steps/0/design_G_non_singleton", "count")),
    ]
    for rid, lab in [("R1", "R1 primary FE"), ("R2", "R2 co-primary"), ("R3", "R3 concept + d x e"), ("R4", "R4 concept x 2yr + d x e"), ("S3", "S3 placebo host"),
                     ("S16", "exact-profile nativeness only"), ("S5", "unprofiled = 1 bound"), ("S6", "S6 coverage-0.50 subset (declared)"), ("S1", "G1 multi-team")]:
        TB["T_mesh"].append(dict(item=T(lab), value=num_cell(G4 + f"::rows/{rid}/irr_sd", nd=3), n=num_cell(G4 + f"::rows/{rid}/N", "count")))
    # ---- T_missing (MISSING_IN_REPORT rows for exp_1-exp_4 from art__i2cIye01VnN)
    REC = P1E + "/record_of_numbers.csv"
    TB["T_missing"] = []
    for i, r in enumerate(AC.load_csv(REC)):
        if r["flag"] != "MISSING_IN_REPORT":
            continue
        TB["T_missing"].append(dict(id=cell(r["id"], REC + f"::csv:id={r['id']}|id", check="exact"), block=T(r["block"]), claim=T(r["claim"]),
                                    value=cell(r["value"], REC + f"::csv:id={r['id']}|value", check="exact"), ci_lo=T(r["ci_lo"]), ci_hi=T(r["ci_hi"]), n=T(r["n"]),
                                    source=T(r["source_path"] + " :: " + r["source_key"]),
                                    highlight=T("SENS2" if "SENS2" in r["id"] else ("r1a" if "r1a" in r["id"].lower() or "r1a" in r["claim"].lower() else
                                                                                    ("Granger" if "granger" in (r["id"] + r["claim"]).lower() else "")))))
    # ---- T_table18
    TB["T_table18"] = [dict(item=T(m["item"]), claimed=cell(m["claimed"][:60], AC.REPORT_REL, check="text", needle="| " + m["item"] + " |"),
                            status=T(m["status"]), evidence_lines=T(m["evidence"]), still_open=T(m["open"])) for m in m11]
    # ---- T_coverage
    TB["T_coverage"] = [
        dict(activity=T("1. Prepare and semantically ground dataset"), status=T("Done"), artifacts=T("art_94GEMUsgAmgK, art_QpM5SM6a7SH6, art_BdBvbNuNU8E7, art_eR1Z7fMlOcxs"),
             caveat=T("grounding covers focal concepts; co-word nodes are Wikidata-linked legacy OpenAlex concepts")),
        dict(activity=T("2. Construct evolving knowledge network"), status=T("Done"), artifacts=T("art_mbFjmo5rbbf8, art_eR1Z7fMlOcxs"), caveat=T("25 yearly snapshots; variant merger recall low")),
        dict(activity=T("3. RQ1 temporal network analysis"), status=T("Done; R1_DEAD"), artifacts=T("art_mbFjmo5rbbf8, art_htO_gJuUn6Pr, art_zw_JJGsUFSnd"),
             caveat=cell("R1_DEAD under the frozen kill rule; structural precursors are volume/churn correlates", "round-4/evaluation-3/src/results_note.md", check="text", needle="R1_DEAD")),
        dict(activity=T("4. RQ2 cross-disciplinary diffusion"), status=T("Done; D2 confirmed on held-out + MeSH (biomed -> biomed)"), artifacts=T("art_2Cd2JJypeGuA, art_WZ8fbLn79nCq, art_XGdzjWgi-a88, art_FZ2OCJwV6xHs"),
             caveat=T("count outcome only (EST_bin null); within-concept permutation p 0.050; primary FE underpowered")),
        dict(activity=T("5. Recurring trajectories"), status=T("Done; k = 2 replicates on held-out; MeSH outside support"), artifacts=T("art_QKsLguxnGFQT, art_mu0h0npvNX_u"),
             caveat=num_cell(P4 + "/mesh_results.json::typology/distances/ks_vs_screen_d1/p", "p")),
        dict(activity=T("6. Representative cases"), status=T("Done (4 cases; cases.md)"), artifacts=T("art_mu0h0npvNX_u"),
             caveat=cell("results/case_interpretations.md", P4 + "/case_interpretations.md", check="text", needle="Case interpretations")),
    ]
    return TB


GHR_ = "round-4/evaluation-2/src/results/g_heldout_rows.csv"
HD_ = "round-4/evaluation-3/src/results/tables/r1_holm_decisions.csv"


def write_tables(TB: dict, results: dict) -> None:
    import csv as _csv
    for name, rows in TB.items():
        if not rows:
            continue
        cols = list(rows[0].keys())
        cells = [dict(table=name, row=i, col=c, **rows[i][c]) for i in range(len(rows)) for c in cols]
        (WS / "tables" / f"{name}.cells.json").write_text(json.dumps(cells, indent=1, ensure_ascii=False, default=str))
    # the assertion script decides which tables ship
    proc = subprocess.run([sys.executable, str(WS / "audit_tables.py"), "check-dir", str(WS / "tables"), "--out", str(WS / "results" / "table_assertions.json")],
                          capture_output=True, text=True, timeout=1800)
    logger.info("audit_tables.py: " + proc.stdout.strip()[-800:])
    if proc.returncode not in (0, 1):
        logger.error(proc.stderr[-2000:])
        raise RuntimeError("audit_tables.py crashed")
    ta = json.loads((WS / "results" / "table_assertions.json").read_text())
    results["table_assertions"] = ta
    for name, rows in TB.items():
        st = ta["tables"].get(name, {})
        if not st.get("pass"):
            for ext in ("csv", "md"):
                (WS / "tables" / f"{name}.{ext}").unlink(missing_ok=True)
            logger.warning(f"table {name} NOT emitted: {st.get('n_fail')} failing cells")
            continue
        cols = list(rows[0].keys())
        with open(WS / "tables" / f"{name}.csv", "w", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(cols)
            for r in rows:
                w.writerow([r[c]["display"] for c in cols])
        md = [f"# {name}", "", "| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
        for r in rows:
            md.append("| " + " | ".join(str(r[c]["display"]).replace("|", "/").replace("\n", " ") for c in cols) + " |")
        srcs = sorted({str(r[c]["src"]).split("::")[0] for r in rows for c in cols if r[c]["src"] and not str(r[c]["src"]).startswith("recompute:")})
        md += ["", "Sources (run-root-relative): " + "; ".join(srcs), f"Assertion: every sourced cell re-read by audit_tables.py ({st.get('n_checked')} cells, 0 failures)."]
        (WS / "tables" / f"{name}.md").write_text("\n".join(md) + "\n")


# ============================================================ Table 18 honesty (M11)
def table18_honesty(lines: list[str], det: dict) -> list[dict]:
    txt = "\n".join(lines)
    it4 = next(i for i, l in enumerate(lines) if l.startswith("# Iteration 4")) + 1

    def has(rx, lo=1, hi=None):
        hi = hi or len(lines)
        return [i + 1 for i in range(lo - 1, hi) if re.search(rx, lines[i])]

    drift_it13 = sorted({int(r["line"]) for r in det["drift"] if r["line"] and int(r["line"]) < it4})
    markers = has(r"\[Correction, iteration 4", 1, it4)
    unmarked = [ln for ln in drift_it13 if not re.search(r"Correction", lines[ln - 1])]
    t14 = has(r"^\| Measure \| S \| 95% CI \| Interpretation \|")
    out = [
        dict(item="M1", claimed="iterations 1-3 carried verbatim; inline [Correction] markers where artifacts disproved numbers",
             status="PARTIAL" if markers and unmarked else ("DONE" if not unmarked else "NOT DONE"),
             evidence=f"iteration-4 correction markers at lines {markers}; drift lines in iterations 1-3 without a marker: {unmarked[:20]}",
             open="add [Correction, iteration 4/5] markers at every drift line listed in report_drift.csv before line %d" % it4),
        dict(item="M2", claimed="Holm columns and detail rows added to iteration-3 tables",
             status="NOT DONE" if t14 and "Holm" not in lines[t14[0] - 1] else "DONE",
             evidence=f"Table 14 header at line {t14} has no Holm column", open="add Holm column to Table 14 (T_rq1 has the held-out Holm values)"),
        dict(item="M3", claimed="robustness count corrected inline (26/27 -> 20/26) with null-row list",
             status="PARTIAL", evidence=f"correction note at {has(r'Correction, iteration 4: the co-primary robustness')}; '26 of 27' still at {has(r'26 of 27')}; the note mis-defines 20/26 as excluding base and strata",
             open="replace at line 551; restate '20 of 26 incl.; 18 of 22 excl.'"),
        dict(item="M4", claimed="closure claim graded by held-out outcome",
             status="PARTIAL" if any(v["flag"] == "VERDICT_DRIFT" and "R1" in v["rule"] for v in det["verdicts"]) else "DONE",
             evidence=f"Artifact 18 body says 'not confirmed' (line {has(r'Overall closure status: not confirmed')}); summary line 7 and heading line {has(r'persistent-neighbour closure survives')} rescue R1; 'R1_DEAD' at {has(r'R1_DEAD')}",
             open="state R1_DEAD and the volume/churn sentence in summary, heading and fig_methodology"),
        dict(item="M5", claimed="full lead-lag category-count table added (Table 21)",
             status="DONE" if has(r"Table 21\. Lead-lag category counts") else "NOT DONE",
             evidence=f"Table 21 at {has(r'Table 21. Lead-lag')}; all 24 counts re-derived (ll.* rows OK); MeSH null p 0.43, log-rank, Granger still missing",
             open="add MeSH null (p 0.43), log-rank p 0.005, F<=2012 cohort 12, Granger b -0.0013 p 0.068"),
        dict(item="M6", claimed="iteration-3 Strategy expanded; iteration-4 decision rules are the held-out specs",
             status="NOT DONE" if not has(r"DECISION RULES FOR THE PAPER") else "DONE",
             evidence=f"'DECISION RULES FOR THE PAPER' at {has(r'DECISION RULES FOR THE PAPER')}; iteration-4 Strategy is {len(has(r'.', it4, it4 + 8))} lines",
             open="copy the iteration-4 decision rules verbatim (T_decision) into the Strategy"),
        dict(item="M7", claimed="coverage table updated with caveats",
             status="DONE" if has(r"^\| Activity \| Status \| Artifact \| Caveats \|") else "NOT DONE",
             evidence=f"coverage header with Caveats at {has(r'^[|] Activity [|] Status [|] Artifact [|] Caveats [|]')}; activity 6 status still Partial (line {has(r'not individually interpreted')})",
             open="set activity 6 to Done (cases.md)"),
        dict(item="M8", claimed="all [ARTIFACT:] markers use artifact IDs",
             status="PARTIAL" if any(a["id"] == "A.art2_id" and a["flag"] != "OK" for a in det["asserts"]) else "DONE",
             evidence=f"Artifact 2 marker at {has(r'calibrate host-nativeness profiles .ARTIFACT:art_eR1Z7fMlOcxs')} points to dataset_5's id",
             open="cite 3_invention_loop/iter_1/gen_art/gen_art_dataset_2 for Artifact 2"),
        dict(item="M9", claimed="prior-review must-fix items incorporated where data are available",
             status="NOT DONE" if not has(r"SENS2") and not has(r"Granger") else "PARTIAL",
             evidence=f"SENS2 at {has(r'SENS2')}, Granger at {has(r'Granger')}, MISSING_IN_REPORT count at {has(r'MISSING_IN_REPORT')}",
             open="transcribe T_missing (292 rows) incl. SENS2, r1a correlations, Granger"),
        dict(item="M10", claimed="nearest-neighbour comparison two-sided (Cheng tension, Guevara)",
             status="DONE" if has(r"Guevara") and has(r"Cheng et al\. \[13\] find") else "NOT DONE",
             evidence=f"Guevara at {has(r'Guevara')[:3]}, Cheng tension at {has(r'Cheng et al. .13. find')}", open="add Jia 2017 / Hofstra 2020 for the adopter result"),
        dict(item="m1", claimed="minor slips corrected: robustness count, Holm p precision, denominator labels",
             status="NOT DONE" if not has(r"S_raw_cc") and not has(r"n_matched = 14|14 matched") else "PARTIAL",
             evidence=f"S_raw_cc at {has(r'S_raw_cc')}; fresh-replication n_matched 14 at {has(r'n_matched = 14|14 matched')}",
             open="label Table 13 S_raw as S_raw_cc; give n_matched = 14 at line 432"),
    ]
    return out


# ============================================================ review closure (M8)
def review_closure(tables_ok: dict, drift: list[dict], verdicts: list[dict], cases_ok: bool) -> list[dict]:
    dl = {r["claim_id"] for r in drift}
    known = {r["known"] for r in drift}

    def st(parts):
        n = sum(parts)
        return "CLOSED" if n == len(parts) else ("PARTIAL" if n else "OPEN")
    items = [
        ("1 RQ1 headline contradicts the frozen kill rule", [tables_ok.get("T_rq1", False), "K01_rq1_rescue_summary" in known, "K02_learned_heading" in known, tables_ok.get("T_design", False)],
         "T_rq1 (R1_DEAD row), T_design (RQ1 status), report_drift.csv lines 7 / 867, A.fig_methodology"),
        ("2 Table 18 claims fixes not made", [tables_ok.get("T_table18", False), "d2.scr.pri.ct_p" in dl, "d2.scr.robust.count2" in dl],
         "T_table18, report_drift.csv (CT p 0.48 -> 0.85; '26 of 27')"),
        ("3 grafting caveats dropped", [tables_ok.get("T_caveats", False), "g1.pooled.multi" in dl, "d2.scr.single_share" in dl],
         "T_caveats; report_drift.csv (Table 20 multi 1.14/1.09; '83%')"),
        ("4 MeSH and adopter read too broadly", [tables_ok.get("T_mesh", False), tables_ok.get("T_adopter", False), "A.cross_domain" in dl, "K09_or_31x" in known, "K10_neg_plac_matching" in known],
         "T_mesh, T_adopter, report_drift.csv (cross-domain, 3.1x, NEG/PLAC/matching)"),
        ("5 RQ2 descriptive results and cases missing", [cases_ok, tables_ok.get("T_rooting", False), "K11_k2_mesh" in known, "K12_mesh_leadlag" in known],
         "cases.md, T_rooting, report_drift.csv (k=2 on MeSH; MeSH lead-lag)"),
        ("6 decision rules not recorded", [tables_ok.get("T_decision", False), all(v["rule_recorded"] or v["status"] == "RULE_NOT_RECORDED" for v in verdicts)],
         "T_decision (verbatim quotes, outcome per rule)"),
    ]
    return [dict(item=i, status=st(p), closed_by=w, components_ok=f"{sum(p)}/{len(p)}") for i, p, w in items]


# ============================================================ cases.md and closed strands
def write_cases() -> bool:
    from registry import P4
    md = (AC.RUN_ROOT / P4 / "case_interpretations.md").read_text().split("\n")
    cr = AC.load_json(P4 + "/cases_rooting.json")
    ents = AC.load_csv(P4 + "/case_entries.csv")
    out = ["# Representative cases (transcribed for the paper)", "",
           "Source: art_mu0h0npvNX_u `3_invention_loop/iter_4/gen_art/gen_art_evaluation_4/results/case_interpretations.md` "
           "(line numbers below), `cases_rooting.json`, `case_entries.csv`. Paragraphs are verbatim; the per-case entry counts and "
           "rooted-minus-unrooted A_cont are recomputed from case_entries.csv and must equal the text.", ""]
    ok = True
    cur = None
    for i, l in enumerate(md, 1):
        if l.startswith("## "):
            cur = l[3:]
            out += [f"## {cur}", f"*(source lines {i}-)*", ""]
            continue
        if cur and l.strip():
            out.append(l + f"  <!-- src L{i} -->")
            out.append("")
    out += ["## Recomputed per-case entry statistics (co-primary sample)", "", "| concept | entries | rooted | mean A_cont rooted | mean A_cont unrooted | diff |", "|---|---|---|---|---|---|"]
    for ph in sorted({e["phrase"] for e in ents}):
        rows = [e for e in ents if e["phrase"] == ph and e["in_coprimary_sample"] == "True"]
        r = [float(e["A_cont"]) for e in rows if e["EST_bin"] == "1"]
        u = [float(e["A_cont"]) for e in rows if e["EST_bin"] != "1"]
        diff = (sum(r) / len(r) - sum(u) / len(u)) if r and u else float("nan")
        out.append(f"| {ph} | {len(rows)} | {len(r)} | {sum(r) / len(r) if r else float('nan'):.3f} | {sum(u) / len(u) if u else float('nan'):.3f} | {diff:+.3f} |")
        if r and u:
            needle = f"+{diff:.3f}"
            if needle not in "\n".join(md):
                ok = False
                out.append(f"<!-- ASSERTION FAILED: {needle} not in case_interpretations.md -->")
    out += ["", f"cases_rooting.json top-level keys: {', '.join(list(cr.keys())[:12])}"]
    (WS / "tables" / "cases.md").write_text("\n".join(out) + "\n")
    return ok


CLOSED = [
    ("D1 openness -> breadth", "screen Holm p 0.405 for all three outcomes; all six held-out sensitivity cells include 0 (art_62TVG6A4f7Iy, art_zw_JJGsUFSnd)"),
    ("Citation-lineage viability (source-sink)", "Gate A failed: 17.3% of edge-years reach within-host share 0.40 (< 50% required) (art_yjFB8Spw2w6M)"),
    ("Co-transfer as mechanism", "CT null in every spec and population (screen primary p 0.85, co-primary 0.48; held-out 0.60; MeSH Holm 0.053)"),
    ("3-channel typology gain over entropy", "residualised newcomer-share eps2 0.171 vs 0.178; CIs overlap (art_QKsLguxnGFQT)"),
    ("Roles -> entry", "lagged BRIDGE OR 0.64 [0.38, 1.08] screen vs 1.86 held-out; E4 FAIL (art_mu0h0npvNX_u)"),
    ("D3 closure-anchoring link", "partial rho +0.025 screen, +0.053 held-out, CIs include 0; unifying sentence dropped (art_zw_JJGsUFSnd)"),
    ("RQ1 structural precursors", "R1_DEAD: pooled-panel held-out raw closure Holm 0.147; volume/churn correlates (art_zw_JJGsUFSnd)"),
    ("Demic/cultural routes", "not run; the adopter test is the nearest evidence (art_FZ2OCJwV6xHs)"),
]


# ============================================================ independent re-derivation (M6)
def independent_sample(claims: list[dict]) -> list[dict]:
    rng = random.Random(SEED)
    elig = [c for c in claims if c["source"] and c["source_value"] not in (None, "") and not c["source_error"]
            and isinstance(c["source_value"], (int, float))]
    by_block = defaultdict(list)
    for c in elig:
        by_block[c["block"]].append(c)
    pick: dict[str, dict] = {}
    for b, lst in by_block.items():
        for c in rng.sample(lst, min(8, len(lst))):
            pick[c["id"]] = c
    rest = [c for c in elig if c["id"] not in pick]
    rng.shuffle(rest)
    while len(pick) < 50 and rest:
        c = rest.pop()
        pick[c["id"]] = c
    for c in elig:  # all verdict-bearing / headline numbers
        if c["headline"]:
            pick[c["id"]] = c
    return [dict(id=c["id"], block=c["block"], src=c["source"], kind=CLAIM_BY_ID[c["id"]]["kind"], audit_value=c["source_value"],
                 report_value=c["report_value"], headline=c["headline"]) for c in pick.values()]


def run_independent(claims: list[dict]) -> dict:
    items = independent_sample(claims)
    sp, op = WS / "results" / "indep_sample.json", WS / "results" / "indep_rederived.json"
    sp.write_text(json.dumps(items, indent=1, default=str))
    proc = subprocess.run([sys.executable, str(WS / "rederive_independent.py"), str(sp), str(op)], capture_output=True, text=True, timeout=1800)
    logger.info("rederive_independent.py: " + proc.stdout.strip()[-300:])
    if proc.stderr.strip():
        logger.warning(proc.stderr.strip()[-1500:])
    res = json.loads(op.read_text())
    agree = 0
    for it in res:
        a, b = it["audit_value"], it.get("indep_value")
        ok = b is not None and (abs(float(a) - float(b)) <= 1e-9 * max(1.0, abs(float(a))))
        it["agree"] = bool(ok)
        agree += ok
    blocks = Counter(i["block"] for i in res)
    return dict(n=len(res), n_agree=agree, rate=agree / len(res) if res else float("nan"), per_block=dict(blocks),
                disagreements=[i for i in res if not i["agree"]], items=res)


# ============================================================ main
@logger.catch(reraise=True)
def main() -> None:
    t0 = time.time()
    lines = AC.read_report()
    hypo_text = json.loads((AC.RUN_ROOT / AC.HYPO_REL).read_text())["hypothesis"]
    frz = freeze(lines, hypo_text)  # nothing from an artifact has been opened before this line
    results: dict = dict(spec=frz["spec"])

    line_arts = line_artifacts(lines)
    logger.info("building per-artifact numeric indexes ...")
    for a in sorted(AC.ARTIFACTS):
        get_index(a)
    logger.info(f"indexes built for {len(_INDEX)} artifacts ({sum(len(i.values) for i in _INDEX.values())} values) in {time.time() - t0:.0f}s")

    det = run_detector(lines, hypo_text, line_arts)
    claims, verdicts, asserts, scan = det["claims"], det["verdicts"], det["asserts"], det["scan"]
    det["drift"] = drift_list(det, lines)
    logger.info(f"claims {Counter(c['flag'] for c in claims)}; verdict mismatches {sum(v['flag'] == 'VERDICT_DRIFT' for v in verdicts)}; "
                f"assertion flags {sum(a['flag'] != 'OK' for a in asserts)}; drift rows {len(det['drift'])}")

    # ---------------- record_of_numbers_final.csv
    import csv as _csv
    rcols = ["id", "block", "claim", "fold_label", "estimator", "artifact", "source", "source_value", "recomputed", "recompute_method", "tier",
             "report_line", "report_value", "hyp_value", "hyp_agrees", "flag", "alt_match", "replacement", "headline", "known", "source_error", "note"]
    with open(WS / "results" / "record_of_numbers_final.csv", "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=rcols, extrasaction="ignore")
        w.writeheader()
        for c in claims:
            w.writerow({k: (fmt(c[k]) if isinstance(c.get(k), float) else c.get(k, "")) for k in rcols})
    with open(WS / "results" / "report_drift.csv", "w", newline="") as fh:
        cols = ["line", "report_text", "reported", "correct_text", "flag", "severity", "source", "claim_id", "known"]
        w = _csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in det["drift"]:
            w.writerow(r)
    (WS / "results" / "verdict_cells.json").write_text(json.dumps(det["vcells"], indent=1, ensure_ascii=False))
    (WS / "results" / "fold_checks.json").write_text(json.dumps(det["folds"], indent=1, ensure_ascii=False))
    (WS / "results" / "verdict_consistency.json").write_text(json.dumps(verdicts, indent=1, ensure_ascii=False))
    (WS / "results" / "assertions.json").write_text(json.dumps(asserts, indent=1, ensure_ascii=False))
    with open(WS / "results" / "autoscan_tokens.csv", "w", newline="") as fh:
        w = _csv.DictWriter(fh, fieldnames=["line", "col", "token", "sig", "status", "n_hits", "example_hit"])
        w.writeheader()
        for s in scan:
            w.writerow(s)

    # ---------------- M1 / M2 / M3
    blocks = BLOCK_ORDER
    in_report = [c for c in claims if c["report_value"]]
    m1 = {b: (sum(c["traced"] for c in claims if c["block"] == b) / max(1, sum(1 for c in claims if c["block"] == b))) for b in blocks}
    m1_overall = sum(c["traced"] for c in claims) / len(claims)
    toks = [s for s in scan if s["status"] in ("TRACED_AUTO", "UNTRACED", "FOLD_LABEL_CONFLICT")]
    toks2 = [s for s in toks if s["sig"] >= 2]
    toks3 = [s for s in toks if s["sig"] >= 3]
    auto_rate = sum(s["status"] != "UNTRACED" for s in toks) / max(1, len(toks))
    auto_rate2 = sum(s["status"] != "UNTRACED" for s in toks2) / max(1, len(toks2))
    auto_rate3 = sum(s["status"] != "UNTRACED" for s in toks3) / max(1, len(toks3))
    by_iter = defaultdict(lambda: [0, 0])
    for s in toks2:
        it = AC.iteration_of_line(lines, s["line"])
        by_iter[it][0] += s["status"] != "UNTRACED"
        by_iter[it][1] += 1
    traced_rep = [c for c in in_report if c["traced"]]
    tierR = [c for c in traced_rep if c["tier"] == "R"]
    tierC = [c for c in traced_rep if c["tier"] == "C"]
    m2 = dict(overall=sum(c["flag"] == "OK" for c in traced_rep) / max(1, len(traced_rep)),
              tier_R=sum(c["flag"] == "OK" for c in tierR) / max(1, len(tierR)), n_R=len(tierR),
              tier_C=sum(c["flag"] == "OK" for c in tierC) / max(1, len(tierC)), n_C=len(tierC))
    head = [c for c in claims if c["headline"]]
    m2["headline_n"] = len(head)
    m2["headline_tier_C"] = sum(c["tier"] == "C" for c in head)
    m2["headline_not_tier_C"] = [c["id"] for c in head if c["tier"] != "C"]
    flag_tab = defaultdict(Counter)
    for c in claims:
        flag_tab[c["block"]][c["flag"]] += 1
    for a in asserts:
        if a["flag"] != "OK":
            flag_tab["text-assertions"][a["flag"]] += 1
    for v in verdicts:
        flag_tab["verdicts"][v["flag"]] += 1
    with open(WS / "results" / "flags_by_block.csv", "w", newline="") as fh:
        allf = AC.FLAGS + ["RULE_NOT_RECORDED"]
        w = _csv.writer(fh)
        w.writerow(["block"] + allf + ["total"])
        for b, cnt in flag_tab.items():
            w.writerow([b] + [cnt.get(f, 0) for f in allf] + [sum(cnt.values())])

    # ---------------- M4 known-drift gate
    detected_known = {r["known"] for r in det["drift"] if r["known"]}
    known_rows = [dict(id=k, desc=v, detected=k in detected_known,
                       lines=sorted({int(r["line"]) for r in det["drift"] if r["known"] == k})) for k, v in {**KNOWN_DRIFT, **EXTRA_KNOWN}.items()]
    gate_known = [r for r in known_rows if r["id"] in KNOWN_DRIFT]
    m4_recall = sum(r["detected"] for r in gate_known) / len(gate_known)
    sev = Counter(r["severity"] for r in det["drift"])
    drift_lines = sorted({int(r["line"]) for r in det["drift"]})
    logger.info(f"M4 known-drift recall {m4_recall:.2f}; missing {[r['id'] for r in gate_known if not r['detected']]}")

    # ---------------- M5 seeded injection
    logger.info("seeded-error injection (blind re-run on a scratch copy) ...")
    inj0 = seeded_injection(lines, hypo_text, line_arts, det, seed=SEED, tag="_seed20260929")
    inj = seeded_injection(lines, hypo_text, line_arts, det, seed=SEED_BLIND, tag="_seed20260930")
    inj["frozen_seed_run"] = dict(seed=SEED, recall=inj0["recall"], recall_by_type=inj0["recall_by_type"],
                                  note="the executor inspected this draw after a first detector version (recall 0.35) and then fixed the detector "
                                       "generically; this re-run is therefore NOT blind")
    logger.info(f"M5 recall blind seed {SEED_BLIND}: {inj['recall']:.3f} {inj['recall_by_type']}; frozen seed {SEED}: {inj0['recall']:.3f}")
    clean_flagged = sorted(ln for ln in det["flagged"] if ln > 0)
    rng = random.Random(SEED + 1)
    fp_sample = rng.sample(clean_flagged, min(30, len(clean_flagged)))
    fp_rows = [dict(line=ln, text=lines[ln - 1][:240], reasons=sorted(det["flagged"][ln])) for ln in sorted(fp_sample)]
    (WS / "results" / "precision_check_sample.json").write_text(json.dumps(fp_rows, indent=1, ensure_ascii=False))
    manual = WS / "results" / "precision_manual_labels.json"
    m5_precision = None
    if manual.exists():
        lab = json.loads(manual.read_text())
        lab = {int(k): v for k, v in lab.items()}
        judged = [lab[r["line"]] for r in fp_rows if r["line"] in lab]
        if judged:
            m5_precision = sum(1 for j in judged if j.startswith("TRUE")) / len(judged)
    inj["precision_manual"] = m5_precision
    inj["n_flagged_clean_lines"] = len(clean_flagged)
    (WS / "results" / "seeded_injection.json").write_text(json.dumps(inj, indent=1, ensure_ascii=False, default=str))

    # ---------------- M6 independent re-derivation
    ind = run_independent(claims)
    (WS / "results" / "independent_rederivation.json").write_text(json.dumps(ind, indent=1, default=str))
    logger.info(f"M6 independent agreement {ind['n_agree']}/{ind['n']}")

    # ---------------- M11, tables, M7, M8, cases
    m11 = table18_honesty(lines, det)
    (WS / "results" / "table18_honesty.json").write_text(json.dumps(m11, indent=1, ensure_ascii=False))
    TB = build_tables(det, m11, verdicts)
    blocked = {d["id"] for d in ind["disagreements"]}
    write_tables(TB, results)
    ta = results["table_assertions"]["tables"]
    tables_ok = {k: v["pass"] for k, v in ta.items()}
    cases_ok = write_cases()
    m7 = sum(tables_ok.values()) / len(tables_ok)
    m8 = review_closure(tables_ok, det["drift"], verdicts, cases_ok)
    (WS / "results" / "review_closure.json").write_text(json.dumps(m8, indent=1))
    closed = ["# Closed strands (one sentence each; numbers audited in record_of_numbers_final.csv)", ""] + [f"- **{a}**: {b}." for a, b in CLOSED]
    (WS / "tables" / "closed_strands.md").write_text("\n".join(closed) + "\n")

    # ---------------- M9 / M10
    m9_mis = [v for v in verdicts if v["flag"] == "VERDICT_DRIFT"]
    rec = AC.load_csv("round-3/evaluation-1/src/results/record_of_numbers.csv")
    miss = [r for r in rec if r["flag"] == "MISSING_IN_REPORT"]
    grep_count = (AC.RUN_ROOT / "round-3/evaluation-1/src/results/record_of_numbers.csv").read_text().count("MISSING_IN_REPORT")
    m10 = dict(n_rows_flag_column=len(miss), grep_occurrences=grep_count, by_block=dict(Counter(r["block"] for r in miss)),
               n_SENS2=sum("SENS2" in r["id"] for r in miss), n_r1a=sum("r1a" in (r["id"] + r["claim"]).lower() for r in miss),
               n_granger=sum("granger" in (r["id"] + r["claim"]).lower() for r in miss))
    m11_counts = Counter(m["status"] for m in m11)

    # ---------------- summary + eval_out.json
    summ = dict(
        M1=dict(curated_overall=m1_overall, curated_by_block=m1, n_curated=len(claims), autoscan_all=auto_rate, autoscan_sig2=auto_rate2, autoscan_sig3=auto_rate3,
                n_tokens=len(toks), n_tokens_sig2=len(toks2), autoscan_sig2_by_iteration={k: v[0] / v[1] for k, v in sorted(by_iter.items())}),
        M2=m2, M3={b: dict(c) for b, c in flag_tab.items()},
        M4=dict(n_drift_rows=len(det["drift"]), n_drift_lines=len(drift_lines), by_severity=dict(sev), known_recall=m4_recall, known=known_rows),
        M5=dict(recall=inj["recall"], by_type=inj["recall_by_type"], precision_manual=m5_precision, n_flagged_clean_lines=len(clean_flagged)),
        M6=dict(n=ind["n"], agree=ind["n_agree"], blocked_claims=sorted(blocked)),
        M7=dict(rate=m7, tables={k: v for k, v in ta.items()}), M8=m8, M9=dict(n_rules=len(verdicts), n_mismatch=len(m9_mis),
                                                                              mismatches=[v["rule"] for v in m9_mis],
                                                                              not_recorded=[v["rule"] for v in verdicts if v["status"] == "RULE_NOT_RECORDED"]),
        M10=m10, M11=dict(counts=dict(m11_counts), items=m11), runtime_s=time.time() - t0)
    (WS / "results" / "audit_summary.json").write_text(json.dumps(summ, indent=1, default=str, ensure_ascii=False))

    ex_claims = []
    for c in claims:
        ex_claims.append(dict(
            input=f"[{c['id']}] {c['claim']} | fold {c['fold_label']} | estimator {c['estimator']} | report line {c['report_line']}: '{c['report_value']}'"
                  + (f" | hypothesis: '{c['hyp_value']}'" if c["hyp_value"] else ""),
            output=f"source {c['source']} = {fmt(c['source_value'])}" + (f"; tier-C recompute {fmt(c['recomputed'])}" if c['recomputed'] != "" else "")
                   + (f"; replacement: {c['replacement']}" if c["replacement"] and c["flag"] != "OK" else ""),
            predict_report=str(c["report_value"] or c["hyp_value"] or ""), predict_source=fmt(c["source_value"]),
            predict_flag=c["flag"],
            metadata_block=c["block"], metadata_fold=c["fold_label"], metadata_tier=c["tier"], metadata_artifact=c["artifact"],
            metadata_headline=bool(c["headline"]), metadata_known_drift=c["known"],
            eval_traced=float(bool(c["traced"])), eval_in_report=float(bool(c["report_value"])),
            eval_ok=float(c["flag"] == "OK"), eval_flag_nonok=float(c["flag"] not in ("OK", "MISSING_IN_REPORT"))))
    ex_drift = [dict(input=f"line {r['line']}: {r['report_text']}", output=r["correct_text"][:600], predict_flag=r["flag"], predict_severity=r["severity"],
                     metadata_source=r["source"], metadata_claim_id=r["claim_id"], metadata_known=r["known"],
                     eval_verdict_changing=float(r["severity"] == "VERDICT-CHANGING")) for r in det["drift"]]
    ex_inj = [dict(input=f"{p['type']} at line {p['line']}: '{p['old']}' -> '{p['new']}'", output="detected" if p["detected"] else "missed",
                   predict_detector="; ".join(p["reasons"])[:500], metadata_type=p["type"], eval_detected=float(p["detected"])) for p in inj["perturbations"]]
    ex_ind = [dict(input=f"[{i['id']}] {i['src']}", output=fmt(i.get("indep_value")), predict_audit=fmt(i["audit_value"]),
                   predict_independent=fmt(i.get("indep_value")), metadata_block=i["block"], eval_agree=float(i["agree"])) for i in ind["items"]]
    ex_ver = [dict(input=f"iteration {v['iteration']} rule: {v['rule']}", output=v["outcome_from_rule"], predict_report=str(v["report_statement"]),
                   predict_status=v["status"], metadata_quote=v["rule_quote"][:300], metadata_inputs=v["inputs"],
                   eval_match=float(v["status"] == "MATCH")) for v in verdicts]
    ex_tab = [dict(input=name, output="emitted" if st["pass"] else "withheld", predict_status="PASS" if st["pass"] else "FAIL",
                   metadata_n_cells=st["n_cells"], eval_pass=float(st["pass"]), eval_n_checked=float(st["n_checked"]), eval_n_fail=float(st["n_fail"]))
              for name, st in ta.items()]
    metrics = dict(
        M1_traceability_curated=m1_overall, M1_traceability_autoscan_all_tokens=auto_rate, M1_traceability_autoscan_sig2=auto_rate2,
        M1_traceability_autoscan_sig3=auto_rate3,
        **{f"M1_traceability_{b}": v for b, v in m1.items()},
        M2_agreement_overall=m2["overall"], M2_agreement_tier_R=m2["tier_R"], M2_agreement_tier_C=m2["tier_C"],
        M2_headline_share_tier_C=m2["headline_tier_C"] / max(1, m2["headline_n"]),
        M3_n_nonOK_numbers=float(sum(c["flag"] not in ("OK", "MISSING_IN_REPORT") for c in claims)),
        M3_n_missing_in_report=float(sum(c["flag"] == "MISSING_IN_REPORT" for c in claims)),
        M3_n_wrong_estimator=float(sum(c["flag"] == "WRONG_ESTIMATOR" for c in claims)),
        M3_n_wrong_definition=float(sum(c["flag"] == "WRONG_DEFINITION" for c in claims) + sum(a["flag"] == "WRONG_DEFINITION" for a in asserts)),
        M3_n_drift_value=float(sum(c["flag"] == "DRIFT_VALUE" for c in claims)),
        M3_n_not_traceable=float(sum(c["flag"] == "NOT_TRACEABLE" for c in claims)),
        M4_report_drift_lines=float(len(drift_lines)), M4_verdict_changing=float(sev.get("VERDICT-CHANGING", 0)),
        M4_number_only=float(sev.get("NUMBER-ONLY", 0)), M4_wording=float(sev.get("WORDING", 0)), M4_known_drift_recall=m4_recall,
        M5_seeded_recall=inj["recall"], **{f"M5_recall_{k}": v for k, v in inj["recall_by_type"].items()},
        M5_seeded_recall_frozen_seed_not_blind=inj["frozen_seed_run"]["recall"],
        M6_independent_agreement=ind["rate"], M6_n_rederived=float(ind["n"]),
        M7_table_pass_rate=m7, M9_rule_mismatches=float(len(m9_mis)), M9_rules_evaluated=float(len(verdicts)),
        M10_missing_in_report_rows=float(len(miss)),
        M11_table18_done=float(m11_counts.get("DONE", 0)), M11_table18_partial=float(m11_counts.get("PARTIAL", 0)),
        M11_table18_not_done=float(m11_counts.get("NOT DONE", 0)),
        M8_review_items_closed=float(sum(r["status"] == "CLOSED" for r in m8)),
    )
    if m5_precision is not None:
        metrics["M5_precision_manual30"] = m5_precision
    out = dict(metadata=dict(evaluation_name="numbers-of-record audit (iteration 5 FIX slot)", audit_spec_sha256=frz["spec"]["_audit_spec_sha256"],
                             universe_sha256=frz["spec"]["universe_sha256"], frozen_utc=frz["spec"]["frozen_utc"], report=AC.REPORT_REL,
                             summary_file="results/audit_summary.json"),
               metrics_agg={k: float(v) for k, v in metrics.items()},
               datasets=[dict(dataset="record_of_numbers", examples=ex_claims), dict(dataset="report_drift", examples=ex_drift or [dict(input="none", output="none")]),
                         dict(dataset="verdict_consistency", examples=ex_ver), dict(dataset="seeded_injection", examples=ex_inj),
                         dict(dataset="independent_rederivation", examples=ex_ind), dict(dataset="table_assertions", examples=ex_tab)])
    (WS / "eval_out.json").write_text(json.dumps(out, indent=1, ensure_ascii=False, default=str))
    logger.info(f"done in {time.time() - t0:.0f}s; metrics: " + json.dumps({k: round(v, 3) for k, v in out['metrics_agg'].items()}))


if __name__ == "__main__":
    main()
