# GEN_REPORT_TEXT - Iteration 4

Research report for "Open neighbourhoods precede concept spread: structural antecedents and cross-disciplinary diffusion of emerging scientific concepts."

## What was done

Confirmation iteration opening four sealed held-out folds and running cross-population replication on MeSH biomedical concepts. Five new artifacts (16-20) resolved the study's two main questions: host-entry grafting is confirmed and replicated (IRR/SD 1.19 held-out, 1.23 MeSH, IVW pooled 1.26); primary closure is not confirmed but persistent-neighbour closure survives (S = -1.073, Holm p = 0.015). An adopter-level mechanism test finds OR 3.14 for prior exposure to entry partners, with a FOREIGN > ADJACENT > NATIVE gradient consistent with absorptive capacity.

## File layout

| File | Description |
|---|---|
| `paper_draft.md` | Full research report, iterations 1-4 (~970 lines) |
| `references.bib` | BibTeX bibliography (40 entries via Semantic Scholar / OpenAlex / Crossref) |
| `references.json` | Fetch record for each bib entry |
| `style_exemplars.md` | Style exemplars from target-venue papers |
| `domain_terms.json` | Domain vocabulary constraints (80 terms) |
| `.terminal_claude_agent_struct_out.json` | Structured JSON output for downstream pipeline |
| `.aii/manifest.yaml` | File manifest (no large binaries or caches to decide on) |

## How to use

The primary output is `paper_draft.md`. It contains the complete chronological research report across all four iterations, with `[FIGURE:fig_id]` markers for figure placement and `[ARTIFACT:id]` markers for traceability. Figure specifications are in `.terminal_claude_agent_struct_out.json` under the `figures` array.

Citations use numbered references `[1]`-`[31]` mapped to entries in `references.bib`.

## Iteration 4 artifact summary

- **Artifact 16** (art_WZ8fbLn79nCq): Grafting held-out confirmation + discriminating tests. Co-primary CONFIRMED (IRR/SD 1.19 [1.06, 1.33], p = 0.004). Mechanism label: host-vocabulary.
- **Artifact 17** (art_XGdzjWgi-a88): MeSH replication. REPLICATED (IRR/SD 1.23 [1.12, 1.36], Holm p = 9.7e-5). IVW pooled 1.26 [1.17, 1.36], I-squared = 0.
- **Artifact 18** (art_zw_JJGsUFSnd): Closure held-out + closure-anchoring link. Closure not confirmed on primary; persistent-neighbour closure CONFIRMED (S = -1.073, p = 0.015). Closure-anchoring link NULL.
- **Artifact 19** (art_mu0h0npvNX_u): Descriptive held-out + MeSH. Lead-lag confirmed (25/26 expansion-first). Rooting NOT SUPPORTED.
- **Artifact 20** (art_FZ2OCJwV6xHs): Adopter mechanism. OR(E_any) = 3.14 [2.37, 4.29]. Vocabulary gradient FOREIGN > ADJACENT > NATIVE (absorptive capacity).

## Dead ends

1. Closure not confirmed on primary held-out operationalisation
2. Closure-anchoring link test NULL (no connection between pre-emergence closure and later anchoring)
3. BROAD concepts do not anchor more
4. Breadth prediction null on both folds
5. Single-paper artefact interaction significant on held-out (caveat, not disqualifying)
6. Adopter x A_cont interaction null

## Restoring removed files

No files were removed. All outputs are small text files kept automatically.
