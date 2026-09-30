# Where the host-vocabulary finding sits in the literature (positioning dossier)

This is a web-only research artifact for the iteration-5 paper on concept emergence and diffusion, targeting *Applied Network Science*. It compares the confirmed claim against its nearest published neighbours. The claim: an emerging concept combined with host-leaning vocabulary when it enters a new subfield gets more uptake from that host's newcomers.

The artifact contains:

- a logged novelty search with a graded verdict ("partly anticipated") and a paper-ready novelty sentence;
- a draft of the paper's Table 1;
- 27 ANS related-work papers;
- 26 methods references for the hurdle, lift/generality, moderator and few-cluster inference tests;
- Crossref-validated DOIs throughout.

## Layout

| Path | What it is |
|---|---|
| `research_report.md` | Main deliverable in 11 sections: claim, nearest-neighbour table (21 rows), Table-1 draft, novelty log and verdict, positioning paragraphs, ANS venue, methods table, ID list, unverified list, corrections, confidence. |
| `research_out.json` | Structured output (answer, 93 numbered sources with passages, follow-ups; every source cited in the answer). Saved by the pipeline from `.terminal_claude_agent_struct_out.json`. |
| `bib_ids.txt` | 88 DOIs/arXiv ids, grouped, ready for `aii-semscholar-bib`; books noted as comments. |
| `reproducibility.md` | How the research was actually done: queries, fetch routes, failures. |
| `search_log/` | 14 queries × 2 modes of raw search output, `queries.txt`, and `titles_all.txt` (571 screened titles). |
| `snowball/` | Semantic Scholar forward citations for 5 seeds, Cheng's Crossref reference list, the DOI validation log, and the methods abstracts batch. |
| `ans/` | Crossref ANS-ISSN queries and the ANS abstracts batch. |
| `cache/` | Text of every fetched page/PDF (markdown), used for local passage checks. Excluded from the published repo. |
| `tools/` | Helper scripts (`getdoc.sh`, `g.py`, `s2title.py`, `s2cites.py`, `crossref.py`, `build_output.py`). |

## How to run

No compute is needed.

- `python3 tools/build_output.py` regenerates the structured output from the source table.
- `tools/getdoc.sh <name> <url>` re-fetches a page into `cache/`, using the aii-web-tools skill interpreter.

## Restoring removed files

The manifest marks nothing for deletion: all outputs are small text files.

`cache/` is excluded from upload but is kept on the run volume. To rebuild it, re-run `tools/getdoc.sh` for the URLs listed in `reproducibility.md`, e.g.:

```bash
tools/getdoc.sh cheng "https://journals.sagepub.com/doi/full/10.1177/00031224231166955"
```
