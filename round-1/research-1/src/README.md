# Prior-art and pre-registration dossier: concept emergence and cross-disciplinary diffusion (OpenAlex → Applied Network Science)

This repository is a **research artifact**: a web-research dossier with no code to run. It prepares a five-candidate screen of mechanisms that separate *locally concentrated* from *broadly integrated* emerging scientific concepts. The candidates:
- C0: citation-lineage source/sink viability
- C1: host anchoring
- C2: toolkit co-transfer
- C3: origin-neighbourhood structure
- C4: demic vs cultural adoption

It also covers the RQ1 "network-only emergence" framing, for a paper targeting *Applied Network Science*, collection "Networks for everyday life".

## What it contains

| File | Content |
|---|---|
| `research_report.md` | The full dossier, 9 sections: executive summary and ranking; master table; prior-art notes per candidate with extracted formulas and effect sizes; the pre-registration operationalisation sheet (formulas, inputs, minimum counts, predicted signs, pitfalls, controls, baselines); the OpenAlex facts table (including two documentation-vs-API contradictions observed on 2026-09-28) and a dataset cost table; the ANS venue (scope, framing note, a 16-paper ANS citation base, a Table-1 draft, the article template); an emergence-evaluation checklist; open risks and cheap falsification tests; bibliography |
| `research_out.json` | Structured output: `answer` (condensed findings with numbered citations), `sources` (81 numbered sources with supporting passages), `follow_up_questions`. Written automatically from the agent's structured output |
| `reproducibility.md` | The searches, fetches, greps and API queries actually run, in order, with dates and how to retrace them |
| `.aii/manifest.yaml` | Storage manifest (nothing heavy is kept) |

## Key results (short)

- **Recommended headline candidate:** C1 host anchoring, with C2 co-transfer as its opposite-sign contrast. **Second:** C0 source/sink viability (strongest mechanism; needs circularity and coverage controls). C3 is mostly prior art and should be a baseline family. The generic "network features predict emergence" claim is already done (Science4Cast, Impact4Cast, Augur, Maillart et al. 2026).
- **OpenAlex, observed 2026-09-28:**
  - `keywords` are now identical to the legacy `concepts` in 11 of 12 sampled works; the `/keywords` entity has 65,004 items.
  - Concepts are still attached to 2026 works, which contradicts the documentation.
  - Share of core-source articles with zero references: 29.0% in 2005, 23.0% in 2016, 13.8% in 2020.
  - `mesh.descriptor_ui` is not a valid filter.
  - `per_page=200` is accepted.
- **Estimated dataset cost:** about $4–9 of API usage, i.e. a few days of the free $1/day allowance.

## How to "run" / retrace

There is no executable pipeline. To retrace, follow `reproducibility.md`. You need an OpenAlex API key, supplied as `&api_key=$OPENALEX_API_KEY`; no key is stored in this repository.

## Restoring removed files

Nothing was marked for deletion. The workspace holds only text files (markdown and JSON), so there is nothing to restore. Scratch downloads (Crossref listings and blocked Springer HTML stubs) lived in a session scratchpad outside this repository and are not needed.
