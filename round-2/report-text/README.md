# gen_report_text — Iteration 2

Internal research report for the source-sink concept diffusion study. This iteration executed five artifacts: concept grounding pipeline, viability estimation (Gate A, viability states, synthetic validation, power analysis), main-pool RQ1 event study with prediction and typology, and MeSH replication. The viability decomposition is blocked (Gate A fails at edge level); the headline finding is a replicated closure reversal — emerging concepts show lower, not higher, triadic closure before onset.

## Layout

| File | Description |
|---|---|
| `paper_draft.md` | Main deliverable: the iteration 1 + 2 internal report |
| `references.bib` | BibTeX bibliography (22 entries fetched from Semantic Scholar) |
| `references.json` | Fetch record for each bibliography entry (source API, IDs, titles) |
| `style_exemplars.md` | Verbatim passages and section outlines from four target-venue papers |
| `domain_terms.json` | 80+ domain terms with glosses, used for terminology checks |
| `.terminal_claude_agent_struct_out.json` | Structured JSON output (title, abstract, figures, summary) |

## How to regenerate

The report was written by the `gen_report_text` step of the AI Inventor pipeline. To regenerate, re-run the step for iteration 2:

```bash
# from the run root
python -m aii run --step gen_report_text --iteration 2
```
