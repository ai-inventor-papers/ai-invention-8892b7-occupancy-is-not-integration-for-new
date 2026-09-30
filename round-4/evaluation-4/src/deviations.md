# Deviations from the artifact plan (gen_plan_evaluation_3_idx4)

The deviations are listed in execution order. None of them changes a frozen threshold, a frozen code file or a decision rule.

1. **Copying the frozen experiment used `tar`, not `rsync`, because rsync is not installed.** The same exclusions were applied (`.venv`, `__pycache__`, `heldout_sim`, `mini_run`). `confirm_heldout.py --dry-run` then verified the spec sha256 `695166b4…`, all 23 code files and all 6 frozen artefacts (`logs/dry_run.log`), and the 12 unit tests passed (`logs/pytest.log`).

2. **The held-out opening ran once, with no manual stage reruns.** The open guard (`logs/open_guard.json`) found no existing `heldout_run/OPENED` in exp_8 or under iter_4. The opening finished all 10 stages in about 14 minutes and wrote `exp8_frozen/heldout_run/results/confirmation.json`.

3. **The adapter gate used reference concepts plus held-out concepts, not screen concepts.** The copied experiment does not contain the screen c-paper table (`work/cp_hyd.parquet` is not materialised). The held-out prep writes held-out and reference concepts only.
   - The gate therefore compared the adapter with the frozen indicators on 20 reference concepts computed by the frozen screen pipeline (829 concept-years). After the opening it also compared 20 held-out concepts against `heldout_run` indicators.
   - Max |diff| was 0 for H, H_rar and active_subfields_3y, and 2.2e-16 for RS. There were no NaN-pattern mismatches (`results/mesh/adapter_gate.json`).

4. **The MeSH spec was re-frozen once (v1 → v2), before any MeSH output.** The first adapter build failed on I/O parsing: the metadata booleans were real bools, and authorships were lists, not repr strings. The PubMed-route definition was also made explicit (pubmed_tiab + mesh_indexed_only).
   - The fix touched only parsing. Because the spec hashes the adapter file, `mesh_spec.json` was re-frozen (v2).
   - v1 is kept as `results/mesh_spec_v1_superseded.json`, and both hashes are in `logs/freeze_log.txt`. No MeSH typology, lead-lag or role number existed before v2.

5. **MeSH roles were built from the stored substrate, with approximations.**
   - Focal neighbour weights are not stored in `focal_YYYY.parquet`. So `n_comm_25pct` uses unweighted neighbour counts per community.
   - `dom` is that artifact's own weighted `module_local`, mapped to persistent ids with the frozen `alluvial_from(0.3, 5)`. P and wmz are that artifact's weighted P and z_within.
   - `founder_rank` ranks focal s among the dominant community's node strengths W_i.
   - The frozen `assign_roles` thresholds and `ga_class` were then applied unchanged.
   - This is a descriptive population contrast, as the plan says (DEPARTS 3).

6. **MeSH seed stability was not assessed.** The frozen `leiden_single` takes 99 s per seed-year on a MeSH snapshot (27,670 nodes, 481,059 edges). Five seeds over 25 years come to about 206 CPU-minutes, which is more than the plan's 30-minute rule (`logs/mesh_seed_timing.txt`). MeSH roles use the single best-of-5 partition from art_yWUkgWWKyq_h.

7. **The MeSH pct_alt_reference sensitivity was not run.** MeSH strengths come from a different co-occurrence graph (the post-stratified 259,716-work background sample), so placing them into the main-pool X3 reference arrays would compare numbers on different scales. As a substitute, the all-node `wdeg_pctl` of that artifact was run as a sensitivity. It gives n_both = 0, because focal MeSH nodes sit near the 2nd all-node percentile, as that artifact documented.

8. **Case partner lists were dropped.** Rebuilding exp_7's top-5 partners needs its prepared corpus cache `results/cache/prepared.pkl`. That cache was deleted under exp_7's manifest, and `io_load.prepare()` would write it back inside a read-only dependency. The plan's fallback applies: stored entry values are reported. A_cont in those values was independently re-derived by exp_7's `audit_rederive.py`.

9. **The year-shuffle null was replicated, not imported.** In the frozen `leadlag.main` the null is inline code, not a function. For MeSH it was replicated line for line (same seed 2026 and 1,000 draws) in `evalsteps/mesh.year_shuffle_null`. The pooled-main null was not computed. The screen and held-out nulls are reported separately.

10. **The screen cross-tab gate was checked to 2 decimals or within 0.006.** Screen p-values reproduced as 0.097, 0.111 (target 0.11), 0.077 and 0.004. The gate passed, so the held-out and pooled rows are reported.

11. **Host share per role includes two extra rows.** Entries whose concept has no role row in e-1 are labelled `NO_ROLE_ROW`, for example before first attachment + 1. Non-robust role years are labelled `NONROBUST`. Both are reported, not dropped.

12. **Concept-level role shares in eval_out have different bases.** For MeSH they are shares over all role-years, since there is no robustness flag. For the main pool they are shares over robust role-years.

13. **The evaluation ran on pandas 2.3.3, not the 3.0.6 pinned by exp_8.** Installing `pyfixest==0.60.0` into the environment downgraded pandas. Every step ran on 2.3.3, including the held-out opening and the pytest check. The frozen code files are byte-identical, and the dry-run hash check does not cover library versions. The exact environment is pinned in `pyproject.toml` (from `uv pip freeze`).

14. **An independent audit was added.** `scripts/audit_rederive.py` and `scripts/audit_rederive_ppml.py` recompute the headline numbers without the evaluation code. They use their own DTW and series builder, statsmodels dummies in place of pyfixest, a statsmodels Poisson GLM in place of exp_7's ppml.py, scipy chi² in place of perm_chi2, and plain CSV counting. They also run placebos. Results are in `results/audit_rederive.json`.
