#!/usr/bin/env python3
"""STEP 3a: freeze the MeSH second-population spec BEFORE any MeSH typology / lead-lag / role output is computed."""
import hashlib, json, datetime
from pathlib import Path
WS = Path(__file__).resolve().parents[1]
E8 = WS / "exp8_frozen"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
files = ["src/typology.py", "src/indicators.py", "src/leadlag.py", "src/roles.py", "src/leiden_seeds.py", "src/patterns.py",
         "vendor/lib_metrics.py", "vendor/stage_indicators.py", "typology/medoids.json", "typology/scaling.json",
         "results/roles_spec.json", "sealed/pct_alt_reference.npz"]
pw = json.loads((WS / "results/power_mde.json").read_text())
spec = dict(
    created_utc=datetime.datetime.now(datetime.UTC).isoformat(),
    frozen_function_sha256={f: sha(E8 / f) for f in files},
    adapter_sha256={"scripts/mesh_adapter.py": sha(WS / "scripts/mesh_adapter.py")},
    adapter_gate=json.loads((WS / "results/mesh/adapter_gate.json").read_text())["passed"],
    population=dict(primary="all 191 MeSH concepts (art_HGiVAYhqO-6q)", sensitivity="rule_parity subset (172)",
                    works="verified_text_match == True only; years 2000-2024; subfield = primary_topic.subfield_id (-1 unknown)"),
    typology=dict(rule="frozen medoids.json + frozen scaling; nearest medoid by frozen dtw_norm (radius 3); series years F..2024 via frozen build_series",
                  coverage_bias="13 retrieval_complete concepts: channels on all verified works vs PubMed-route works only; switch rate + mean channel deflation; MeSH broad share reported as a LOWER BOUND"),
    leadlag=dict(expansion_channel="wdeg_pctl_focal (MeSH-internal focal percentile, art_yWUkgWWKyq_h features.parquet), gain 10, 2 consecutive years",
                 diffusion="frozen: H_rar(y)-H_rar(y-2) >= 0.2 AND new active subfield in y (new_active_years on MeSH c-papers)",
                 first_attach="first snapshot year with a network row (k > 0 or s > 0) in features.parquet",
                 sensitivities=["4x3 grid gain {5,10,15,20} x rise {0.1,0.2,0.3}", "cum2 variant",
                                "all-node wdeg_pctl as pct_col", "Granger-style panel dH on lagged dpct (concept FE, clustered)"],
                 note="placement of MeSH strengths into sealed/pct_alt_reference.npz declared as a sensitivity; run only if attach.pct_alt_value applies to the MeSH strength scale"),
    roles=dict(inputs="art_yWUkgWWKyq_h features.parquet P and z_within (single best-of-5 partition); frozen thresholds from results/roles_spec.json",
               necessary_condition="report max z_within and share >= 1 and >= 2.5; if max < 1 CORE_GROWING cannot fire",
               seed_stability="5-seed Leiden rerun only if extrapolated time <= 30 min, else declared NOT ASSESSED"),
    patterns="art_yWUkgWWKyq_h rq1_patterns_by_concept.csv (reproduced by exp8) vs screen and held-out patterns.csv",
    mde=dict(wilson_halfwidth_n191=pw["wilson_halfwidth"], chi2_w_80pct_n191={k: v["191"] for k, v in pw["chi2_mde_w_80pct"].items()}),
)
p = WS / "results/mesh_spec.json"
p.write_text(json.dumps(spec, indent=1))
h = sha(p)
with open(WS / "logs/freeze_log.txt", "a") as fh:
    fh.write(f"{datetime.datetime.now(datetime.UTC).isoformat()} mesh_spec.json sha256 {h} (frozen before any MeSH typology/lead-lag/role output)\n")
print(h)
