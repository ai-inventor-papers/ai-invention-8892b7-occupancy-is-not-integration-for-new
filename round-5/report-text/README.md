# Iteration 5 Report Text

Produces the iteration 5 section of the internal research report for
"Exploring emerging scientific concepts through evolving knowledge networks."
Iterations 1-4 are carried verbatim from the previous iteration; iteration 5
is appended.

## Layout

| File | Description |
|---|---|
| `paper_draft.md` | Full report (iterations 1-5), the primary output |
| `references.bib` | BibTeX bibliography built via Semantic Scholar |
| `references.json` | Fetch record for each BibTeX entry |
| `.terminal_claude_agent_struct_out.json` | Structured output (title, abstract, figures, summary) |
| `style_exemplars.md` | Writing-style exemplars used during drafting |
| `domain_terms.json` | Domain vocabulary used for terminology checking |
| `.aii/manifest.yaml` | Artifact manifest with dependencies and entries |

## Iteration 5 content

- **Margin decomposition** (extensive vs intensive): BOTH margins significant.
  IVW extensive +6.43 pp/SD [4.76, 8.11]; IVW intensive IRR/SD 1.183
  [1.104, 1.267].
- **Host-specificity test**: HOST-SPECIFIC. Generality controls leave A_cont
  unchanged (IVW retention 0.984). A_lift IVW IRR/SD 1.34 [1.23, 1.46].
- **Field-boundary test**: NO DETECTABLE FIELD BOUNDARY (Wald p = 0.638).
- **Audit**: 11-module numerical audit. 99.4% curated accuracy. All 6 MAJOR
  reviewer critiques closed. 4 of 11 Table 18 claims not done.
- **Positioning**: PARTLY ANTICIPATED (0 ANTICIPATES, 11 PARTLY among 25
  graded).
- **Figures**: 8 publication-ready figures, all pass production checks.

## How to run

This artifact is a text-generation step. It reads artifact output files from
the evaluation and research steps listed in `.aii/manifest.yaml` and appends
iteration 5 to the carried-forward report draft.

```bash
# No executable code; the report is written by the agent.
# To regenerate, re-run the gen_report_text module in the invention loop.
```

## Dependencies

See `.aii/manifest.yaml` for the full dependency list.

## Restoring removed files

No files were removed. All outputs are small text files retained in place.
