# Deviations from prereg_freeze.json

Each entry: what changed relative to prereg_freeze.json, why, and its expected effect. The prereg file itself is never edited.

1. **Git commit of the freeze skipped.** The workspace is not a git repository (`git rev-parse` fails), so per the plan the
   commit is skipped; the sha256 + ISO timestamp in `prereg_freeze.sha256` are the freeze record.
2. **n_min rule not met.** No |Kd| bin reaches a median 90% CI width of log rho <= 0.7 (widths 1.29-1.83, see
   `results/viability/viability_summary.json`), so the pre-declared fallback n_min_rule = 30 (flagged) applies and the
   main n_min = max(10, 30) = 30. The width does not shrink with |Kd| because it is driven by the small cohort-parent
   count |Pd|; the 5/10/15/20/30 curves are reported as declared.
3. **Tested also requires >= 1 traced child** (declared in the prereg's eligibility block, reason code
   `no_traced_children`); m is undefined otherwise.
4. **Within-host share can exceed the lenient share** on 3.5% of edges: the lenient loader definition (iteration-1
   assemble.py) uses no dedup and parents strictly older than the child, while the primary statistic allows same-year
   parents (year(p) <= year(k)) as frozen. The plan's "subset" expectation therefore holds for 96.5% of edges, not all.
5. **H1 sign check operationalised** as: Model B (BASE + both S features, standardised) coefficient sum on the two S
   features > 0. Continuous-outcome success = CI95 lower > 0 AND sign recovered (no 0.01 point floor; declared in prereg).
6. **Extra design points** beyond the plan (not replacing any): H1 cells at N = 150 concepts and at the main n_min (30);
   Gate B designs 'upper_bound_nmin5' and its projection. These are sensitivity additions.
7. **Hypothesis quote 13/23/40/54/63 (old-rule eligible units) not reproduced exactly.** Dedup'ed counts are
   10/15/33/48/54 and no-dedup counts 12/16/36/51/55 (screen fold) or 15/26/54/80/99 (all main). The quote's unit
   definition is not recoverable from the artifacts, so both variants are reported in `results/audit/audit_summary.json`.
8. **Synthetic generator details not fixed by the plan:** lambda0 = median stationary reference rho / (kappa * pi)
   (the plan's "/ pi" read as the traced probability kappa*pi); reference cells flattened by filler papers in years
   t-2..t plus a solved parent split so expected yearly counts are flat; pi drift = +10%/yr from t-4 for host edges only.
