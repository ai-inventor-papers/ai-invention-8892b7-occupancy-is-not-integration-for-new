#!/usr/bin/env python3
"""Entry point: runs the concept-cleaning experiment end to end (proposed models AND their baselines).

  uv run method.py                 # full pipeline (steps 0-9), same order as the frozen run
  uv run method.py --mini          # T2 mini pipeline: small samples, LLM calls stubbed (dry run), outputs -> mini_run/
  uv run method.py --from s3       # resume from a step

Steps (all code in src/):
  s0_load            integrity (frame sha256) + dataset extraction
  s1a_fetch_arxiv    arXiv titles <= 2018 (HF librarian-bots/arxiv-metadata-snapshot)
  s1_corpus          termhood statistics (Aho-Corasick pass; outcome-blind windows for frame phrases)
  t1_reused_code     T1: vendored Schwartz-Hearst reproduces DS4 pair precision; guard check
  s2_features        lexical features + MiniLM/SPECTER2 embeddings
  s3_classifier      PRIMARY concept LR + HGB/ablations + baselines (majority, C-value, LLM A, LLM B) + human anchors
  s4_merger          PRIMARY pair LR + HGB/unweighted/D3-only + baselines (normalised-equal, cosine, token_set>=85)
  s4b_merger_choice  admissibility of the F5 alternative merger under the plan's two-subset threshold rule
  s5_link_calib      NIL-aware linker calibration on MeSH (MiniLM vs SPECTER2, SapBERT reported)
  s7a_predict        frozen classifier applied to the 426-concept frame (written BEFORE any frame LLM label)
  s6_llm_audit       sense proxy + frame silver labels + adjudication (OpenRouter, cap $0.30)
  s7b_merge_link     frame merging, acronym risk, linking (OpenAlex keywords/concepts, MeSH, Wikidata)
  s6_llm_audit --links  LLM judgement of accepted stage-2/broader links and frame merges
  s8_freeze          frozen, hashed test population for iteration 3
  s9_report          method_out.json + tables
  t3_leakage_checks  T3/T7 hard checks (leakage, ordering by mtime, hashes, list subsets, file sizes)
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STEPS = [("s0_load", []), ("s1a_fetch_arxiv", []), ("s1_corpus", []), ("t1_reused_code", []), ("s2_features", []),
         ("s3_classifier", []), ("s4_merger", []), ("s4b_merger_choice", []), ("s5_link_calib", []), ("s7a_predict", []),
         ("s6_llm_audit", []), ("s7b_merge_link", []), ("s6_llm_audit", ["--links"]), ("s8_freeze", []), ("s9_report", []), ("t3_leakage_checks", [])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mini", action="store_true", help="T2 mini pipeline (no LLM spend, outputs in mini_run/)")
    ap.add_argument("--from", dest="start", default=None, help="first step to run (e.g. s3_classifier)")
    args = ap.parse_args()
    env = dict(os.environ)
    if args.mini:
        env["AII_MINI"] = "1"
    started = args.start is None
    for name, extra in STEPS:
        if not started:
            started = name == args.start
            if not started:
                continue
        if args.mini and name in ("s0_load", "s1a_fetch_arxiv", "t1_reused_code"):
            continue  # inputs are shared with the full run
        cmd = [sys.executable, str(ROOT / "src" / f"{name}.py")] + extra
        if args.mini and name == "s6_llm_audit":
            cmd.append("--dry-run")
        t0 = time.time()
        print(f"=== {name} {' '.join(extra)}", flush=True)
        r = subprocess.run(cmd, cwd=ROOT, env=env)
        print(f"=== {name} exit {r.returncode} in {time.time() - t0:.0f}s", flush=True)
        if r.returncode != 0:
            sys.exit(r.returncode)


if __name__ == "__main__":
    main()
