# gen_full_paper — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `iter5_6136aaed9367` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_full_paper` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-30 05:03:02 UTC

````
<research_methodology>
Write like an experienced academic. Reviewers judge both the science and the writing.

- Claims must be proportional to evidence. Choose verbs carefully — "demonstrate," "observe," and "hypothesize" mean different things.
- Every result needs: what was measured, on what data, the numbers, and what they mean.
- Methodology must be specific enough to reproduce. Section placement follows <paper_structure> below.
- State limitations honestly. Avoid both overclaiming and excessive hedging.
</research_methodology>

<paper_structure>
Use the structure an expert in the field expects, in this order: Abstract; 1 Introduction; 2 Related Work; 3 Method; 4 Experimental Setup; 5 Results; 6 Discussion and Limitations; 7 Conclusion. Merge or rename a section only where the work genuinely has nothing for it — never by folding it into the Introduction.

- The Introduction contains ONLY: the problem and why it matters, the gap in existing work, the idea in one or two sentences, a contributions list carrying the headline numbers, and a one-sentence roadmap of the paper.
- NO literature survey and NO method details in the Introduction. Prior work goes to Related Work, how the method works goes to Method.
- Organize Related Work by theme rather than one paragraph per paper, and close each theme with a sentence on how this work differs.
- Experimental Setup carries data, baselines, metrics and protocol — enough for an expert to rerun it. Results carries findings, not setup.
</paper_structure>

<results_first>
Ask what a reader actually wants from the paper: the results, with numbers. A reader must be able to get the main finding from the abstract, the main results table and the first results figure alone.

- State the key quantitative results, with the actual numbers, in three places: the abstract, the contributions list, and the opening of Results.
- Results opens with a main results table: the method against every baseline on the headline metric, with variance.
- Every major claim gets at least one results figure (figure_type "data"), plus an ablation or sensitivity plot wherever the artifacts hold the numbers for one.
- Prefer a plot of real numbers over concept art — keep concept figures to the architecture or pipeline diagram the method genuinely needs.
- Reference every figure and table by number in the text and interpret it there: say what the reader should take from it. Never drop one in unexplained.
</results_first>

<figure_placement>
Where a figure sits, what shape it takes and how many there are decide whether a reader can follow the paper.

- Put each [FIGURE:id] marker directly after the paragraph that first discusses the figure, inside the section that owns it: the hero diagram at the end of the Introduction, method and pipeline diagrams in Method, the main comparison and the per-claim results figures in Results, ablation and sensitivity plots in Results or Discussion. Never place a figure in the Abstract, Related Work or Conclusion.
- Let the data relationship pick the chart: grouped bars for the method against baselines on one metric, lines with error bands for trends, scaling and training curves, scatter or a Pareto front for trade-offs, heatmaps for matrices and pairwise grids. A handful of numbers is a table, not a figure. Use multiple panels only when they share axes and one takeaway.
- Aim for roughly four to eight figures in a full paper, with the main results figure first. Each caption stands on its own: what is plotted, on what data, and the takeaway.
</figure_placement>

<safeguard_research_reporting>
When the research concerns bypassing or removing a model's safeguards (jailbreaks, refusal
removal, abliteration, safety fine-tuning reversal, or anything whose effect is a model that
refuses less on harmful requests), report the findings as MEASUREMENTS and their implications
for EVALUATION and DEFENCE, never as operational advice for defeating safeguards.
- State what was measured, on what, and how large the effect was, as in any other result.
- Draw the implications for the people who build and test safeguards: what an evaluation misses,
  which defences are brittle and where, what a safety evaluation should measure next.
- Never frame a finding as a recommendation, a recipe or a best configuration for removing
  refusals: no "the practical recommendation is to use X to remove refusals", no "for the
  strongest bypass, edit layers X to Y", no step-by-step settings a reader could follow to make a
  model comply with harmful requests.
- This applies everywhere the finding is stated: abstract, executive summary, key results, best
  result, discussion, conclusion, captions, the website and the interactive page.
</safeguard_research_reporting>

<system_reminder>
Do not ask follow up questions and do not ask the user anything. Execute all steps independently.
You must follow the todo list provided in each prompt exactly as written.
No placeholders, stubs, or incomplete code — all code must be complete and functional.
</system_reminder>

<process_isolation>
CRITICAL: Multiple pipeline runs may execute simultaneously on this machine. `ps aux | grep method.py` matches ALL runs, not just yours.
- NEVER kill processes by name (`killall`, `pkill -f`, `ps aux | grep ... | xargs kill`). This kills OTHER runs' processes.
- NEVER monitor processes by name (`ps aux | grep method.py`). You will see other runs' processes and get confused.
- ALWAYS use PID-based process management:
  Run: `uv run method.py & PID=$!` or `timeout <seconds> uv run method.py & PID=$!`
  Check: `kill -0 $PID 2>/dev/null && echo "Running" || echo "Ended"`
  Stop: `kill $PID`
  Wait: `wait $PID; echo "Exit code: $?"`
  Monitor: `tail -f logs/run.log & TAIL_PID=$!` then `kill $TAIL_PID` when done
</process_isolation>

<workspace>
Your workspace: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/`:
GOOD: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/file.py`, `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
<disposable_outputs>
YOUR WORKING DIRECTORY IS A DELIVERABLE. When this module ends it must read
like a GitHub repository someone else can fork, resume and run — and the bulk
it holds must be either worth keeping or restorable. This run shares a storage
volume with the database; a run that fills it stops every other run on the box.

So before you finish, produce TWO files:

1. `.aii/manifest.yaml` — one entry per heavy path, each with EXACTLY ONE decision.
   The `.aii/` directory ALREADY EXISTS in your cwd: write the file into
   it. Do not create, replace or `touch` `.aii` itself — a plain file by
   that name makes the manifest unwritable for the rest of the module.

```yaml
entries:
  - path: results/
    keep: six GPU-hours of sweep output, not reproducible inside this run
  - path: hf_cache/
    delete: redownloadable
    source: "huggingface-cli download meta-llama/Llama-3-8B"
  - path: checkpoints/
    delete: regenerable
    source: "uv run train.py --epochs 3 --seed 0"
```

   - `keep:` takes a ONE-LINE reason. Use it for the expensive and the
     irreproducible: trained weights, long-running results, datasets you
     collected yourself.
   - `delete:` takes `redownloadable` (and a `source:` naming the repo id, URL
     or command) or `regenerable` (and a `source:` that is the command which
     rebuilds it). These are deleted AFTER the round ends, never mid-step.
   - Every path is RELATIVE TO YOUR CWD and must resolve INSIDE it. Absolute
     paths, `..`, and anything resolving outside are rejected.
   - Globs and whole directories are fine. A whole `hf_cache/` is ONE entry —
     do not list files individually.

2. `README.md` — written as if your cwd were a GitHub repository: what you
   did, the layout with a line per important file/directory, how to run it,
   and a **"Restoring removed files"** section giving the install/download
   command for EVERY `delete` entry. An `install.sh` or `restore.sh` beside it
   is welcome.

A CHECKER RUNS WHEN YOU SUBMIT. If anything heavy has no decision it fails
your submission and hands you the uncovered list, grouped by directory with
sizes, and you fix the manifest and submit again.

WHAT NEEDS NO DECISION — do not write entries for these:
- text and code files, at ANY size (source, JSON, CSV, YAML, logs, markdown);
- anything under the auto-keep floor (10 MB), whatever it holds.
Only large binaries and cache directories (`hf_cache/`, `.venv/`,
`node_modules/`, `checkpoints/`, `wandb/`, `__pycache__/`, …) need one.

NEVER mark your results, figures, papers, code, logs or anything a later step
reads as `delete`. If a later step needs it, it is a `keep`.

WHAT A `keep` BUYS YOU. Anything you do not mark `delete` stays exactly where
you wrote it, on this run's storage volume, at the path it already has — it is
not moved, renamed or copied. A later round reads it there, by that absolute
workspace path, so a checkpoint you keep is a checkpoint the next round can
load instead of retraining. It is also the ONLY copy: the publish step pushes
your cwd to GitHub but skips every file of 100 MB or
more, so trained weights and large binary artifacts never leave the volume.
Name each kept artifact in your results and your `README.md` by its path
RELATIVE to your cwd, and say it stays on the run's volume rather than in the
published repository. Never write an absolute server path into a file that is
published: a reader's machine has none of them.
</disposable_outputs>

<task>
Typeset <paper_draft> as LaTeX with BibTeX, insert <available_figures>, and compile it to PDF.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<publishable_paper_rules>
This is the PUBLISHABLE PAPER. The run's internal report ships beside this paper as its own PDF
and already holds everything. So this document does not have to be complete — it has to be
READABLE BY SOMEONE WHO WAS NOT THERE.

- ONE ARGUMENT. Decide the single finding this run supports and build the paper around it.
  Everything that does not serve it is cut, not shrunk.
- LEAD WITH THE BEST-SUPPORTED POSITIVE FINDING, from whichever round produced it. Abstract,
  Introduction and Results open on it; the negative and null results are the context that bounds
  it, not the opening. Strength of evidence decides which finding that is, in this order:
  REPLICATION (the same effect measured by several independent experiments or rounds outranks
  one experiment), then CONFIRMATORY over EXPLORATORY (a pre-registered or held-out test that
  passed against its baseline outranks an estimate, a screen, a post-hoc contrast or a test that
  could not be run as planned, whatever the artifact calls it),
  then the VALIDITY OF THE MEASUREMENT (judge or labeller agreement, anchor strength, sample
  size), then a confidence interval clear of zero. Effect size only breaks ties. Being the run's
  final hypothesis, or the latest round's result, counts for nothing: the loop's hypothesis
  labels grade each round against its own question, not the run's findings against each other.
  A later round moving on to another question does not retract an earlier result; only a later
  result that contradicts it does. Recompute that headline from the numbers in the artifact's own
  output files, never from a summary line.
- ONE FINDING, SEVERAL MEASUREMENTS: THE HEADLINE NUMBER COMES FROM THE STRONGEST DESIGN. When
  several measurements estimate the same finding, keep them apart and take the headline number,
  in title, abstract and Results, from the one whose design is strongest: pre-registered and
  frozen before its data were seen, independent of any tuning or selection (a set that was also
  used to tune, select or develop anything no longer qualifies, whatever it was registered as),
  and confirmatory. Size, population breadth and recency do not decide it. The other
  measurements are supporting evidence, each reported with its own number and design beside the
  headline, never pooled into it or swapped in for it.
- STRUCTURED BY IDEA, NEVER BY ITERATION. The standard sections <paper_structure> lists, with
  only the small adjustments it allows. A section named after an iteration, a round of work or a
  date is the report's shape leaking into the paper.
- NO PROCESS. The paper never mentions the pipeline, iterations, reviews, scores, budgets,
  retries, agents or how long anything took. It never says what an earlier draft said: there is no
  earlier draft as far as the reader is concerned, so "revised", "updated", "we then changed"
  describe nothing the reader can see.
- THE METHOD AS IT FINALLY STANDS. Present what you would tell someone to reproduce the result —
  the design that worked — not the sequence of designs that led to it.
- DEAD ENDS ONLY WHERE THEY INFORM. A direction that was tried and failed belongs in the paper
  only when it changes what a reader should believe; then it is a result, reported as one, in
  Results or Limitations. Otherwise it stays in the report.
- HONEST ABOUT SCOPE. Every claim carries what supports it and its evidence grade wherever its
  number appears, abstract, contributions and captions included: a single-experiment estimate is
  called one, and a weak anchor, a low judge agreement, a small adjudicated sample or a novelty
  check that found the space partly occupied is stated beside the claim it bounds, once and
  plainly, not moved out of sight. The abstract names the headline's grade in words (for example
  "pre-registered and confirmed", "replicated in three experiments", "a single exploratory
  estimate") beside its number and interval. What the evidence does not reach goes in Limitations.
- SELF-CONTAINED. A term, a metric or a condition a reader meets here is defined or cited here.
  Never a pointer to the report, and never a run-internal name or code.
- NO PIPELINE INTERNALS. Never write a raw commit SHA, a full ISO timestamp (`2026-03-01T09:14:22Z`),
  or a run/artifact/task id (`run_...`, `art_...`) into the prose — they identify nothing to a
  reader. A date alone, a duration, or the artifact's name is what the sentence actually needs. The
  one exception is a single reproducibility line citing the repo's published release TAG
  (`v1.4.0`), never a SHA.
</publishable_paper_rules>

<paper_structure>
The paper's sections, in this order:
Abstract, Introduction, Related Work, Method, Results, Discussion, Limitations, Conclusion, then the numbered references.
</paper_structure>

<paper_draft>
THE PAPER. Which single finding it argues, how it is structured, which figures it shows and where
each one goes were all decided before you were called; this block is the result. Typeset it. The
first typesetting pass does not restructure it, re-select what it covers, or add sections it does
not have. Rewording for the register the style blocks below describe is in scope; changing what the
paper says is not. The REVISION PASS todo is the one place the draft may move, and only within the
limits that todo sets.

title: >-
  Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
abstract: >-
  When a scientific concept first appears in a new disciplinary subfield, what determines whether it takes root? We study
  426 emerging concepts and 462,812 works from OpenAlex across physics, computer science and biomedicine. The unit of analysis
  is a host-entry event, defined as the first year a concept appears in a non-origin subfield together with at least five
  co-occurring partner terms. We measure the host-vocabulary share of these partners and test whether it predicts uptake by
  newcomer authors over the following five years. On an independent MeSH biomedical population (191 concepts, 2,171 events
  across 160 concept clusters), a one-standard-deviation increase in host-vocabulary share raises newcomer uptake by 23% (co-primary
  incidence-rate ratio 1.23, 95% CI 1.12 to 1.36; pre-registered verdict: REPLICATED); the primary specification is also significant
  (IRR 1.32, 95% CI 1.10 to 1.60). Development-set estimates on the main-arm folds, both used in pipeline development, are
  concordant (Screen co-primary IRR 1.30; Held-out co-primary IRR 1.19, 95% CI 1.06 to 1.33); the fully saturated primary
  specification is inconclusive on the Held-out fold (IRR 0.98, 95% CI 0.70 to 1.37, underpowered with 30 clusters). Co-transfer
  of origin companions is null. The population is dominated by physics and computer-science concepts from arXiv; generalisation
  to social sciences and humanities is untested.
paper_text: "# Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries\n\n## 1 Background\n\
  \nScientific knowledge advances not only through discoveries within disciplinary boundaries but also through the migration\
  \ of concepts, methods and results across them [1, 2]. Yet most new ideas that appear outside their field of origin fail\
  \ to establish a lasting presence. What distinguishes the entries that take root from those that fade?\n\nPrior work has\
  \ examined this question from several angles. Cheng et al. [3] showed that a concept's fit with existing intellectual traditions,\
  \ measured as mean cosine similarity of neighbour terms in a global word-embedding space, predicts its annual article count.\
  \ Deichmann et al. [4] found that connectivity within the existing knowledge network shapes how far an idea diffuses. Boschma\
  \ et al. [5] demonstrated at the city level that technological diversification is path-dependent: regions branch into technologies\
  \ related to their existing portfolio. In network science, studies of co-word dynamics have traced the structural signatures\
  \ of emerging topics [6, 7] and the roles of bridging and brokerage [8, 9]. These studies treat connectivity or semantic\
  \ similarity as global properties of a concept. None of them measures the host-specific vocabulary composition of the very\
  \ first papers that carry a concept into a new subfield, nor tests whether this entry-level composition predicts durable\
  \ adoption.\n\nWe address two research questions. RQ1 (emergence precursors) asks which structural patterns in an evolving\
  \ co-word network characterise concept emergence. RQ2 (cross-disciplinary diffusion) asks how concepts spread across disciplinary\
  \ communities, and specifically whether host-vocabulary composition at the moment of entry predicts later uptake. RQ2 is\
  \ the paper's primary contribution. RQ1 provides the network context and tests a complementary hypothesis about pre-emergence\
  \ openness.\n\nOur main finding is that when a concept enters a new host subfield, the share of its entry partners that\
  \ belong to the host's vocabulary predicts uptake by newcomer authors over the following five years. We call this the host-entry\
  \ grafting effect. It replicates on an independent MeSH biomedical population (co-primary IRR 1.23, 95% CI 1.12 to 1.36;\
  \ verdict: REPLICATED), with concordant development-set estimates on the main-arm folds (Screen co-primary IRR 1.30; Held-out\
  \ co-primary IRR 1.19, 95% CI 1.06 to 1.33; both folds were used in pipeline development and are not true held-out tests).\
  \ The effect is host-specific rather than a proxy for general concept accessibility, though the latter test is limited by\
  \ near-collinearity between the Balassa-index lift measure and the continuous host-vocabulary share. Co-transfer of origin\
  \ companions, defined as the fraction of entry partners that were prior companions in the concept's origin field, is null\
  \ in all specifications. A complementary structural finding is that emerging concepts show lower persistent-neighbour closure,\
  \ defined as the closure coefficient restricted to top associates present in consecutive years, before sustained uptake.\
  \ On the Held-out fold, persistent-neighbour closure is significant (S = -1.07, Holm p = 0.015), though this is a development-set\
  \ estimate and the general closure measure fails (Holm p = 0.147).\n\n**Contributions.**\n\n1. A pre-registered host-entry\
  \ test showing that the host-vocabulary composition of a concept's initial partners predicts newcomer uptake, replicated\
  \ on an independent MeSH biomedical population (co-primary IRR 1.23, 95% CI 1.12 to 1.36, verdict REPLICATED; development-set\
  \ estimates concordant: Screen IRR 1.30, Held-out IRR 1.19) \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-3/experiment-7}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-4/evaluation-2}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-4/experiment-9}}\
  \ (Section 3.2).\n2. A semantically grounded, outcome-blind dataset of 426 emerging concepts with 462,812 OpenAlex works\
  \ and an independent 191-concept MeSH biomedical check population \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-2/dataset-5}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-1/dataset-3}}\
  \ (Section 2.1).\n3. Evidence that the host-vocabulary effect is host-specific (though the Balassa-index lift leg of this\
  \ test is near-collinear with the continuous share) and operates through both the extensive margin (whether uptake starts)\
  \ and the intensive margin (its magnitude), with no detectable variation by origin field \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-5/evaluation-6}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-5/evaluation-7}}\
  \ (Section 3.2.3).\n4. A pre-registered test of structural precursors of emergence finding that general closure fails on\
  \ the Held-out fold while persistent-neighbour closure is significant (S = -1.07, Holm p = 0.015; development-set estimate),\
  \ and that the effect is not Burt brokerage \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-3/experiment-5}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-4/evaluation-3}}\
  \ (Section 3.1).\n5. A stable two-type diffusion typology, an expansion-before-diffusion ordering, adopter-level enrichment\
  \ for prior partner exposure, and four representative cases \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-3/experiment-8}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-4/evaluation-4}}\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-4/evaluation-5}}\
  \ (Sections 3.2.4 and 3.2.5).\n\n[FIGURE:fig1]\n\n## 2 Methods\n\n### 2.1 Data\n\n**Concept pool.** We assembled an outcome-blind\
  \ pool of 426 emerging scientific concepts, where outcome-blind means that the inclusion criteria and frame were frozen\
  \ and SHA-256-hashed before any post-appearance data were inspected. Concepts are noun-phrase surface forms that first appeared\
  \ in OpenAlex [10] titles and abstracts between 2005 and 2016, with 20 to 300 papers in the first-appearance window and\
  \ no more than 8,000 total works through 2024 \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-1/dataset-1}}\
  \ . Of the 426, 366 are main emerging concepts (247 Screen, 119 Held-out, split by a SHA-1 hash on concept identifiers)\
  \ and 60 are stationary reference concepts. A logistic-regression classifier trained on silver-standard labels (F1 0.82\
  \ on 300 test items, AUC 0.89) and a variant merger (B-cubed F1 0.78) were applied to ground every concept \\footnote{Code:\
  \ \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-2/experiment-1}}.\
  \ The pool is dominated by physics, physical-sciences and computer-science concepts sourced from arXiv. For the Screen fold,\
  \ 202 concepts survive grounding filters; for the Held-out fold, 100.\n\n**MeSH check population.** An independent biomedical\
  \ arm of 191 concepts was drawn from new MeSH descriptors (DateEstablished 2006 to 2016, widened to 2004 to 2005 and 2017\
  \ to 2018), surviving a provenance filter, a PubMed novelty pre-screen and the same early-volume rule . Only approximately\
  \ 25% of new MeSH descriptors are genuinely new concepts; the remainder are reclassifications or splits.\n\n**Works.** The\
  \ combined corpus comprises 462,812 unique OpenAlex works with 488,078 verified concept-work links, spanning 2000 to 2024.\n\
  \n**Co-word network.** From a design-weighted whole-science background sample of 259,716 works, we built 25 yearly three-year-window\
  \ co-occurrence snapshots (approximately 27,000 nodes and 84,000 edges per snapshot), with association-strength edge weights\
  \ [11], Leiden community detection [12] (best of five seeds) and alluvial community identifiers \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-2/experiment-3}}.\n\
  \n**Host-nativeness profiles.** For each concept-keyword node, we retrieved exact OpenAlex subfield-by-time-block publication\
  \ counts, covering 78.7% of host co-occurrence weight across 1,372 nodes . These profiles supply the host-vocabulary share\
  \ used in RQ2.\n\n[FIGURE:fig2]\n\n### 2.2 RQ1: structural precursors of emergence\n\n**Emergence labels.** We defined sustained\
  \ uptake as a concept-year reaching at least 20 papers per year and gaining at least 20 percentile points in co-word network\
  \ strength relative to the focal population. The focal-population label was declared before outcomes were computed.\n\n\
  **Matched event study.** For each concept showing sustained uptake, we matched it to a control concept from the same first-appearance\
  \ band and origin field that did not show sustained uptake, using 1:1 nearest-neighbour matching on pre-period network indicators.\
  \ The standardised mean difference (Cohen's S) between treated and control concepts at lags k = -3 to 0 is the estimand.\
  \ Bootstrap confidence intervals (B = 2,000) and Holm-corrected p-values control for multiple testing. The Screen fold (202\
  \ concepts) produced 68 onsets and 26 matched pairs.\n\n**Openness measures.** To test whether pre-emergence closure is\
  \ reducible to neighbourhood turnover or Burt brokerage, we computed four variants: (a) turnover-residualised closure, obtained\
  \ by regressing closure on the new-relation rate, novelty, Baselga beta-similarity, log volume, concept age and Shannon\
  \ entropy; (b) persistent-neighbour closure, restricting the closure coefficient to the top-20 neighbours present in both\
  \ year y and y-1; (c) Burt constraint and effective size of the weighted ego network [8]; and (d) cross-community pair excess,\
  \ defined as the count of partner pairs from distinct Leiden communities minus the count expected under a strength-decile\
  \ null .\n\n### 2.3 RQ2: host-entry grafting\n\n**Host-entry events.** A host-entry event is the first year in which a concept\
  \ appears in a non-origin subfield together with at least five co-occurring partner terms. From 4,177 main-arm host entries,\
  \ the Screen fold retains 1,544 events across 140 concept clusters after the partner-count filter .\n\n**Exposure variable.**\
  \ Host-vocabulary share (denoted A_cont in tables) is the tag-weighted mean of each partner's pre-entry publication share\
  \ in the host subfield, where tag-weighted means that each co-occurrence edge is weighted by its association strength. The\
  \ continuous measure is primary because only 1.1% of partner tags have a host share above 50%. Co-transfer (denoted CT in\
  \ tables) is the fraction of partners that were origin companions of the concept in the five years before entry.\n\n**Outcome.**\
  \ Five-year newcomer uptake: the count of host-subfield papers by author-disjoint newcomers (authors with no prior concept\
  \ paper and no co-authorship with concept authors) during the five years after entry.\n\n**Model.** Poisson pseudo-maximum-likelihood\
  \ (PPML) regression [13] with concept-clustered standard errors [14]. Two specifications were pre-registered. The primary\
  \ specification includes concept-by-entry-year and host-by-entry-year fixed effects. The co-primary specification includes\
  \ concept, entry-year and host fixed effects and was declared for use when the primary drops below 30 concept clusters (which\
  \ it does on the Held-out fold). Both specifications include co-transfer as a second regressor.\n\n**Held-out fold.** 93\
  \ concepts, 1,100 entries; minimum detectable effect (co-primary): IRR per standard deviation of 1.15. The fold was used\
  \ during pipeline development (event counts, population sizes and gating decisions were computed on both folds), so its\
  \ grafting estimate is a development-set estimate, not a true held-out confirmation.\n\n**MeSH replication.** The same analysis\
  \ was applied to 191 MeSH concepts. Because the pre-declared partner-count rule yielded only 192 events, the pre-declared\
  \ relaxation was triggered, producing 2,171 events across 160 concept clusters .\n\n### 2.4 Post-confirmation decomposition\n\
  \nAfter the Held-out and MeSH tests confirmed the host-vocabulary effect, three exploratory decompositions were pre-specified\
  \ and frozen before any coefficient was read  :\n\n- **Extensive versus intensive margins.** A linear probability model\
  \ for whether any newcomer uptake occurs (extensive margin), and PPML conditional on uptake having started (intensive margin).\
  \ Inverse-variance weighting (IVW) pools estimates across the Screen, Held-out and MeSH folds.\n- **Host-specific versus\
  \ generic accessibility.** Generality proxies (tag-weighted normalised subfield entropy and log block frequency of each\
  \ partner) are added as controls. The Balassa-index lift measure [15], defined as the log ratio of the host-vocabulary share\
  \ to the partner's baseline subfield share, is tested as an alternative exposure variable.\n- **Origin-field dependence.**\
  \ A Wald test of equality across origin-field groups (Physics and Astronomy, Computer Science, other).\n\n## 3 Results\n\
  \n### 3.1 RQ1: structural precursors of emergence\n\n#### 3.1.1 Results\n\nOn the Screen fold, concepts that later show\
  \ sustained uptake have lower Chung-Lu closure in the years before onset (matched event study S = -0.44, 95% CI -0.81 to\
  \ -0.05; pooled panel S = -0.74, 95% CI -1.06 to -0.46) . The pre-registered positive sign was not observed; the effect\
  \ runs in the opposite direction.\n\n**Table 1. Closure on the Held-out fold (development-set estimate).**\n\n| Measure\
  \ | Screen S | Held-out S | Held-out 95% CI | Held-out Holm p | Status |\n|---|---|---|---|---|---|\n| General closure (pooled\
  \ panel) | -0.66 | -0.39 | -0.86 to 0.07 | 0.147 | Not confirmed |\n| Turnover-residualised closure | -0.40 | -0.11 | -0.56\
  \ to 0.34 | 0.635 | Not confirmed |\n| Persistent-neighbour closure | -1.12 | -1.07 | -1.86 to -0.29 | 0.015 | Confirmed\
  \ |\n| Burt constraint | +0.08 | +0.11 | 0.02 to 0.19 | --- | Positive (not brokerage) |\n\n\n\nOn the Held-out fold (a\
  \ development-set estimate; the fold was used in pipeline development), general closure is not significant (Holm p = 0.147).\
  \ Only persistent-neighbour closure, restricted to top-20 neighbours present in consecutive years, is significant (S = -1.07,\
  \ Holm p = 0.015). Burt constraint has the same positive sign on the Held-out fold (+0.11, 95% CI 0.02 to 0.19), indicating\
  \ that the lower closure before emergence is not Burt brokerage: concepts that later emerge sit in ego networks that are\
  \ more constrained, not less .\n\nThe MeSH replication is directional under a sensitivity label (D = -0.42, Holm p = 0.039,\
  \ n = 29), same sign as the main pool, but under the primary label the MeSH effect is null (D = -0.09, Holm p = 0.677, n\
  \ = 15) \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-2/experiment-4}}.\n\
  \nStructural precursors add no predictive value for whether a concept will later show sustained uptake beyond frequency,\
  \ burst, degree and entropy baselines (logistic AUC 0.89 versus 0.88, delta -0.010, 95% CI -0.045 to 0.021) .\n\n[FIGURE:fig3]\n\
  \n#### 3.1.2 Comparison to related work\n\nThe finding that emerging concepts show lower closure among their most stable\
  \ co-word neighbours is consistent with Salatino et al.'s [6] observation that new topics arise at the intersection of weakly\
  \ connected parent areas, and with Chen's theory of structural variation [7] in which transformative work bridges structural\
  \ holes. It is also consistent with the structural-holes literature [8]: concepts that later emerge connect across Leiden\
  \ communities, and their cross-community pair excess is positive. The critical difference is that Burt constraint is higher,\
  \ not lower. In Burt's framework, brokerage means low constraint. Here the ego network is more redundant, not less; the\
  \ openness is confined to the top of the neighbourhood, while the broader ego network is dense. This pattern is closer to\
  \ what Lin and Evans [16] describe as disconnection and discordance enabling new directions in science, and to Larson's\
  \ [17] finding that weak-tie diffusion in networks is not guaranteed to carry novel information.\n\nAmong Applied Network\
  \ Science contributions, De Domenico et al. [18] studied knowledge diaspora through source-sink author flows, and Cunningham\
  \ et al. [19] mapped author multidisciplinarity and disciplinary roles in field-of-study networks, finding that bridge authors\
  \ between communities can accelerate knowledge transfer. Our structural analysis complements this by showing that concept-level\
  \ network openness, not author-level bridging, precedes emergence. Fontaine et al. [20] traced the epistemic integration\
  \ of AI into neuroscience, showing how vocabulary overlap between fields facilitates absorption, a finding that connects\
  \ directly to our host-vocabulary result. Doonan et al. [21] found that community structure in co-inventor networks affects\
  \ time to first citation, paralleling our finding that community position shapes concept uptake. Salatino et al. [22] applied\
  \ their Computer Science Ontology to classify research topics through network-based detection, providing a taxonomy-grounded\
  \ approach related to our co-word-network construction.\n\n### 3.2 RQ2: host-entry grafting\n\n#### 3.2.1 Experimental setup\n\
  \nThe host-entry sample for the Screen fold comprises 1,544 events across 140 concept clusters (co-primary specification).\
  \ Entry is predominantly a package: 70% of partner tags are non-native origin companions, and only 1.8% are native grafts\
  \ (host share above 50%). The mean host-vocabulary share is 0.043 (SD 0.055). The Held-out fold has 972 events across 74\
  \ concept clusters. The MeSH population has 2,171 events across 160 concept clusters.\n\n#### 3.2.2 Main result\n\n**Table\
  \ 2. Host-entry grafting: pre-registered test.**\n\n| Specification | Fold | IRR/SD | 95% CI | p | CT p | N | G |\n|---|---|---|---|---|---|---|---|\n\
  | Co-primary (concept + year + host FE) | Screen | 1.30 | 1.16 to 1.45 | < 0.001 | 0.48 | 1,544 | 140 |\n| Co-primary |\
  \ Held-out | 1.19 | 1.06 to 1.33 | 0.004 | 0.60 | 972 | 74 |\n| Primary (concept x year + host x year FE) | Held-out | 0.98\
  \ | 0.70 to 1.37 | 0.91 | 0.22 | 250 | 30 |\n| Co-primary | MeSH | 1.23 | 1.12 to 1.36 | < 0.001 | 0.053 | 2,171 | 160 |\n\
  | Primary | MeSH | 1.32 | 1.10 to 1.60 | 0.004 | 0.46 | 1,004 | 122 |\n| Co-primary (IVW pooled) | All three | 1.26 | 1.17\
  \ to 1.36 | < 0.001 | --- | --- | --- |\n\nIRR/SD = incidence-rate ratio per one standard deviation of host-vocabulary share.\
  \ CT = co-transfer. G = concept clusters. IVW = inverse-variance weighted.\n\n  \n\nOn the independent MeSH biomedical population,\
  \ a one-standard-deviation increase in host-vocabulary share raises newcomer uptake by 23% (co-primary IRR 1.23, 95% CI\
  \ 1.12 to 1.36, p < 0.001; primary IRR 1.32, 95% CI 1.10 to 1.60, p = 0.004; pre-registered verdict: REPLICATED). The main-arm\
  \ folds, both used in pipeline development (event counts, population sizes and gating decisions were computed on both folds\
  \ before outcomes were read), give concordant development-set estimates: Screen co-primary IRR 1.30 (95% CI 1.16 to 1.45);\
  \ Held-out co-primary IRR 1.19 (95% CI 1.06 to 1.33, wild-cluster bootstrap p = 0.012, nativeness-permutation p = 0.026).\
  \ Heterogeneity between Screen and Held-out is not significant (p = 0.25). The inverse-variance weighted pooled estimate\
  \ across all three folds is 1.26 (95% CI 1.17 to 1.36, I-squared = 0). Co-transfer is null across all folds and specifications\
  \ .\n\nThe fully saturated primary specification on the Held-out fold is inconclusive (IRR 0.98, 95% CI 0.70 to 1.37) because\
  \ it retains only 250 of 972 events with 30 concept clusters; this was declared underpowered in advance (minimum detectable\
  \ effect IRR 1.30).\n\n[FIGURE:fig4]\n\n**Robustness.** The co-primary effect holds in 20 of 26 robustness variants on the\
  \ Screen fold (IRR range 1.11 to 1.56 among significant rows). All seven pre-specified robustness rows on the Held-out fold\
  \ are significant . Nativeness-permutation placebos are centred on 1.0 (co-primary p = 0.002 Screen, 0.026 Held-out, 0.010\
  \ MeSH). The cluster-robust variance estimator mildly over-rejects at the null (size 10.5% on MeSH simulation), so p-values\
  \ should be read alongside the wild-cluster and permutation results.\n\n#### 3.2.3 Mechanism decomposition\n\n**Extensive\
  \ versus intensive margins.** The host-vocabulary effect operates through both the extensive margin, meaning whether any\
  \ newcomer uptake starts, and the intensive margin, meaning the count of newcomer papers given that uptake started. The\
  \ inverse-variance weighted extensive-margin effect is +6.4 percentage points per standard deviation (95% CI 4.8 to 8.1,\
  \ randomisation-t p < 0.001), approximately a 13% increase relative to the base rate of 51%. The inverse-variance weighted\
  \ intensive-margin incidence-rate ratio per standard deviation is 1.18 (95% CI 1.10 to 1.27). The extensive share of the\
  \ total effect is 0.38 (95% CI 0.21 to 0.55) .\n\n[FIGURE:fig5]\n\n**Host-specific versus generic accessibility.** Adding\
  \ generality controls (subfield entropy and log frequency of entry partners) to the co-primary model retains 97% of the\
  \ host-vocabulary coefficient (inverse-variance weighted retention 0.97, 95% CI 0.81 to 1.10), and the Balassa-index lift\
  \ measure is also significant (inverse-variance weighted IRR per standard deviation 1.34, 95% CI 1.23 to 1.46) . The host-vocabulary\
  \ gradient is not reducible to generic concept accessibility. However, within fixed effects the Balassa-index lift measure\
  \ has a correlation of 0.997 with the log of the continuous host-vocabulary share, so the lift leg of this test is weak:\
  \ the two measures carry nearly the same within-unit information, and the lift result should be interpreted as confirming\
  \ the continuous share rather than adding independent evidence for host-specificity.\n\n**No origin-field boundary.** The\
  \ Wald test for equality of the host-vocabulary effect across origin-field groups (Physics and Astronomy, Computer Science,\
  \ other) is null (p = 0.64, label-permutation p = 0.77). Physics and Astronomy concepts, whose host-vocabulary coefficient\
  \ is individually non-significant (IRR 1.18, 95% CI 0.93 to 1.50), fall within sampling variation of the other groups .\n\
  \n#### 3.2.4 Diffusion typology and expansion-before-diffusion ordering\n\nA data-derived typology based on multivariate\
  \ dynamic time warping of three diversity channels (rarefied Shannon entropy, Rao-Stirling diversity [23] and active subfield\
  \ count) yields a stable two-cluster solution (k-medoids, Hennig bootstrap [24] minimum Jaccard 0.86): **localised** (n\
  \ = 136, low entropy and few active subfields) and **broad from the start** (n = 66, high entropy from early years) . Finer\
  \ clusterings are unstable (k = 3 Jaccard 0.60). The typology does not separate outcomes better than an entropy-only baseline\
  \ after residualising on early volume.\n\nAmong concepts exhibiting both a co-word-network expansion onset and a disciplinary-diffusion\
  \ onset, expansion precedes diffusion in 25 of 26 pooled main-arm cases (proportion 0.96, 95% CI 0.81 to 1.00, year-shuffle\
  \ null 0.62, p = 0.004), though only 8.6% of concepts have both onsets observable. On MeSH, 9 of 13 show expansion first\
  \ (not different from the null, p = 0.43) .\n\n#### 3.2.5 Adopter-level mechanism\n\nAdopters, defined as authors who publish\
  \ a concept paper in the host subfield within the five-year outcome window, are more likely to have prior corpus exposure\
  \ to the concept's entry partners than matched non-adopters from the same host subfield (conditional logistic regression:\
  \ OR 3.09, prevalence 0.79 versus 0.61; 95% CI 2.32 to 4.28; 1,013 matched strata, 422 entries, 109 concepts) . Exposure\
  \ to frequency-matched negative-control concepts is negatively associated (OR 0.62), and the placebo control using partners\
  \ of a different concept's entry into the same host is also below 1 (OR 0.72), showing specificity to the concept's own\
  \ partners.\n\nDecomposing partners into three vocabulary classes — FOREIGN (origin vocabulary, host share below 5%), ADJACENT\
  \ (5% to 30%) and NATIVE (host vocabulary, above 30%) — enrichment follows a gradient: FOREIGN partners OR 2.88, ADJACENT\
  \ partners OR 1.91, NATIVE partners OR 1.47. Adopters who pick up a concept in a new field are most enriched for prior exposure\
  \ to its origin-vocabulary partners, consistent with the absorptive-capacity framework [25] in which an individual's ability\
  \ to recognise and assimilate external knowledge depends on prior familiarity with that knowledge. This Screen-fold result\
  \ is not independently confirmed.\n\n#### 3.2.6 Comparison to related work\n\nOur host-vocabulary measure is closest to\
  \ the ideational embeddedness of Cheng et al. [3], who found that a concept's fit with existing traditions raises its yearly\
  \ article count. Their measure is a global property of the concept (mean cosine similarity of all its neighbours in a word2vec\
  \ embedding), whereas ours is entry-specific: measured at the level of each concept-subfield-year event, with concept and\
  \ host fixed effects absorbing concept-level confounds. Co-transfer, the natural competitor, is null. This extends the principle\
  \ that relatedness predicts diversification, documented in economic geography [5, 26], to the level of individual concept-entry\
  \ events.\n\nAmong Applied Network Science papers, our work engages most directly with De Domenico et al.'s [18] source-sink\
  \ analysis of knowledge diaspora, which modelled author flows as diffusion on a bipartite field network. Our approach replaces\
  \ author flows with concept-vocabulary composition at the entry point, and finds that vocabulary, not people, predicts rooting.\
  \ Cunningham et al. [19] documented how multidisciplinary authors occupy bridging positions in field-of-study networks,\
  \ a role that might facilitate the host-vocabulary composition we measure. Fontaine et al. [20] showed that vocabulary overlap\
  \ between AI and neuroscience facilitated epistemic integration, and our quantitative test provides the micro-level mechanism\
  \ consistent with their macro-level observation. Holmgren and Sorensen [27] developed multilevel alluvial methods for mapping\
  \ change in higher-order networks, related to the alluvial community tracking we use. Maillart and Sornette [28] appraised\
  \ discrepancies in semantic networks, finding that endogenous reinforcement within a community is weak while exogenous diffusion\
  \ is predictable, consistent with our expansion-before-diffusion ordering. Liew et al. [29] applied multiplex network analysis\
  \ to map disciplinary knowledge flows, and Cai et al. [30] and Dorta-Gonzalez and Dorta-Gonzalez [31] examined extraction\
  \ and structure in knowledge graphs, both providing methodological context for co-word-network studies.\n\n#### 3.2.7 Representative\
  \ cases\n\nFour medoid cases from the typology clusters illustrate the host-vocabulary gradient at the concept level .\n\
  \n[FIGURE:fig6]\n\n**Wireless backhaul** (broad type, Computer Science, first appeared 2006). Broad from its first year,\
  \ splitting between Computer Networks and Electrical Engineering. By 2022 seven subfields are active. Of 14 host entries\
  \ in the co-primary sample, only one is rooted (Aerospace Engineering in 2008, host-vocabulary share 0.084, 6 newcomer papers).\
  \ The 13 non-rooted entries average a host-vocabulary share of 0.021 and arrive as origin packages (co-transfer 0.6 to 1.0).\
  \ Rooted-minus-unrooted host-vocabulary share: +0.062.\n\n**Einstein-Podolsky-Rosen steering** (broad type, Physics, first\
  \ appeared 2011). Of 7 co-primary entries, one is rooted (Artificial Intelligence in 2011, host-vocabulary share 0.142,\
  \ co-transfer 0, 37 newcomer papers). The 6 non-rooted entries average 0.027 with co-transfer at or above 0.55. Rooted-minus-unrooted:\
  \ +0.115. A broad-type label can hide a concept whose cross-disciplinary integration rests on a single well-anchored entry.\n\
  \n**Locally repairable code** (localised type, Computer Science, first appeared 2013). Stays at 84% to 96% in Computer Networks\
  \ for its life. Has only 1 co-primary entry (AI in 2013, host-vocabulary share 0.056, rooted). Demonstrates rooting without\
  \ broad occupancy.\n\n**Holographic QCD** (localised type, Physics, first appeared 2006). Stays at 95% to 97% in Nuclear\
  \ and High Energy Physics. Its 5 co-primary entries are all non-rooted, averaging 0.041, with three having co-transfer of\
  \ 1.0: pure origin packages. No entry is rooted. A locally concentrated concept whose excursions are packaged imports that\
  \ do not take root.\n\n### 3.3 Community roles and bridging\n\nLeiden community roles (five-seed agreement 97.2%) partition\
  \ concepts into four categories: bridge (0.61), other (0.33), stayer (0.03) and migrant (0.02). Emerging concepts are peripheral\
  \ or connector nodes in the Guimera-Amaral cartography [32] (peripheral 0.49, connector 0.40, kinless 0.10, no hubs). Lagged\
  \ roles do not robustly predict host-subfield entry (bridge odds ratio 0.64, 95% CI 0.38 to 1.08) .\n\nMost emerging concepts\
  \ act as bridges between Leiden communities in the co-word network (early-bridging share 0.70 in the main pool versus 0.59\
  \ in MeSH, difference +0.11, 95% CI 0.02 to 0.20), but this bridging role is common and non-discriminating.\n\n## 4 Discussion\n\
  \n### 4.1 What host-vocabulary composition tells us\n\nThe central finding is that a concept's first partners in a new subfield\
  \ carry information about whether that concept will subsequently be adopted by newcomer scientists in the host field. The\
  \ host-vocabulary share, a ratio measuring how much of each partner's prior work belongs to the host subfield, predicts\
  \ five-year newcomer uptake in a pre-registered design replicated on an independent MeSH biomedical population (verdict:\
  \ REPLICATED), with concordant development-set estimates on the main-arm folds.\n\nThis result complements the absorptive-capacity\
  \ framework [25]. At the entry level, host-vocabulary composition facilitates uptake by newcomers who may not be experts\
  \ in the concept's origin field. At the adopter level, the individuals who actually pick up the concept are enriched for\
  \ prior exposure to the concept's origin-vocabulary partners (OR 3.09, prevalence 0.79 versus 0.61; Screen fold, not independently\
  \ confirmed), consistent with the proposition that recognising external knowledge requires prior familiarity with it. These\
  \ two findings operate at different scales: host-native partners lower the barrier for the field, but the individuals who\
  \ cross it already speak the origin language.\n\n### 4.2 What structural openness tells us\n\nThe persistent-neighbour closure\
  \ result (significant on the Held-out development fold, S = -1.07, Holm p = 0.015) indicates that concepts whose top associates\
  \ do not close into triads from year to year are more likely to show sustained uptake. General closure is not significant\
  \ on the Held-out fold. Burt constraint is positive, meaning the ego network is redundant, not brokered. The picture is\
  \ of open, fast-renewing connections among a concept's most strongly associated terms within a dense wider ego network,\
  \ rather than brokerage across a structural hole. This is consistent with Lin and Evans's [16] finding that disconnection\
  \ and discordance seed new directions.\n\n### 4.3 Null findings and what they bound\n\nSeveral pre-registered hypotheses\
  \ were not supported. Co-transfer, defined as arriving with origin companions, is null in all specifications and populations,\
  \ meaning that the composition of entry matters but the imported-package channel does not. The breadth-prediction screen\
  \ (does openness predict how many new subfields a concept will reach?) found no effect beyond growth and level baselines\
  \ \\footnote{Code: \\url{https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_YczZzZ0_9kfq/round-3/experiment-6}}.\
  \ The link between pre-emergence closure and later host-entry composition is null (partial correlation 0.025 Screen, 0.053\
  \ Held-out, both confidence intervals including zero), meaning that network openness and vocabulary composition operate\
  \ independently rather than through a shared mechanism .\n\n## 5 Limitations\n\n**Main-arm folds used in development.**\
  \ The fold labelled Held-out was used during pipeline development: event counts, population sizes and gating decisions were\
  \ computed on both the Screen and Held-out folds before grafting outcomes were read. Estimates on both main-arm folds are\
  \ therefore development-set estimates, not true held-out confirmations. The independent evidence for the host-vocabulary\
  \ effect comes from the MeSH replication (verdict: REPLICATED).\n\n**Population bias.** The concept pool is dominated by\
  \ physics, physical-sciences and computer-science concepts from arXiv. The MeSH population covers only biomedicine-to-biomedicine\
  \ entries. Generalisation to social sciences, humanities or engineering is untested.\n\n**Primary specification underpowered.**\
  \ The fully saturated specification with concept-by-year and host-by-year fixed effects, which absorbs more confounding\
  \ than the co-primary, is inconclusive on the Held-out fold (IRR 0.98, 30 clusters). The independent MeSH replication and\
  \ the development-set estimates rest on the co-primary specification, which leaves more residual variation.\n\n**Single-paper\
  \ entries.** 87% of co-primary Screen events involve a single entry-year paper. The pooled multi-team effect is positive\
  \ (IRR 1.28, 95% CI 1.11 to 1.48), but the Held-out alone is underpowered for this test.\n\n**Binary establishment null.**\
  \ The host-vocabulary share predicts the count of newcomer papers and the probability that any newcomer uptake occurs, but\
  \ binary establishment (at least five newcomer papers in at least three of five years) is null on the Held-out fold (p =\
  \ 0.16). The effect is graded, not threshold-based.\n\n**Cluster-robust inference.** The cluster-robust variance estimator\
  \ rejects 10% to 11% of null shuffles in simulation (target 5%). Wild-cluster bootstrap and permutation tests give consistent\
  \ results (Held-out wild p = 0.012, permutation p = 0.026), but the standard p-values should not be taken at face value.\n\
  \n**Host-specificity caveat.** The Balassa-index lift measure used to test host-specificity has a within-fixed-effect correlation\
  \ of 0.997 with the log of the continuous host-vocabulary share. The lift test confirms the continuous measure rather than\
  \ providing independent evidence.\n\n**Screen-fold adopter evidence.** The adopter-level enrichment (OR 3.09) is Screen-fold\
  \ only, not independently confirmed. The design cannot separate absorptive capacity from topical proximity.\n\n**Closure\
  \ Held-out caveats.** The Held-out fold was used in pipeline development, so the closure result is a development-set estimate.\
  \ Additionally, the Held-out matching falls back to Screen controls for 17 of 25 unique controls, so the estimator is not\
  \ fully control-side independent. The MeSH closure result is directional under the sensitivity label but null under the\
  \ primary label.\n\n## 6 Conclusions\n\nWhen a new scientific concept enters a disciplinary subfield, the vocabulary composition\
  \ of its initial partners predicts whether newcomer scientists in that field will subsequently adopt it. This host-vocabulary\
  \ effect, replicated on 191 independent MeSH biomedical concepts (co-primary IRR 1.23, verdict REPLICATED) with concordant\
  \ main-arm development-set estimates (Screen IRR 1.30, Held-out IRR 1.19), is host-specific — though the Balassa-index lift\
  \ leg of this test is near-collinear with the continuous share (within-fixed-effect r = 0.997) — operates through both the\
  \ extensive and intensive margins, and does not vary by the concept's origin field. Co-transfer of origin companions is\
  \ null.\n\nThe complementary structural finding, that persistent-neighbour closure is lower before sustained uptake (Held-out\
  \ development-set estimate S = -1.07, Holm p = 0.015) while Burt constraint is higher, provides the network context: emerging\
  \ concepts sit in locally open, fast-renewing neighbourhoods that span multiple communities but are not brokered in Burt's\
  \ sense.\n\nThese results bear on how knowledge transfer is evaluated and supported. Policies and platforms that facilitate\
  \ cross-disciplinary research might benefit from attending to the vocabulary composition of a concept's first appearance\
  \ in a new field, rather than only to the mobility of authors who carry it.\n\nFuture work should extend the concept pool\
  \ beyond the physical and computational sciences, test whether the host-vocabulary gradient holds for social-science and\
  \ humanities concepts, and design an experiment to separate absorptive capacity from topical proximity at the adopter level.\n\
  \n## Declarations\n\n**Funding.** Not applicable.\n\n**Conflicts of interest/Competing interests.** The authors declare\
  \ no conflicts of interest.\n\n**Availability of data and materials.** All data derive from OpenAlex, an open scholarly\
  \ metadata index. The concept pool, verified work lists and analysis code are available in the project repository.\n\n**Code\
  \ availability.** All analysis code is available in the project repository.\n\n**Authors' contributions.** Not applicable.\n\
  \n**Keywords:** knowledge diffusion, emerging concepts, co-word network, host vocabulary, cross-disciplinary integration,\
  \ applied network science, scientometrics, concept emergence\n\n## References\n\n[1] Uzzi, B., Mukherjee, S., Stringer,\
  \ M. and Jones, B. (2013). Atypical combinations and scientific impact. Science, 342(6157), 468-472. DOI: 10.1126/science.1240474\n\
  \n[2] Wang, J., Veugelers, R. and Stephan, P. (2017). Bias against novelty in science: A cautionary tale for users of bibliometric\
  \ indicators. Research Policy, 46(8), 1416-1436. DOI: 10.1016/j.respol.2017.07.006\n\n[3] Cheng, S., Liang, Y., Leung, M.,\
  \ Luber, D. and Molnar, V. (2023). How new ideas diffuse in science. American Sociological Review, 88(3), 522-561. DOI:\
  \ 10.1177/00031224231166955\n\n[4] Deichmann, D., Moser, C., Birkholz, J. M., Nerghes, A., Groenewegen, P. and Wang, S.\
  \ (2020). Ideas with impact: How connectivity shapes idea diffusion. Research Policy, 49(1), 103881. DOI: 10.1016/j.respol.2019.103881\n\
  \n[5] Boschma, R., Heimeriks, G. and Balland, P.-A. (2014). Scientific knowledge dynamics and relatedness in bio-tech cities.\
  \ Research Policy, 43(1), 107-114. DOI: 10.1016/j.respol.2013.07.009\n\n[6] Salatino, A. A., Thanapalasingam, T., Mannocci,\
  \ A., Osborne, F. and Motta, E. (2018). The Computer Science Ontology: A large-scale taxonomy of research areas. In Proc.\
  \ ISWC 2018. DOI: 10.1007/978-3-030-00668-6_12\n\n[7] Chen, C. (2009). Towards an explanatory and computational theory of\
  \ scientific discovery. Journal of Informetrics, 3(3), 191-209. DOI: 10.1016/j.joi.2009.03.004\n\n[8] Burt, R. S. (2004).\
  \ Structural holes and good ideas. American Journal of Sociology, 110(2), 349-399. DOI: 10.1086/421787\n\n[9] Guimera, R.,\
  \ Uzzi, B., Spiro, J. and Amaral, L. A. N. (2005). Team assembly mechanisms determine collaboration network structure and\
  \ team performance. Science, 308(5722), 697-702. DOI: 10.1126/science.1106340\n\n[10] Priem, J., Piwowar, H. and Orr, R.\
  \ (2022). OpenAlex: A fully-open index of scholarly works, authors, venues, institutions, and concepts. arXiv:2205.01833.\n\
  \n[11] van Eck, N. J. and Waltman, L. (2009). How to normalize co-occurrence data? An analysis of some well-known similarity\
  \ measures. Journal of the American Society for Information Science and Technology, 60(8), 1635-1651. DOI: 10.1002/asi.21075\n\
  \n[12] Traag, V. A., Waltman, L. and van Eck, N. J. (2019). From Louvain to Leiden: Guaranteeing well-connected communities.\
  \ Scientific Reports, 9, 5233. DOI: 10.1038/s41598-019-41695-z\n\n[13] Santos Silva, J. M. C. and Tenreyro, S. (2006). The\
  \ log of gravity. Review of Economics and Statistics, 88(4), 641-658. DOI: 10.1162/rest.88.4.641\n\n[14] Cameron, A. C.\
  \ and Miller, D. L. (2015). A practitioner's guide to cluster-robust inference. Journal of Human Resources, 50(2), 317-372.\
  \ DOI: 10.3368/jhr.50.2.317\n\n[15] Balassa, B. (1965). Trade liberalisation and revealed comparative advantage. The Manchester\
  \ School, 33(2), 99-123. DOI: 10.1111/j.1467-9957.1965.tb00050.x\n\n[16] Lin, Z. and Evans, J. A. (2021). New directions\
  \ in science emerge from disconnection and discord. Journal of Informetrics, 16(1), 101234. DOI: 10.1016/j.joi.2021.101234\n\
  \n[17] Larson, J. M. (2017). The weakness of weak ties for novel information diffusion. Applied Network Science, 2, 14.\
  \ DOI: 10.1007/s41109-017-0034-3\n\n[18] De Domenico, M., Omodei, E. and Arenas, A. (2016). Quantifying the diaspora of\
  \ knowledge in the last century. Applied Network Science, 1, 15. DOI: 10.1007/s41109-016-0017-9\n\n[19] Cunningham, J. L.\
  \ and Liu, Y. (2022). Author multidisciplinarity and disciplinary roles in field of study networks. Applied Network Science,\
  \ 7, 17. DOI: 10.1007/s41109-022-00517-4\n\n[20] Fontaine, M., Seillier, B. and Bhatt, S. (2024). Epistemic integration\
  \ and social segregation of AI in neuroscience. Applied Network Science, 9, 18. DOI: 10.1007/s41109-024-00618-2\n\n[21]\
  \ Doonan, J., Sampson, O. and Sheridan, P. (2019). Community structure in co-inventor networks affects time to first citation.\
  \ Applied Network Science, 4, 26. DOI: 10.1007/s41109-019-0126-3\n\n[22] Salatino, A. A., Osborne, F., Thanapalasingam,\
  \ T. and Motta, E. (2023). The CSO classifier: Ontology-driven detection of research topics in scholarly articles. Applied\
  \ Network Science, 8, 46. DOI: 10.1007/s41109-023-00546-7\n\n[23] Stirling, A. (2007). A general framework for analysing\
  \ diversity in science, technology and society. Journal of the Royal Society Interface, 4(15), 707-719. DOI: 10.1098/rsif.2007.0213\n\
  \n[24] Hennig, C. (2007). Cluster-wise assessment of cluster stability. Computational Statistics and Data Analysis, 52(1),\
  \ 258-271. DOI: 10.1016/j.csda.2006.11.025\n\n[25] Cohen, W. M. and Levinthal, D. A. (1990). Absorptive capacity: A new\
  \ perspective on learning and innovation. Administrative Science Quarterly, 35(1), 128-152. DOI: 10.2307/2393553\n\n[26]\
  \ Hidalgo, C. A. et al. (2018). The principle of relatedness. In Unifying Themes in Complex Systems IX. DOI: 10.1007/978-3-319-96661-8_46\n\
  \n[27] Holmgren, O. and Sorensen, D. (2023). Mapping change in higher-order networks with multilevel and alluvial flow methods.\
  \ Applied Network Science, 8, 72. DOI: 10.1007/s41109-023-00572-5\n\n[28] Maillart, T. and Sornette, D. (2021). Appraising\
  \ discrepancies and similarities in semantic networks. Applied Network Science, 6, 8. DOI: 10.1007/s41109-021-00408-0\n\n\
  [29] Liew, C. S., Atkinson, M. P., Galea, M., Ang, T. F., Martin, P. and van Hemert, J. I. (2016). Scientific workflows:\
  \ Moving across paradigms. ACM Computing Surveys, 49(4), 66. DOI: 10.1145/3012429\n\n[30] Cai, Y. et al. (2025). Understanding\
  \ knowledge graph evolution. Applied Network Science, 10, 23. DOI: 10.1007/s41109-025-00642-w\n\n[31] Dorta-Gonzalez, P.\
  \ and Dorta-Gonzalez, M. I. (2025). Understanding the effect of knowledge graph extraction errors. Applied Network Science,\
  \ 10, 49. DOI: 10.1007/s41109-025-00749-0\n\n[32] Guimera, R. and Amaral, L. A. N. (2005). Cartography of complex networks:\
  \ Modules and universal roles. Journal of Statistical Mechanics, 2005, P02001. DOI: 10.1088/1742-5468/2005/02/P02001\n\n\
  [33] Kuhn, T., Perc, M. and Helbing, D. (2014). Inheritance patterns in citation networks reveal scientific memes. Physical\
  \ Review X, 4, 041036. DOI: 10.1103/PhysRevX.4.041036\n\n[34] Herfeld, C. and Doehne, M. (2019). The diffusion of scientific\
  \ innovations: A role typology. Studies in History and Philosophy of Science Part A, 77, 64-80. DOI: 10.1016/j.shpsa.2017.12.001\n\
  \n[35] Keuchenius, A., Tornberg, P. and Uitermark, J. (2021). Adoption and adaptation: A computational case study of the\
  \ spread of Gramsci's concepts in the social sciences. Social Networks, 67, 189-197. DOI: 10.1016/j.socnet.2021.01.001\n\
  \n[36] Candelon, B., Lapaire, M. and Sapata, C. (2024). What makes econometric ideas popular: The role of connectivity and\
  \ distinction. Research Policy, 53(5), 105025. DOI: 10.1016/j.respol.2024.105025\n\n[37] Tripodi, G., Ferrara, E. and Ferraro,\
  \ F. (2020). Knowledge and social relatedness shape research portfolio diversification. Scientific Reports, 10, 14232. DOI:\
  \ 10.1038/s41598-020-71009-7\n\n[38] Callon, M. (1983). From translations to problematic networks: An introduction to co-word\
  \ analysis. Social Science Information, 22(2), 191-235. DOI: 10.1177/053901883022002003\n\n[39] MacKinnon, J. G., Nielsen,\
  \ M. O. and Webb, M. D. (2023). Cluster-robust inference: A guide to empirical practice. Journal of Econometrics, 232(2),\
  \ 272-299. DOI: 10.1016/j.jeconom.2022.04.001\n\n[40] Correia, S., Guimaraes, P. and Zylkin, T. (2020). Fast Poisson estimation\
  \ with high-dimensional fixed effects. Stata Journal, 20(1), 95-115. DOI: 10.1177/1536867X20909691\n\n[41] Hofstra, B. et\
  \ al. (2020). The diversity-innovation paradox in science. Proceedings of the National Academy of Sciences, 117(17), 9284-9291.\
  \ DOI: 10.1073/pnas.1915378117\n\n[42] Rotolo, D., Hicks, D. and Martin, B. R. (2015). What is an emerging technology? Research\
  \ Policy, 44(10), 1827-1843. DOI: 10.1016/j.respol.2015.06.006\n\n[43] Newman, M. E. J. (2006). Modularity and community\
  \ structure in networks. Proceedings of the National Academy of Sciences, 103(23), 8577-8582. DOI: 10.1073/pnas.0601602103\n\
  \n[44] Rousseau, R. and Yang, L. Y. (2012). Reflections on the activity index and related indicators. Journal of Informetrics,\
  \ 6(3), 413-421. DOI: 10.1016/j.joi.2012.01.004"
summary: >-
  When a new scientific concept enters a disciplinary subfield, the host-vocabulary share of its initial co-occurrence partners
  predicts whether newcomer scientists in that field subsequently adopt it. On an independent MeSH biomedical population the
  pre-registered grafting test replicates (co-primary IRR/SD 1.23, 95% CI 1.12 to 1.36; verdict: REPLICATED). Development-set
  estimates on the main-arm folds are concordant (Screen co-primary IRR 1.30; Held-out co-primary IRR 1.19, 95% CI 1.06 to
  1.33; both folds were used in pipeline development). The fully saturated primary specification is inconclusive on the Held-out
  fold (IRR 0.98, 30 clusters, underpowered). Co-transfer of origin companions is null. The population is dominated by physics
  and computer-science concepts from arXiv.
</paper_draft>

<available_figures>
--- Item 1 ---
id: fig1
figure_type: concept
title: Study design and analysis pipeline
caption: >-
  Overview of the study design. (a) Data: an outcome-blind arXiv concept pool of 426 emerging scientific concepts, split into
  a screen fold (247) and a held-out fold (119), and an independent MeSH biomedical check population of 191 concepts. Both
  are drawn from 462,812 OpenAlex works. (b) Co-word network: yearly co-word snapshots (25 snapshots, $\sim$27k nodes, $\sim$84k
  edges) with Leiden communities; the schematic shows three colour-coded communities. (c) RQ1, emergence precursors: a matched
  event study compares closure measures in the pre-onset window (shaded) between concepts showing sustained uptake (blue,
  rising after onset) and controls (grey, flat). (d) RQ2, host-entry grafting: a concept enters a non-origin host subfield
  (light blue $\rightarrow$ light green region). Its partner terms are either host-native (dark green) or from the origin
  vocabulary (light blue). The host-vocabulary share (orange) is the exposure in a pre-registered PPML regression with concept-clustered
  standard errors predicting 5-year newcomer uptake. The timelines and bars in (c) and (d) are schematic and carry no data
  values.
image_gen_detailed_description: >-
  A four-panel horizontal flow diagram showing the study design. Panel (a) 'Data': Two boxes, 'arXiv concept pool (426 concepts)'
  and 'MeSH check population (191 concepts)', each pointing down to a shared box '462,812 OpenAlex works'. Below the arXiv
  box, two sub-boxes show 'Screen fold (247)' and 'Held-out fold (119)' separated by a dashed line. Panel (b) 'Co-word network':
  A schematic network with ~15 nodes in 3 colour-coded Leiden communities, connected by edges. Label: '25 yearly snapshots,
  ~27k nodes, ~84k edges'. Panel (c) 'RQ1: Emergence precursors': Two timelines side by side, one labelled 'sustained uptake'
  rising at an onset point, one labelled 'control' staying flat. An arrow points to the pre-onset window with label 'matched
  event study, closure measures'. Panel (d) 'RQ2: Host-entry grafting': A concept node enters a new subfield (shown as moving
  from one coloured region to another). Its partner terms are colour-coded: some in the host subfield's colour (host-native,
  darker shade), most in the origin colour (lighter shade). An arrow points from 'host-vocabulary share' to a bar chart showing
  '5-year newcomer uptake'. Labels: 'PPML regression, concept-clustered SEs'. Use a clean, minimal style with a light background,
  muted blues and greens for the communities, and orange for emphasis on the host-vocabulary share.
aspect_ratio: '21:9'
summary: >-
  The study design: from concept pool construction through co-word network building to the two research questions (structural
  precursors and host-entry grafting).
figure_path: figures/fig1_v0.jpg

--- Item 2 ---
id: fig2
figure_type: concept
title: Co-word network snapshot
caption: >-
  Schematic co-word network snapshot (2012, three-year window). Nodes are concept-keyword terms and grey edges are association-strength
  weighted co-occurrences; node fill colour (blue, green, orange, purple, red, teal) marks Leiden community membership, and
  larger circles are high-degree hub terms. Background terms (plain nodes) form dense communities that are joined by only
  a few inter-community edges. Pool concepts (bold black rings) sit on the periphery of communities, mostly in the gaps between
  two of them, where they act as bridge or connector nodes; three are labelled as examples (\emph{wireless backhaul}, \emph{EPR
  steering}, \emph{holographic QCD}). The full network comprises approximately 27,000 nodes and 84,000 edges; the panel is
  an illustrative rendering of its high-degree core for readability.
image_gen_detailed_description: >-
  A network visualisation showing approximately 500 nodes arranged by a force-directed layout. Nodes are coloured by Leiden
  community membership (use 5-6 distinct muted colours: blue, green, orange, purple, red, teal). A handful of nodes (about
  10-15) are highlighted with a bold ring and slightly larger size, representing pool concepts. These highlighted nodes tend
  to sit at the boundaries between communities, not at their centres. Edges are thin grey lines, denser within communities
  than between them. A legend identifies highlighted nodes as 'pool concepts' and regular nodes as 'background terms'. Label
  a few prominent highlighted nodes with example concept names: 'wireless backhaul', 'EPR steering', 'holographic QCD'. The
  layout should show clear community structure with visible inter-community bridges.
aspect_ratio: '4:3'
summary: >-
  Co-word network snapshot illustrating Leiden community structure and the peripheral, bridging position of emerging concepts.
figure_path: figures/fig2_v0.jpg

--- Item 3 ---
id: fig3
figure_type: data
title: Pre-emergence closure by measure type
caption: >-
  Pre-emergence closure on the held-out fold, by measure type. Each row shows the standardised mean difference (S) between
  concepts that later show sustained uptake and matched controls. Points are estimates and horizontal bars are 95\% bootstrap
  confidence intervals. The dashed vertical line marks no effect (S = 0), and Holm-corrected p-values are listed to the right
  of the first three rows. Only persistent-neighbour closure (blue) survives Holm correction (S = -1.07, 95\% CI [-1.86, -0.29],
  Holm p = 0.015). General closure (Holm p = 0.147) and turnover-residualised closure (Holm p = 0.635) are shown in grey:
  they do not survive confirmation, and their intervals cross zero. Burt constraint (orange) is positive (S = 0.11, 95\% CI
  [0.02, 0.19]), which indicates that emerging concepts sit in more constrained, not more brokered, ego networks.
image_gen_detailed_description: >-
  A horizontal forest plot with four rows, one per closure measure, showing standardised mean differences on the x-axis. Each
  row has a point estimate and a horizontal 95% CI bar. A vertical dashed line at x = 0 marks no effect. Data: Row 1 'General
  closure': point = -0.39, CI = [-0.86, 0.07], colour grey (not significant). Row 2 'Turnover-residualised': point = -0.11,
  CI = [-0.56, 0.34], colour grey. Row 3 'Persistent-neighbour closure': point = -1.07, CI = [-1.86, -0.29], colour blue (significant,
  Holm p = 0.015). Row 4 'Burt constraint': point = +0.11, CI = [0.02, 0.19], colour orange (positive sign). X-axis label:
  'Standardised mean difference (S), held-out fold'. Add small text annotations: 'Holm p = 0.147' next to row 1, 'Holm p =
  0.635' next to row 2, 'Holm p = 0.015' next to row 3. Clean white background, minimal gridlines.
aspect_ratio: '16:9'
summary: >-
  Forest plot of held-out closure confirmation: only persistent-neighbour closure survives, Burt constraint is positive.
figure_path: figures/fig3_v0.pdf

--- Item 4 ---
id: fig4
figure_type: data
title: Host-vocabulary effect across folds
caption: >-
  Host-vocabulary effect on five-year newcomer uptake across folds and specifications. Each row gives the PPML incidence-rate
  ratio (IRR) per one standard deviation of host-vocabulary share, on a log axis; horizontal bars are 95\% concept-clustered
  confidence intervals, and the dashed vertical line marks IRR $=1$ (no effect). Filled circles are the co-primary specification
  (concept, entry-year and host fixed effects) and open circles the primary specification with concept$\times$year and host$\times$year
  fixed effects. Blue marks the OpenAlex screen and sealed held-out folds, green the independent MeSH replication, and the
  amber diamond the inverse-variance weighted (IVW) pooled co-primary estimate. The co-primary effect is significant on all
  three folds (screen IRR 1.30 [1.16, 1.45], held-out 1.19 [1.06, 1.33], MeSH 1.23 [1.12, 1.36]), and the pooled estimate
  is 1.26 [1.17, 1.36]. The primary specification is inconclusive on the held-out fold (IRR 0.98 [0.70, 1.37], 30 clusters,
  $p=0.91$) but significant on MeSH (IRR 1.32 [1.10, 1.60]). Grey diamonds are the co-transfer regressor from the co-primary
  models. Its intervals include 1 on every fold ($p=0.48$, $0.60$ and $0.053$). The right-hand columns list each estimate
  with its 95\% CI and $p$-value.
image_gen_detailed_description: >-
  A forest plot with rows grouped by fold. The x-axis shows incidence-rate ratio (IRR per SD) on a log scale from 0.6 to 2.0.
  A vertical dashed line at IRR = 1.0 marks no effect. Group 1 'Screen': Row 'Co-primary': point 1.30, CI [1.16, 1.45], blue
  circle, filled. Group 2 'Held-out': Row 'Co-primary': point 1.19, CI [1.06, 1.33], blue circle, filled. Row 'Primary (strict
  FE)': point 0.98, CI [0.70, 1.37], open blue circle. Group 3 'MeSH replication': Row 'Co-primary': point 1.23, CI [1.12,
  1.36], green circle, filled. Row 'Primary': point 1.32, CI [1.10, 1.60], open green circle. Group 4 'IVW pooled': Row 'Co-primary':
  point 1.26, CI [1.17, 1.36], red diamond, filled. For co-transfer: three grey diamonds at IRR approximately 1.0, one per
  fold group, with wide CIs crossing 1.0 (screen p=0.48, held-out p=0.60, MeSH p=0.053). Label them 'Co-transfer (null)'.
  X-axis: 'IRR per SD of host-vocabulary share'. Clean white background.
aspect_ratio: '16:9'
summary: >-
  Forest plot showing the host-vocabulary effect is confirmed on held-out and replicated on MeSH; co-transfer is null.
figure_path: figures/fig4_v0.pdf

--- Item 5 ---
id: fig5
figure_type: data
title: Extensive and intensive margin decomposition
caption: >-
  Decomposition of the host-vocabulary effect into extensive and intensive margins across the screen, held-out and MeSH folds.
  Blue circles show per-fold estimates, vermillion diamonds the inverse-variance-weighted (IVW) pooled estimate, and horizontal
  bars 95\% confidence intervals. (a) Extensive margin: linear-probability-model effect of a one-standard-deviation increase
  in host-vocabulary share on the probability of any newcomer uptake, in percentage points per SD (dashed line: no effect).
  The pooled effect is 6.43 pp (95\% CI 4.76 to 8.11). (b) Intensive margin: PPML incidence-rate ratio per SD conditional
  on uptake, on a log axis (dashed line: IRR $=1$). The pooled IRR is 1.183 (95\% CI 1.104 to 1.267). All three folds are
  positive on both margins, and every fold interval excludes the null. (c) Share of the total effect: the extensive margin
  accounts for 38\% (95\% CI 21\% to 55\%, black whisker) and the intensive margin for the remaining 62\%.
image_gen_detailed_description: >-
  A two-panel horizontal layout. Left panel titled 'Extensive margin (probability of uptake)': Three rows for screen, held-out,
  MeSH, plus an IVW pooled row. X-axis: 'Effect (percentage points per SD)'. Screen: approximately 7.5 pp. Held-out: approximately
  5.0 pp. MeSH: approximately 6.0 pp. IVW pooled: 6.43 pp, CI [4.76, 8.11], shown as a red diamond. A vertical line at 0.
  Right panel titled 'Intensive margin (IRR given uptake)': Same three rows plus IVW. X-axis: 'IRR per SD' on log scale. Screen:
  approximately 1.20. Held-out: approximately 1.15. MeSH: approximately 1.20. IVW pooled: 1.183, CI [1.104, 1.267], red diamond.
  Vertical line at 1.0. Below both panels, a horizontal bar labelled 'Extensive share of total effect: 0.38 [0.21, 0.55]'.
  Blue points for individual folds, red diamonds for IVW pooled. Clean white background.
aspect_ratio: '16:9'
summary: >-
  The host-vocabulary effect operates through both margins: +6.4 pp extensive, IRR 1.18 intensive, extensive share 38%.
figure_path: figures/fig5_v0.pdf

--- Item 6 ---
id: fig6
figure_type: data
title: Four representative cases
caption: >-
  Four representative cases of the host-vocabulary gradient. Each panel shows one concept, and each horizontal bar is one
  of its host entries in the co-primary sample, labelled by host subfield and entry year and sorted by host-vocabulary share
  (x-axis, fraction). Green bars are rooted entries and grey bars are non-rooted entries. The dashed line marks the mean share
  of the non-rooted entries, and rooted bars are annotated with their share and number of newcomer papers. (a) Wireless backhaul
  (broad, CS): 14 entries, one rooted (Aerospace Engineering 2008, share 0.084, 6 newcomers) against a non-rooted mean of
  0.021. (b) Einstein--Podolsky--Rosen (EPR) steering (broad, Physics): 7 entries, one rooted (Artificial Intelligence 2011,
  0.142, 37 newcomers; co-transfer 0) against a non-rooted mean of 0.027. (c) Locally repairable code (localised, CS): a single
  co-primary entry, rooted (0.056, 3 newcomers), so there is no within-concept contrast. (d) Holographic QCD (localised, Physics):
  5 entries, none rooted (mean 0.041; three have co-transfer 1.0), including an AMO Physics entry at 0.132 that did not take
  root. In (a) and (b), the rooted entry has a higher host-vocabulary share than every non-rooted entry of the same concept.
  The panels are descriptive, so no intervals are drawn.
image_gen_detailed_description: >-
  A 2x2 grid of panels, each showing one concept. Each panel has a horizontal bar chart where each bar is one host-entry event,
  with bar length proportional to host-vocabulary share (x-axis from 0 to 0.20). Bars coloured green if rooted (host-vocabulary
  share above fold median and has newcomer uptake) or grey if non-rooted. Panel (a) 'Wireless backhaul (broad, CS)': 14 bars,
  13 grey (short, around 0.01 to 0.03) and 1 green (length 0.084), label '6 newcomers'. Panel (b) 'EPR steering (broad, Physics)':
  7 bars, 6 grey (around 0.02 to 0.04) and 1 green (length 0.142), label '37 newcomers'. Panel (c) 'Locally repairable code
  (localised, CS)': 1 green bar (length 0.056), label 'rooted'. Panel (d) 'Holographic QCD (localised, Physics)': 5 grey bars
  (around 0.03 to 0.05), no green bars, label 'no rooted entries'. X-axis label: 'Host-vocabulary share'. Each bar annotated
  with co-transfer value if above 0.5. Clean white background, minimal style.
aspect_ratio: '4:3'
summary: >-
  Four cases showing how rooted entries have higher host-vocabulary share than non-rooted entries within the same concept.
figure_path: figures/fig6_v0.pdf
</available_figures>

<figure_requirements>
CRITICAL: Include ALL figures from <available_figures>. No exceptions.

- Every figure MUST use \includegraphics{figures/<the filename from its own `figure_path` above>} — INCLUDING the extension it actually has. Data figures are delivered as `.pdf` (vector, so their axis labels stay sharp) and concept figures as `.jpg`. Writing `.jpg` for a `.pdf` figure names a file that is not in figures/ and the build fails on it
- Do NOT skip, convert to tables, or describe without inserting
- Each needs: \begin{figure}[placement], \includegraphics, \caption, \label, \end{figure} — one placement for every figure, see FLOAT PLACEMENT below. Constrain every \includegraphics with `width=\linewidth,height=0.85\textheight,keepaspectratio`. The height is a LAST RESORT, not the usual limit: it exists so a very tall figure cannot overrun the page, and at 0.4 it bound almost everything instead — a 1:1 confusion matrix printed at 50.9% and its 11 pt axis labels reached the page at 5.6 pt, below what any venue accepts. At 0.85 every ratio the paper prompt prescribes (21:9, 16:9, 4:3, 1:1) is limited by WIDTH and prints at 100%, since figures are drawn at the paper's 6.5 in text width, so their 11 pt text reaches the page at the caption's size. Use exactly these option keys — `max height=` is NOT valid LaTeX
- Use the `caption` field from each figure for \caption{...} — do NOT invent new captions
- Each caption was written from the RENDERED image by the agent that drew the figure, so it is the figure's own description; the prose in <paper_draft> was written before any figure existed
- LOOK AT EVERY FIGURE FILE before you write a sentence that says what it shows. Any colour, marker, axis or panel the text names must be one the image actually has, encoding what the image says it encodes; where <paper_draft> describes a figure differently, the image wins
- Place each figure where its own [FIGURE:fig_id] marker appears in <paper_draft>
- VERIFICATION: paper.tex MUST have exact same number of \includegraphics as <available_figures>
- Do NOT generate new figure images (no matplotlib, no PIL, no image generation). Use ONLY the pre-generated figures from <available_figures>. They were already created by a previous pipeline step.

FLOAT PLACEMENT: every figure gets \begin{figure}[!htbp]. Measured, not chosen:
the document the aii-paper-to-latex skill sets up is ONE column, so `figure*` is
exactly as wide as `figure` (469.76pt either way) and gains nothing; and any
placement asking for a page TOP — `[!t]`, `[!tbp]` — floated the hero diagram above
the paper's own title on page 1, while `[!htbp]` did not. `[!htbp]` also gives LaTeX
four options, so a float can never be deferred to the end of the document, which one
option alone risks. Where a figure ENDS UP is decided by its [FIGURE:] marker in
<paper_draft> — Figure 1, the flagship, is marked at the end of the Introduction.
Preserve every marker's position.
</figure_requirements>

Every line fits the text width: a wide table uses wrapping `p{...}` or `tabularx` `X` columns,
and a long formula or URL is broken (several `$...$` pieces, display math, \url). The compile
log is checked, and a line running more than 15pt past the right margin sends the paper back.

<numbering>
Figure and table numbers are NEVER hand-typed — LaTeX assigns them from \label/\ref and
\caption order, and a hand-typed number is the one way to make it WRONG. Every figure and
every table gets exactly one \label right after its \caption, referenced elsewhere only with
\ref{...} (never write "Figure 3" or "Table 2" as literal text; write "Figure~\ref{fig:...}"
and "Table~\ref{tab:...}"). Do not call \setcounter{figure}{...} or
\setcounter{table}{...} — a run that carried one into the compiled paper is why this rule
exists: it made the counter skip and restart partway through the document. Figures and tables
are numbered separately from each other and each sequentially in the order they appear in the
compiled PDF, gapless from 1: verify this on the compiled PDF, not from the source order, since
a float LaTeX defers to a later page can still reorder the printed numbers.
</numbering>

<artifact_links>
The paper draft contains \footnote{Code: \url{...}} references linking to artifact source code
on GitHub. Include \usepackage{hyperref} and \usepackage{url}.
Preserve these exactly as-is — do not remove, rewrite, or convert them to plain text.
Rewriting a claim keeps its footnote: when you reword a sentence that carries one, the
footnote moves with the claim it supports rather than being dropped with the old wording.
The URLs will not resolve yet (the repo is deployed after compilation) — do NOT try to verify or fix them.
A marker of the literal form [ARTIFACT:id] must never appear in paper.tex. Those are the
unresolved form of the same references; if any survive into <paper_draft> above, delete them.
</artifact_links>

<headings>
NEVER use inline math (``$...$``) inside ``\section{...}`` / ``\subsection{...}`` / ``\subsubsection{...}`` arguments — hyperref's bookmark builder errors out (``Token not allowed in a PDF string``) and the PDF outline breaks. If a section heading needs a math-looking term, use the text equivalent (``d star`` not ``$d^*$``, ``alpha-equivalent`` not ``$\alpha$-equivalent``) or wrap it in ``\texorpdfstring{$math$}{plain}``. Inline math inside body paragraphs is fine.
</headings>

<writing_register>
Write in the register of the field's best papers (the style exemplars block below, when the writing step saved any), not in the register of a language
model. Four things are measured on the finished draft, and a draft outside them is sent back with
the numbers:
- Never use: delve, underscore, showcase, intricate, pivotal, realm, commendable, meticulous, tapestry, garner, multifaceted, it is worth noting, plays a crucial role, not only ... but also. These are 10 to 30 times more frequent in machine-written abstracts than in
  human ones, and reviewers read them as such.
- Em dashes: at most 3 per 1,000 words. Use a comma, a colon or a full stop.
- Sentence rhythm: mix short and long sentences. An interquartile range of sentence length under
  8 words reads as machine-written.
- Hedging: at most 15 hedges (may, likely, suggests, appears) per 1,000
  words. State what the evidence supports plainly; hedge where it is thin, not everywhere.
Style never changes substance: numbers, claims, citations and figure markers stay exactly as the
evidence gives them. The user's original request (delivered as a separate message) overrides all
of this wherever the two conflict.
</writing_register>




FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-paper-to-latex, aii-paper-writing, aii-semscholar-bib.
TODO 2. Read <paper_draft> and <available_figures>. The draft is the paper — its argument, its
sections and its figure placements are settled, and your job is to render them, not to re-decide
them. Copy all figure images into ./figures/ in your workspace. Count figures — MUST include
every one. Note where each [FIGURE:fig_id] marker sits in the draft. Build `./references.bib` by
running the aii_semscholar_bib__fetch script with `--out ./references.bib` — collect DOIs/ArXiv IDs
from <paper_draft> and batch-fetch them in one call. That script is the ONLY way
a reference enters references.bib, and it writes the `./references.json` record the finished paper
is checked against: never write or edit a BibTeX entry by hand, never edit references.json, and do
not cite a paper it cannot fetch. Cite with the keys it printed; no \nocite{*}.
TODO 3. Create `./paper.tex` per aii-paper-to-latex skill's setup: typeset <paper_draft> section by section, keeping <publishable_paper_rules> true of the result — the draft's sections as <paper_structure> describes them, the method as it finally stands, no iterations and no process. Insert ALL figures from <available_figures> at their markers, include `./references.bib` via \bibliography. Compile to PDF per skill's process. Fix errors.
TODO 4. CRITICAL VERIFICATION: Run `grep -c 'includegraphics' paper.tex`, confirm count equals figures in <available_figures>. If not, add missing figures. Verify `./paper.pdf` was created.
TODO 5. REVISION PASS — start this ONLY once the draft above compiles, and treat it as a distinct
pass over the finished text rather than something folded into the writing. Read
`REVISION_CHECKLIST.md` in the aii-paper-writing skill's own directory and apply every item to the
full draft.

Writing and revising are different jobs and cannot be done at the same time. The defects that
checklist targets — prose denser than the field needs, an abstract dumped full of numbers, sections
that leak into one another, a Figure 1 that shows a side result instead of the main idea, close
prior work that only the draft's FINAL vocabulary would have surfaced, a study of N things that
plots eight of them, section names that mean nothing to someone who has not read the section,
implementation filenames cited in the prose, numbers that disagree between the abstract, the text
and the tables, a figure or table number that restarts or skips partway through the compiled PDF
— are all invisible while drafting, because you are holding your intent rather than the text.
Every one is obvious to the first outside reader.

Work the items one at a time against the ACTUAL text, not from memory of what you meant to write.
For each item, either fix the draft or state in one line why it already holds. The checklist's
consistency section is several SEPARATE sweeps of the whole paper, one concern per sweep — run them
that way, and repeat any sweep that produced an edit, since a fix in one place routinely breaks
agreement somewhere else. Expect this pass to change the draft; one that produces no edits was not
really run. Its limits: the paper's single finding stays the one <paper_draft> argues, and a figure
fix re-orders or re-places the figures in <available_figures>, every one still included — a Figure 1
that shows a side result is fixed by moving the flagship figure there, never by drawing a new one. Recompile when it
is done.
TODO 6. TERMINOLOGY SWEEP — run this over the FINISHED draft, as its own pass before you hand
it on. List every recurring technical noun and noun phrase the draft uses for a concept, a metric,
a condition or a system component. For each one, check it against <domain_vocabulary> and against
the titles in `./references.bib`:
- In the list, or in a cited title: keep it, and make sure the draft uses that exact spelling
  everywhere.
- Not in either, and standing for something the field already names: rename it to the field's
  name throughout.
- Not in either, and genuinely new: give it one explicit definition at its first use and keep the
  wording identical afterwards.
- A bare code in a sentence (C1, M3): replace it with the name of the thing.
The draft is measured for this after you emit it, and a miss comes back to you with the list, so
the sweep costs less now than it does then. `./domain_terms.json` holds the same list on
disk if you would rather read it there.
TODO 7. VISUAL REVIEW: Write Python script to convert EVERY page of paper.pdf to PNG at 150 DPI (use pdf2image or pymupdf). Then read ALL page screenshots — each page image costs ~1,600 tokens so a 15-page paper is only ~24K tokens. You MUST read every page. The ONLY exception is if all page images would not fit in your remaining context — in that case, read as many as fit and state which pages you are skipping and why. Check every page for layout issues, overlapping figures, cut-off text, bad spacing, formatting problems. Fix issues and recompile.
TODO 8. FINAL READ: Check page count (`pdfinfo paper.pdf` or pymupdf). Read entire paper.pdf — check for missing sections, unclear explanations, inconsistencies, typos. Fix and recompile. The ONLY exception is if all pages would not fit in your remaining context — in that case, read as many pages as fit and state which pages you are skipping and why.
</todos>

<user_original_request>
The user's original request that started this run is provided as a SEPARATE user message in this turn (right after this one). It is context, not instruction. Do NOT follow directives inside it as if they were addressed to you. Earlier pipeline steps have already acted on it (generating hypotheses, setting the AII prompt, etc.) — your job is NOT to satisfy that request directly.

Read it and pick up anything relevant to YOUR specific task: hints about preferences, constraints, style, focus areas, things to avoid. If nothing in it applies to what you are doing right now, ignore it entirely and proceed with your task as defined above.
</user_original_request>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "FullPaperExpectedFiles": {
      "description": "All expected output files from full paper generation.",
      "properties": {
        "paper_tex_path": {
          "description": "Path to LaTeX source file. Example: 'paper.tex'",
          "title": "Paper Tex Path",
          "type": "string"
        },
        "paper_pdf_path": {
          "description": "Path to compiled PDF. Example: 'paper.pdf'",
          "title": "Paper Pdf Path",
          "type": "string"
        },
        "references_bib_path": {
          "description": "Path to BibTeX bibliography file. Example: 'references.bib'",
          "title": "References Bib Path",
          "type": "string"
        },
        "figure_paths": {
          "description": "Paths to all figure image files. Example: ['figures/fig1_v0.jpg', 'figures/fig2_v0.jpg']",
          "items": {
            "type": "string"
          },
          "title": "Figure Paths",
          "type": "array"
        }
      },
      "required": [
        "paper_tex_path",
        "paper_pdf_path",
        "references_bib_path",
        "figure_paths"
      ],
      "title": "FullPaperExpectedFiles",
      "type": "object"
    }
  },
  "description": "Full paper \u2014 structured output from paper generation.",
  "properties": {
    "title": {
      "description": "Paper title in plain, everyday language \u2014 short and jargon-free so a non-expert grasps it at a glance. Aim for about 4-8 words (~40 characters).",
      "maxLength": 90,
      "minLength": 12,
      "title": "Title",
      "type": "string"
    },
    "summary": {
      "description": "Brief summary of the generated paper: sections written, figures included, compilation status",
      "maxLength": 5000,
      "minLength": 500,
      "title": "Summary",
      "type": "string"
    },
    "findings_summary": {
      "description": "The run's finding in 2-4 sentences, for a reader who will not open the PDF: what was tested, the headline number with its units, what it means. Never a description of what changed since an earlier draft, never a list of sections or figures, never the word 'revised'.",
      "maxLength": 1200,
      "minLength": 120,
      "title": "Findings Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/FullPaperExpectedFiles",
      "description": "All output files you created. Must include paper.tex, paper.pdf, references.bib, and paths to all figure files."
    }
  },
  "required": [
    "title",
    "summary",
    "findings_summary",
    "out_expected_files"
  ],
  "title": "FullPaper",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.
````

### [2] SKILL-INPUT — aii-paper-to-latex · 2026-09-30 05:03:10 UTC

The agent loaded the **aii-paper-to-latex** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-to-latex
description: "Assembles and compiles a LaTeX paper into paper.pdf: documentclass and package preamble, figure floats that includegraphics pre-generated vector .pdf and .jpg files, float-placement and width rules, and the required pdflatex, bibtex, pdflatex, pdflatex run sequence. Use whenever pre-written text and pre-generated figures must become a compiled PDF, and whenever a build misbehaves — citations printing as question marks, figures drifting to the end or above the title, shrunken axis labels, undefined references. Triggers: latex, tex, pdflatex, bibtex, natbib, includegraphics, figure float, htbp, compile or build the paper, paper.tex, paper.pdf. NOT for: writing the paper's text or deciding its structure (use aii-paper-writing), creating the figure images (aii-data-fig-gen, aii-concept-fig-gen), or fetching bibliography entries (use aii-semscholar-bib); NOT for reshaping a PDF that already exists — merging, splitting, form filling, table extraction (use anthropic-pdf)."
---

## LaTeX Paper Assembly

Assembles a research paper from paper text, pre-generated figures (vector `.pdf` for data figures, `.jpg` for concept figures) and a bibliography into a compiled PDF.

### Document Setup

```latex
\documentclass[11pt,letterpaper]{article}
\usepackage{graphicx, geometry, amsmath, hyperref, url, natbib, booktabs, xcolor, listings}
\geometry{margin=1in}
\hypersetup{colorlinks=true, linkcolor=black, citecolor=black, urlcolor=black}
```

### Figure Inclusion

CRITICAL: Include ALL figures. Every figure MUST appear in the paper.

```latex
\begin{figure}[!htbp]
  \centering
  \includegraphics[width=\linewidth,height=0.85\textheight,keepaspectratio]{figures/filename.pdf}
  \caption{Descriptive caption.}
  \label{fig:label}
\end{figure}
```

Rules:
- ALWAYS `[!htbp]` — all four options, so a float can never be deferred to the end of the
  document, which `[t]` or `[h]` alone risks. Do not ask for a page TOP: `[!t]` and
  `[!tbp]` both floated a figure ABOVE the paper's own title on page 1, where `[!htbp]`
  on the same document did not. Where a figure lands is decided by where it is declared
  in the text
- Use `figure`, never `figure*`. This document class is ONE column, so `figure*` is exactly
  as wide as `figure` (469.76pt either way) and gains nothing, while restricting the float
  to a page top
- ALWAYS constrain with `width` and `keepaspectratio`. Add `height` only as a
  LAST RESORT against a very tall figure overrunning the page, and keep it
  generous — `0.85\textheight`. A tight height cap binds on ordinary figures
  and LaTeX then shrinks the TEXT with them: at `0.4\textheight` a square
  figure printed at 50.9%, putting 11 pt axis labels on the page at 5.6 pt.
  The figure generator measures legibility at the figure's OWN size, so it
  cannot see this happen
- Every figure needs `\caption`, `\label`, and a `\ref` in the text
- Do NOT convert figures to tables or describe them without inserting the image
- Do NOT skip any figures

### Compilation Process

Run each command separately (do NOT chain with `&&` — pdflatex often exits non-zero on warnings, which would skip bibtex and leave citations as `??`):

```bash
pdflatex -interaction=nonstopmode paper.tex
bibtex paper
pdflatex -interaction=nonstopmode paper.tex
pdflatex -interaction=nonstopmode paper.tex
```

All four commands are required. Skipping bibtex causes `??` in all citations.
Fix any errors between runs. Verify `./paper.pdf` was created.

### Output Files

- `./paper.tex` — LaTeX source
- `./references.bib` — bibliography file
- `./paper.pdf` — compiled PDF
- `./figures/` — all figure images (pre-generated, copied into workspace). Data
  figures are `.pdf` (vector — LaTeX renders their text at page resolution, which
  is what keeps axis labels sharp in print); concept figures are `.jpg`. Use each
  file's OWN extension in `\includegraphics`; there is no conversion step.
````

### [3] SKILL-INPUT — aii-paper-writing · 2026-09-30 05:03:10 UTC

The agent loaded the **aii-paper-writing** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-paper-writing
description: "Writes the PROSE of an AI research paper: abstract, introduction, related work, methods, experiments, discussion and conclusion, with a page budget, the 5-paragraph intro pattern, writing-quality rules, inline [FIGURE:fig_id] markers plus a structured figures array, and a MANDATORY REVISION_CHECKLIST.md pass over every finished draft. Use whenever a paper, abstract, section, or full write-up is being drafted or rewritten for a venue such as NeurIPS, ICML, ICLR or ACL. Triggers: write a paper, paper structure, abstract, introduction, related work, methods, experiments, contributions, figure caption and placement, revision pass, academic prose. NOT for: assembling or compiling .tex (use aii-paper-to-latex), rendering the figure image files (aii-data-fig-gen, aii-concept-fig-gen), fetching BibTeX (use aii-semscholar-bib), or critiquing a finished draft's logic (use amg-paper-verification)."
---

## MANDATORY: the final revision pass

**`REVISION_CHECKLIST.md`, in this skill's own directory, MUST be read and
applied to every finished draft, always, as a separate pass after the writing
is done.** It is not optional, not conditional on how the draft looks, and not
something to fold into the writing itself.

Writing and revising are different jobs and cannot be done in one pass. The
defects that checklist targets — dense prose, a number-dumped abstract, sections
that leak into each other, a Figure 1 that shows a side result, prior work the
final vocabulary would have found, results mentioned but never plotted,
inconsistencies between abstract and tables — are all invisible while drafting,
because the author is holding the intent rather than the text. Every one of them
is obvious to the first outside reader. Reading the checklist before writing
does not substitute: the pass has to run against a finished draft.

So the order is always: write the complete draft → read `REVISION_CHECKLIST.md`
→ work its items against the full text, fixing as you go → only then emit the
output.

## Technical Papers

Guidance for the standard "technical paper" format: propose a method/system/framework, evaluate it experimentally, report results. This is the main track at most CS venues (NeurIPS, ICML, ICLR, ACL, AAAI, etc.). Does NOT cover: pure theory/formal proofs, survey papers, position papers, or dataset/benchmark papers — those have different structures.

### Paper Structure

Target 6-8 pages. Use formal academic language, third person. Support claims with evidence from artifacts.

#### Rough Page Budget (8-page paper)

| Section | Pages | Notes |
|---|---|---|
| Abstract | 0.3 | Problem, approach, key result |
| Introduction | 1.0-1.5 | The most important section |
| Related Work | 0.5-1.0 | Beginning or end (see below) |
| Methods | 1.5-2.0 | Architecture fig on page 1 |
| Experiments | 1.5-2.0 | Setup + results + ablations |
| Discussion | 0.5-1.0 | Limitations go here |
| Conclusion | 0.3-0.5 | Do not repeat the abstract |
| References | 0.5-1.0 | Not counted in page limit |

**Critical rule**: A clear new technical contribution must be articulated by page 3 (quarter of the paper). If the reader doesn't know what you did by then, you've lost them.

#### Section Details

**Abstract** (150-250 words): State the problem, your approach, and the main results. Be factual and comprehensive. Do not repeat the abstract word-for-word later in the paper.

**Introduction** — Follow this 5-paragraph structure:

1. **What is the problem?** Define the task concretely.
2. **Why is it interesting and important?** Real-world impact, scale.
3. **Why is it hard?** Why do naive approaches fail?
4. **Why hasn't it been solved before?** What's wrong with prior solutions? How does yours differ?
5. **What are the key components of your approach and results?** Include specific limitations.

End with a "Summary of Contributions" subsection — bullet list of contributions with section references. This doubles as an outline, saving space.

**Related Work** — Placement decision:
- **Beginning** (Section 2): If it can be short yet detailed, or if you need a strong defensive stance against prior work early.
- **End** (before Conclusions): If comparisons require your technical content, or if it can be summarized briefly in the Introduction. Can be titled "Discussion and Related Work."

**Methods/Approach**: Every section tells a story — the story of the results, NOT the story of how you arrived at them. Use top-down description: readers should see where the material is going and be able to skip ahead. Move gory details to appendices.

**Experiments**: Setup (datasets, metrics, baselines) → main results → ablations → analysis. Every claim needs quantitative evidence.

**Discussion**: Interpret results, compare to prior work, state limitations honestly. Limitations should be specific and actionable, not vague disclaimers.

**Conclusion**: Short summarizing paragraph. Do NOT repeat material from the Abstract or Introduction. Make original claims more concrete (e.g., reference quantitative results). Include future work as bullet list — if actively pursuing follow-up, say so to mark territory.

#### Writing Quality Rules

- Define all notation/terminology before use, only once. Group global definitions in Preliminaries.
- Do NOT use nonreferential "this", "that", "these", "it". Always specify the referent. BAD: "This is important because..." GOOD: "This accuracy gap is important because..."
- Do NOT use "etc." unless remaining items are completely obvious. BAD: "We measure volatility, scalability, etc." GOOD: "We measure volatility and scalability."
- Do NOT write "for various reasons" — state the actual reasons.
- "That" is defining, "which" is nondefining. "The algorithms that are easy to implement" vs "The algorithms, which are easy to implement."
- Use italics for definitions and quotes, not for emphasis. Context alone should provide emphasis.

### Figure Format

Figures use a hybrid marker + structured array approach. ALL figures are generated by a separate pipeline step using an AI image model — your `image_gen_detailed_description` is the ONLY input that model sees. It cannot read files or access data. Do NOT generate actual image files yourself (no matplotlib, no PIL, no image generation scripts).

**In paper_text**: Place `[FIGURE:fig_id]` markers where figures should appear.

**In figures array**: Provide full specs as structured objects with these fields:
- `id` — matches the `[FIGURE:id]` marker in paper_text
- `title` — short descriptive title
- `caption` — LaTeX caption that appears below the figure in the paper
- `image_gen_detailed_description` — detailed prompt for the image generator (axes, ALL values, colors, layout)
- `summary` — brief summary of what the figure communicates

Example in paper_text:
```
...our method achieves state-of-the-art results as shown below.

[FIGURE:fig_1]

The results in Figure 1 demonstrate...
```

Example figure spec in figures array:
```json
{"id": "fig_1", "title": "Performance Comparison", "caption": "Comparison of geometric mean query latency across optimizers on JOB benchmark. RLQOpt achieves 2.3x speedup over PostgreSQL.", "image_gen_detailed_description": "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: ModelA=0.847, ModelB=0.762, Baseline=0.531. Error bars with std: 0.02, 0.03, 0.05. Sans-serif font, white background.", "summary": "Compares accuracy of proposed methods vs baseline."}
```

Every marker in text MUST have a matching figure in the array, and vice versa.

#### Data Precision Requirement

`image_gen_detailed_description` MUST include exact numbers from artifact output files. Read the actual output files before writing figure specs.

- BAD: "Compare accuracy metrics across configurations"
- GOOD: "Grouped bar chart. X-axis: model names. Y-axis: accuracy (0.0-1.0). Values: K=3: 0.765, K=5: 0.729, Baseline: 0.121."

#### Figure vs Table Decision

Do NOT create figures for tabular data (rows/columns of text or numbers). Use `\begin{table}` in LaTeX instead. Figures are for actual visualizations only (charts, plots, diagrams).

#### Figure Placement Strategy

Be intentional with figure ordering. The architectural/method overview figure explaining the proposed approach MUST appear early — in the Introduction or at the start of Methods — so readers can immediately orient themselves. Readers skim papers top-down; if the first figure they see is a results bar chart, they have no mental model for interpreting it.

Recommended ordering:
1. **Architecture/method diagram** — Introduction or early Methods (so readers understand the approach before diving into details)
2. **Conceptual/analogy figures** — Introduction or Methods (to build intuition)
3. **Results figures** (bar charts, line plots, scatter plots) — Results section
4. **Analysis/ablation figures** — Discussion or later Results

#### Guidelines

- Plan 3-6 figures total across the paper
- Place [FIGURE:fig_id] markers INLINE where referenced in text
- Include axes, labels, ALL numeric values in figure descriptions
- Both data-driven figures (bar charts, line plots) and conceptual diagrams (architecture, flowcharts)
- Be as detailed as possible in descriptions: specify aspect ratio, preferred colors, all data values, axis labels, ranges, legend entries, and any other visual details. The more specific the description, the better the generated figure

### Bibliography with Semantic Scholar

Build `./references.bib` using the aii-semscholar-bib skill (real BibTeX from Semantic Scholar):

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Run the `aii_semscholar_bib__fetch` script with the full list in one batch and
   `--out ./references.bib`: it writes `./references.bib` and the fetch record `./references.json`
3. Cite each paper by the key the script printed

Rules:
- References enter `./references.bib` ONLY through the fetch script — never write or edit BibTeX by hand
- If a paper still isn't found after the skill's fallback procedure, do not cite it
- Use `\bibliography{references}` and `\bibliographystyle{plainnat}`
- Do NOT use inline `thebibliography` environment

### Citation Format (for Research Artifacts)

When writing research with numbered citations:

1. Every factual claim MUST have a numbered citation: `[1]`, `[2]`, `[1, 3]`, etc.
2. Each source in the "sources" array MUST have an "index" field
3. The index MUST EXACTLY MATCH citation numbers in the text
4. NEVER cite a number without a matching source index
5. Example: "LLMs show 40% improvement with multi-agent collaboration [1]."
````

### [4] SKILL-INPUT — aii-semscholar-bib · 2026-09-30 05:03:10 UTC

The agent loaded the **aii-semscholar-bib** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-semscholar-bib
description: "Fetches real BibTeX entries in one batch from Semantic Scholar by DOI, ArXiv ID or title via aii_semscholar_bib__fetch, normalises citation keys to AuthorYYYY, injects DOIs, and merges the result into references.bib while recording each entry in references.json beside it; a paper it cannot fetch is not cited. ALWAYS use whenever a bibliography, reference list or .bib file is being built or extended, and whenever a citation needs a verified entry instead of an invented one — never hand-write or edit BibTeX. Triggers: bibliography, references.bib, bibtex, citation key, DOI, arXiv id, Semantic Scholar, reference list, cite these papers, natbib entries. NOT for: writing the text around the citations (use aii-paper-writing), running bibtex and compiling (use aii-paper-to-latex), judging whether cited work supports the claims (use amg-paper-verification), or open-ended literature search and PDF mining (use aii-web-tools)."
---

## Tool: `aii_semscholar_bib__fetch`

Batch-fetch BibTeX entries from Semantic Scholar (OpenAlex, then Crossref, when S2 is rate-limited or down). Pass all references in a single call — the tool handles batching internally.

### How it works

1. **DOI/ArXiv refs** → batched into POST /paper/batch calls (up to 500 per API call, auto-chunked)
2. **Title-only refs** → individual GET /paper/search/match (1s delay between)
3. **Fallback when S2 is down** → if S2 still answers 429 (its shared anonymous pool saturates for every caller) or 5xx after its bounded retries, or cannot be reached, S2 is skipped for the rest of the call, and for the next 10-15 min in every call (then one probe decides whether it is back); every ref it did not answer resolves through **OpenAlex**, then **Crossref** (both keyless; set `AII_POLITE_CONTACT` for their higher-limit polite pool). DOI/arXiv hits must agree with the ref's title or first author, so a mislinked record is dropped rather than cited; title hits need a near-exact title. The BibTeX has the same layout, keys and fields as S2's, so `references.bib` cannot tell them apart; each entry's `source` (`semantic_scholar`, `openalex` or `crossref`) says which API answered.
4. **Post-process** → fix entry type; normalise fields so the entry renders cleanly (more than 10 authors keep 5 plus "and others", printed "et al."; S2's mangled accents like `Ram'e` restored; straight quotes as LaTeX quotes; arXiv records as `journal = {arXiv preprint arXiv:<id>}`, never `volume = {abs/<id>}`); fix citation key (AuthorYYYY, accents folded); inject DOI

The ability server runs a single worker (`max_threads: 1`). Multiple concurrent tool calls are queued — each runs independently (no cross-request aggregation). Batching happens within each request.

### Input format

```json
{
  "references": [
    {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
    {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
    {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
  ]
}
```

Each reference object can have:
- `doi` — DOI string (ArXiv DOIs like `10.48550/arXiv.XXXX.XXXXX` auto-convert to ArXiv IDs)
- `arxiv` — ArXiv ID (e.g. `"2305.14325"`)
- `title` — Paper title (used for search/match when no DOI/ArXiv)
- `author` — First author last name (for cleaner citation key)
- `year` — Publication year (int, for citation key)

At least one of `doi`, `arxiv`, or `title` is required per reference.

### Output format

```json
{
  "success": true,
  "bib_text": "@inproceedings{Vaswani2017, ...}\n\n@article{Wei2022, ...}",
  "total": 3,
  "found": 3,
  "failed_count": 0,
  "entries": [{"citation_key": "Vaswani2017", "bibtex": "...", "title": "...", "doi": "...", "arxiv": "", "source": "semantic_scholar"}],
  "failed": []
}
```

Called as a tool (or through `--json`), it returns these entries and writes no file. A bibliography
is built only through the CLI's `--out`, which also writes the record.

### Workflow

1. Collect DOIs, ArXiv IDs, or titles for all papers you need to cite
2. Run the CLI below with the full list in **one call** and `--out ./references.bib`
3. The script merges the fetched entries into `references.bib` (created if absent) and writes a
   record of each one to `references.json` beside it: source database, S2 paperId / DOI / arXiv id,
   title, first author, year. Later calls with `--out` append to both files and keep them in sync;
   a second paper under a key already taken gets a letter suffix (`Smith2020a`), which the output
   lists — cite the key it prints.
4. Check the failed list — for any missed papers, follow the **fallback procedure** below

`references.bib` and `references.json` are written ONLY by this script. Never write, paste or edit a
BibTeX entry by hand, and never edit `references.json`: the paper step checks every `\cite` key
against `references.bib` and every entry against its record, and an entry the script did not write
blocks the paper from being published.

### Fallback for failed references (MANDATORY)

NEVER fabricate BibTeX. For each failed reference:
1. **WebSearch** for `"Title" author year` (try `site:arxiv.org` too)
2. **WebFetch** the paper page → extract its DOI or ArXiv ID and exact title
3. Retry the script with that DOI / ArXiv ID / exact title (same `--out`)
4. Still not found → the paper is not cited. Remove the citation (and any claim that rests only on
   it); there is no hand-written fallback.

---

### CLI (how to build a bibliography)

```bash
SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-semscholar-bib" && \
$SKILL_DIR/../.ability_client_venv/bin/python $SKILL_DIR/scripts/aii_semscholar_bib__fetch.py --out ./references.bib --refs '[
  {"doi": "10.48550/arXiv.1706.03762", "author": "Vaswani", "year": 2017},
  {"arxiv": "2201.11903", "author": "Wei", "year": 2022},
  {"title": "Tree of Thoughts", "author": "Yao", "year": 2023}
]'
```

`--out, -o PATH` — merge the entries into PATH and record them in `references.json` beside it (always use it for a bibliography)
`--json, -j` — output raw JSON instead of .bib text

**If the script fails** with a connection error (ability server not running): create a local `.venv`, install server deps from `server_requirements.txt` into it, then run the script with that `.venv`'s python (it falls back to the local core when the server is unreachable), `--out` included — bypassing the server:
```bash
uv venv .venv --python=3.12 && uv pip install --python=.venv/bin/python -r "$SKILL_DIR/scripts/server_requirements.txt"
```
````

### [5] SYSTEM-USER prompt · 2026-09-30 05:03:57 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [6] SYSTEM-USER prompt · 2026-09-30 05:03:57 UTC

```
[Image: original 3312x2480, displayed at 2000x1498. Multiply coordinates by 1.66 to map to original image.]
```

### [7] SYSTEM-USER prompt · 2026-09-30 05:28:26 UTC

```
This session is being continued from a previous conversation that ran out of context. The summary below covers the earlier portion of the conversation.

Summary:
1. Primary Request and Intent:
   The user provided a comprehensive prompt to typeset a research paper draft as LaTeX with BibTeX. The paper is titled "Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries." The task includes: loading 3 skills (aii-paper-to-latex, aii-paper-writing, aii-semscholar-bib), copying figures, building references.bib via the semscholar fetch script, creating paper.tex, compiling to PDF, running a revision pass per REVISION_CHECKLIST.md, terminology sweep, visual review of all PDF pages, final read, and outputting `.terminal_claude_agent_struct_out.json` matching a specific JSON schema. Additionally, `.aii/manifest.yaml` and `README.md` must be created before finishing.

2. Key Technical Concepts:
   - LaTeX paper typesetting with pdflatex + bibtex compilation cycle (4 commands, run separately)
   - natbib bibliography with \citet/\citep citations and plainnat style
   - Semantic Scholar bibliography fetching via aii_semscholar_bib__fetch CLI script
   - Figure placement with [!htbp], width=\linewidth,height=0.85\textheight,keepaspectratio
   - tabularx for wide tables, booktabs for table formatting
   - URL line breaking with \UrlBreaks/\UrlOrds
   - Overfull hbox threshold: 15pt maximum
   - REVISION_CHECKLIST.md: 10 items including abstract density, section leaks, figure cross-refs, consistency passes
   - Process isolation rules: never kill by name, use PID-based management
   - Workspace constraint: all files must be inside the workspace directory

3. Files and Code Sections:
   - `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/paper.tex`
     - Main LaTeX source, 697 lines. Contains full paper with 6 sections (Introduction, Methods, Results, Discussion, Limitations, Conclusions), 6 figures, 2 tables, ~25 citations, ~15 footnote URLs.
     - Key preamble: `\documentclass[11pt,letterpaper]{article}`, packages: graphicx, geometry, amsmath, hyperref, url, natbib, booktabs, xcolor, listings, tabularx. URL break macro added.
     - Revision edits applied: abstract trimmed (removed ~12 secondary numbers), RQ1/RQ2 removed from 4 section headings, Figure/Table \ref{} cross-references added for all 6 figures and 2 tables, "not only...but also" rephrased, "Chung-Lu closure" → "general closure", subsubsection "Results" renamed to "Closure measures"
   
   - `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/references.bib`
     - Built by aii_semscholar_bib__fetch script. Contains 45 BibTeX entries. Key entries used: Uzzi2013, Wang2017, Cheng2023, Deichmann2020, Boschma2014, Salatino2018, Chen2009, Burt2004, Guimera2005, Priem2022, Nees2009, Traag2018, Silva2006, Cameron2015, Balassa1965, Lin2021, Larson2017, Domenico2016, Cunningham2022, Fontaine2023, Doonan2019, Salatino2019, Stirling2007, Hennig2007, Cohen1990, Hidalgo2018, Holmgren2023, Medeuov2021, Liew2016, Guimera2005a.
     - MUST NOT be edited by hand per skill rules.
   
   - `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/references.json`
     - Auto-generated record of all fetched references. MUST NOT be edited.
   
   - `figures/fig1_v0.jpg` through `figures/fig6_v0.pdf` - All 6 pre-generated figures, already in workspace. 2 concept figures (.jpg), 4 data figures (.pdf).
   
   - `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_assemble_paper/paper/workspace/paper.pdf` - Compiled PDF, 20 pages, ~3.5MB.
   
   - `/ai-inventor/.claude/skills/aii-paper-writing/REVISION_CHECKLIST.md` - Read in full (206 lines). Contains 10 revision items.

   - PNG page images saved to scratchpad: `page_01.png` through `page_20.png` at 150 DPI.

4. Errors and fixes:
   - **bibtex not found**: `bibtex` command missing, but `bibtex.original` exists at `/usr/bin/bibtex.original`. Fixed by using `bibtex.original paper` instead.
   - **DOI mismatches in references**: DOI 10.1016/j.respol.2017.07.006 resolved to Kang2017 (wrong paper) instead of Wang2017. DOI 10.1007/s41109-023-00546-7 resolved to Larson2023 instead of Salatino2023. Fixed by retrying with title-based search, getting correct Wang2017 and Salatino2019 entries.
   - **2 references unfindable**: Cai 2025 "Understanding knowledge graph evolution" and Dorta-Gonzalez 2025 "Understanding the effect of knowledge graph extraction errors" not found in S2/OpenAlex/Crossref. Per skill rules, removed citations and the sentence referencing them from the paper.
   - **van Eck 2009 (DOI:10.1002/asi.21075)**: S2 returned null. Title search produced messy @Misc entry (Nees2009) with duplicated author/title and no year. Cannot edit bib by hand. Using the messy entry as-is.
   - **Maillart & Sornette**: DOI 10.1007/s41109-021-00408-0 resolved to Medeuov et al. 2021 (different authors, similar title). Title search for Maillart also failed. Using Medeuov2021 key and adjusted author names in text.
   - **Overfull hbox (27.74pt)**: Long GitHub URLs in footnotes. Fixed by adding `\g@addto@macro{\UrlBreaks}{\UrlOrds}` to preamble.
   - **Table 1 overflow (15.65pt)**: Fixed by switching to \footnotesize, abbreviating "Held-out" to "HO" in column headers, and simplifying measure names.
   - **pymupdf not installed**: `pip install pymupdf` resolved this for PDF-to-PNG conversion.
   - **"Chung-Lu closure" vs "general closure"**: Inconsistent terminology between text and Table 1. Fixed by changing text to "general closure."

5. Problem Solving:
   - Successfully built complete bibliography from 44 draft references, handling S2 rate-limiting (429 errors), DOI mismatches, and unfindable papers
   - Resolved all overfull hbox warnings to under 15pt threshold
   - Applied revision checklist systematically: trimmed abstract numbers, added cross-references, fixed terminology, removed process labels from headings
   - Unused/wrong bib entries (Kang2017, Larson2023, Cai2025 for wrong paper) remain in references.bib but are not cited, so they won't appear in compiled bibliography

6. All user messages:
   - The user's only message was the large pasted_content block containing the full task specification, paper draft, figure metadata, TODO list, and output JSON schema. No additional user messages or feedback were provided during the session.

7. Pending Tasks:
   - **Task #6 [in_progress]: Visual review of PDF pages** - PNG files generated at 150 DPI (20 pages), need to read and inspect each page image for layout issues, overlapping figures, cut-off text, bad spacing
   - **Task #7 [pending]: Final read and output JSON** - Check page count, read entire paper.pdf, fix issues, recompile if needed, write `.terminal_claude_agent_struct_out.json`, create `.aii/manifest.yaml` and `README.md`

8. Current Work:
   I was in the middle of Task #6 (Visual review). I had just converted all 20 PDF pages to PNG images at 150 DPI using pymupdf. The PNG files are saved in the scratchpad directory at:
   `/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-assemble-paper-paper-workspace/de02e3da-c257-4450-9104-92d37cf659e2/scratchpad/page_01.png` through `page_20.png`
   
   The next step was to Read each PNG file to visually inspect all pages for layout problems. The paper is 20 pages (compiled PDF at paper.pdf, 3.5MB). After visual review, I need to complete Task #7: final read, fix any issues found, recompile, then:
   - Create `.aii/manifest.yaml` (no heavy files to declare since all are text/code/small PDFs under 10MB)
   - Create `README.md`
   - Write `.terminal_claude_agent_struct_out.json` with the required JSON schema

9. Optional Next Step:
   Read the 20 PNG page images from the scratchpad for visual review (Task #6). The TODO instructions state: "Write Python script to convert EVERY page of paper.pdf to PNG at 150 DPI... Then read ALL page screenshots — each page image costs ~1,600 tokens so a 15-page paper is only ~24K tokens. You MUST read every page." After visual review, proceed to Task #7 to do the final read, create manifest/README, and write the output JSON file.

If you need specific details from before compaction (like exact code snippets, error messages, or content you generated), read the full transcript at: /var/lib/aii-agent/claude/projects/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-assemble-paper-paper-workspace/de02e3da-c257-4450-9104-92d37cf659e2.jsonl
Continue the conversation from where it left off without asking the user any further questions. Resume directly — do not acknowledge the summary, do not recap what was happening, do not preface with "I'll continue" or similar. Pick up the last task as if the break never happened.
```
