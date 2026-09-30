# gen_report_text — Iteration 1

Internal research report for the source-sink concept diffusion study. This iteration assembled four preparatory artifacts (concept pool, MeSH held-out population, semantic grounding infrastructure, prior-art dossier) and documented their construction, quality metrics, and shortfalls. No experiment or evaluation was executed.

## Layout

| File | Description |
|---|---|
| `paper_draft.md` | Main deliverable: the iteration 1 internal report |
| `references.bib` | BibTeX bibliography (22 entries fetched from Semantic Scholar) |
| `references.json` | Fetch record for each bibliography entry (source API, IDs, titles) |
| `style_exemplars.md` | Verbatim passages and section outlines from four target-venue papers |
| `domain_terms.json` | 80+ domain terms with glosses, used for terminology checks |
| `.terminal_claude_agent_struct_out.json` | Structured JSON output (title, abstract, figures, summary) |

## How to regenerate

The report was written by the `gen_report_text` step of the AI Inventor pipeline. To regenerate, re-run the step for iteration 1:

```bash
# from the run root
python -m aii run --step gen_report_text --iteration 1
```

The bibliography was built with the `aii-semscholar-bib` skill. To re-fetch:

```bash
SKILL_DIR="$(git rev-parse --show-toplevel)/.claude/skills/aii-semscholar-bib"
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py \
  --out ./references.bib --refs '<see references.json for the full input list>'
```
