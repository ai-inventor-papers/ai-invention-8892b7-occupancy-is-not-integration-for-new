# gen_paper_site — report_results

> Phase: `gen_paper_repo` · `gen_full_paper`
> Run: `run_F1tk5OGtH84L-phase-gen_paper_repo-mod-gen_full_paper` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
>
> Full, verbatim record of every prompt the AI Inventor pipeline gave this agent — system-user, human-user and skill-input — in the order they landed. Nothing truncated.

## Task: `gen_paper_site` (terminal_claude_agent)

### [1] SYSTEM-USER prompt · 2026-09-30 07:03:58 UTC

````
<design_philosophy>
You are building ONE web page whose only job is to let a reader understand a research paper faster
than they could by opening the PDF. Every decision on the page is judged against that.

WHAT "FASTER" MEANS HERE
- A reader who leaves after thirty seconds still knows the finding and the number behind it.
- A reader who stays five minutes has the method, the figures and the caveats, in that order.
- Nothing on the page is there because a layout had a slot for it.

ACCURACY IS THE HARD CONSTRAINT
Every number, name and claim comes from the paper as written — you read them out of the LaTeX
source, the only source this page has. You never change a number's precision, never restate a
comparison the paper did not make, and never invent a headline figure to fill a card. A page that
looks excellent and misreports one result is worse than no page, because the PDF beside it says
something else and a reader will find that out.

CRAFT, AND THE LOOK TO AVOID
The failure mode for a generated page is a look every reader now recognises on sight: a
purple-to-blue gradient banner, three identical cards with emoji headings, and body text set in
one weight at one size. Avoid all of it.
- Type carries the design. One system font stack, a real scale with visible jumps between levels
  rather than a creep of similar sizes, long-form text around 17-19px with a measure of 65-75
  characters and generous line height. Weight and size do the emphasis; colour rarely does.
- Colour is restrained. A light, near-white ground, one dark ink for text, one accent used for
  links and the current-section marker and almost nothing else. No gradients as decoration.
- Space does the work that borders and boxes would do badly. Sections separated by real vertical
  rhythm, cards defined by alignment and a single hairline rather than by shadow stacks.
- Structure over ornament: no emoji as section markers, no icon fonts, no badge clutter, no
  animated counters.
- Motion is a courtesy. A short transition on a lightbox or a hover state is welcome; anything
  that moves on scroll, autoplays, or delays the reader is not — and all of it stops under
  prefers-reduced-motion.
- Every interactive element works with a keyboard and says what it is to a screen reader. That is
  part of the craft, not a checklist bolted on at the end.

FINISH IT
The page is done when you have opened it in a browser, read it at a phone width and a desktop
width, tabbed through every control, and found nothing to fix. Not before.
</design_philosophy>

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
Your workspace: `/ai-inventor/aii_data/runs/run_F1tk5OGtH84L/4_gen_paper_repo/_4_assemble_paper/paper`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_F1tk5OGtH84L/4_gen_paper_repo/_4_assemble_paper/paper/`:
GOOD: `/ai-inventor/aii_data/runs/run_F1tk5OGtH84L/4_gen_paper_repo/_4_assemble_paper/paper/file.py`, `/ai-inventor/aii_data/runs/run_F1tk5OGtH84L/4_gen_paper_repo/_4_assemble_paper/paper/results/out.json`
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
Build the paper's public web page: ONE self-contained `index.html` that lets a reader grasp
this paper faster than opening the PDF would. It is published as this run's GitHub Pages site, so
it is the first thing anyone sees.
</task>

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<what_is_already_here>
Your workspace is the finished paper folder. It already holds everything the page is made of, and
you must not change any of it — you are adding one file, not revising the paper.

- `paper.tex` — the FINAL paper, as it was actually written. It is the ONLY source for
  every claim, name and NUMBER that goes on the page. Earlier versions of this paper, the research
  report and any page written in an earlier session are not sources: where your memory of one
  differs from `paper.tex`, the paper wins.
- `paper.pdf` — the compiled paper. The page must NOT link to it by this local name:
  the PDF is published on the code branch and the page on a different one. Link to it at the
  full URL below instead.
- `references.bib` — the bibliography, when the paper has one.
- `figures/` — every figure the paper uses, flattened into one folder.
- `workspace/` — the scratch folder the LaTeX task worked in. Ignore it.
</what_is_already_here>

<available_figures>
Each line gives the path the PAGE must use, then the figure's title and caption. It is the same
path the file has on disk here: the publish step copies the page and its figures into one folder,
so what works in this workspace is what works on the live site.

- figures/fig1_v0.jpg — "Study design and analysis pipeline" (caption: "Overview of the study design. (a) Data: an outcome-blind arXiv concept pool of 426 emerging scientific concepts, split into a screen fold (247) and a held-out fold (119), and an independent MeSH biomedical check population of 191 concepts. Both are drawn from 462,812 OpenAlex works. (b) Co-word network: yearly co-word snapshots (25 snapshots, $\sim$27k nodes, $\sim$84k edges) with Leiden communities; the schematic shows three colour-coded communities. (c) RQ1, emergence precursors: a matched event study compares closure measures in the pre-onset window (shaded) between concepts showing sustained uptake (blue, rising after onset) and controls (grey, flat). (d) RQ2, host-entry grafting: a concept enters a non-origin host subfield (light blue $\rightarrow$ light green region). Its partner terms are either host-native (dark green) or from the origin vocabulary (light blue). The host-vocabulary share (orange) is the exposure in a pre-registered PPML regression with concept-clustered standard errors predicting 5-year newcomer uptake. The timelines and bars in (c) and (d) are schematic and carry no data values.")
- figures/fig2_v0.jpg — "Co-word network snapshot" (caption: "Schematic co-word network snapshot (2012, three-year window). Nodes are concept-keyword terms and grey edges are association-strength weighted co-occurrences; node fill colour (blue, green, orange, purple, red, teal) marks Leiden community membership, and larger circles are high-degree hub terms. Background terms (plain nodes) form dense communities that are joined by only a few inter-community edges. Pool concepts (bold black rings) sit on the periphery of communities, mostly in the gaps between two of them, where they act as bridge or connector nodes; three are labelled as examples (\emph{wireless backhaul}, \emph{EPR steering}, \emph{holographic QCD}). The full network comprises approximately 27,000 nodes and 84,000 edges; the panel is an illustrative rendering of its high-degree core for readability.")
- figures/fig3_v0.png [render from fig3_v0.pdf first] — "Pre-emergence closure by measure type" (caption: "Pre-emergence closure on the held-out fold, by measure type. Each row shows the standardised mean difference (S) between concepts that later show sustained uptake and matched controls. Points are estimates and horizontal bars are 95\% bootstrap confidence intervals. The dashed vertical line marks no effect (S = 0), and Holm-corrected p-values are listed to the right of the first three rows. Only persistent-neighbour closure (blue) survives Holm correction (S = -1.07, 95\% CI [-1.86, -0.29], Holm p = 0.015). General closure (Holm p = 0.147) and turnover-residualised closure (Holm p = 0.635) are shown in grey: they do not survive confirmation, and their intervals cross zero. Burt constraint (orange) is positive (S = 0.11, 95\% CI [0.02, 0.19]), which indicates that emerging concepts sit in more constrained, not more brokered, ego networks.")
- figures/fig4_v0.png [render from fig4_v0.pdf first] — "Host-vocabulary effect across folds" (caption: "Host-vocabulary effect on five-year newcomer uptake across folds and specifications. Each row gives the PPML incidence-rate ratio (IRR) per one standard deviation of host-vocabulary share, on a log axis; horizontal bars are 95\% concept-clustered confidence intervals, and the dashed vertical line marks IRR $=1$ (no effect). Filled circles are the co-primary specification (concept, entry-year and host fixed effects) and open circles the primary specification with concept$\times$year and host$\times$year fixed effects. Blue marks the OpenAlex screen and sealed held-out folds, green the independent MeSH replication, and the amber diamond the inverse-variance weighted (IVW) pooled co-primary estimate. The co-primary effect is significant on all three folds (screen IRR 1.30 [1.16, 1.45], held-out 1.19 [1.06, 1.33], MeSH 1.23 [1.12, 1.36]), and the pooled estimate is 1.26 [1.17, 1.36]. The primary specification is inconclusive on the held-out fold (IRR 0.98 [0.70, 1.37], 30 clusters, $p=0.91$) but significant on MeSH (IRR 1.32 [1.10, 1.60]). Grey diamonds are the co-transfer regressor from the co-primary models. Its intervals include 1 on every fold ($p=0.48$, $0.60$ and $0.053$). The right-hand columns list each estimate with its 95\% CI and $p$-value.")
- figures/fig5_v0.png [render from fig5_v0.pdf first] — "Extensive and intensive margin decomposition" (caption: "Decomposition of the host-vocabulary effect into extensive and intensive margins across the screen, held-out and MeSH folds. Blue circles show per-fold estimates, vermillion diamonds the inverse-variance-weighted (IVW) pooled estimate, and horizontal bars 95\% confidence intervals. (a) Extensive margin: linear-probability-model effect of a one-standard-deviation increase in host-vocabulary share on the probability of any newcomer uptake, in percentage points per SD (dashed line: no effect). The pooled effect is 6.43 pp (95\% CI 4.76 to 8.11). (b) Intensive margin: PPML incidence-rate ratio per SD conditional on uptake, on a log axis (dashed line: IRR $=1$). The pooled IRR is 1.183 (95\% CI 1.104 to 1.267). All three folds are positive on both margins, and every fold interval excludes the null. (c) Share of the total effect: the extensive margin accounts for 38\% (95\% CI 21\% to 55\%, black whisker) and the intensive margin for the remaining 62\%.")
- figures/fig6_v0.png [render from fig6_v0.pdf first] — "Four representative cases" (caption: "Four representative cases of the host-vocabulary gradient. Each panel shows one concept, and each horizontal bar is one of its host entries in the co-primary sample, labelled by host subfield and entry year and sorted by host-vocabulary share (x-axis, fraction). Green bars are rooted entries and grey bars are non-rooted entries. The dashed line marks the mean share of the non-rooted entries, and rooted bars are annotated with their share and number of newcomer papers. (a) Wireless backhaul (broad, CS): 14 entries, one rooted (Aerospace Engineering 2008, share 0.084, 6 newcomers) against a non-rooted mean of 0.021. (b) Einstein--Podolsky--Rosen (EPR) steering (broad, Physics): 7 entries, one rooted (Artificial Intelligence 2011, 0.142, 37 newcomers; co-transfer 0) against a non-rooted mean of 0.027. (c) Locally repairable code (localised, CS): a single co-primary entry, rooted (0.056, 3 newcomers), so there is no within-concept contrast. (d) Holographic QCD (localised, Physics): 5 entries, none rooted (mean 0.041; three have co-transfer 1.0), including an AMO Physics entry at 0.132 that did not take root. In (a) and (b), the rooted entry has a higher host-vocabulary share than every non-rooted entry of the same concept. The panels are descriptive, so no intervals are drawn.")
</available_figures>

<figure_requirements>
- Reference every figure as `figures/` plus its filename, exactly as listed above.
  The publish step copies the page and its figures into one folder together, so that relative
  path is what resolves on the live site; anything else breaks once published.
- A browser cannot draw a PDF in an image element. Data figures are delivered as vector PDF for
  LaTeX's benefit, so for each one check whether a PNG of the same name already sits in
  `figures/`; if it does not, render one there at about 200 DPI with pdftoppm or
  pymupdf before referencing it. Renderable formats: .avif, .gif, .jpeg, .jpg, .png, .svg, .webp.
- Write those PNG files into `figures/` and nowhere else — that folder is published, a
  new folder of your own is not.
- Use each figure's own caption. It was written from the rendered image by the agent that drew
  the figure. Do not invent new ones, and do not describe a figure you did not place on the page.
- Look at every figure before you place it. A figure whose axis labels are unreadable at the size
  you give it is worse than no figure. Any colour, marker, axis or panel the page names must be
  one the image actually has, encoding what the image says it encodes.
</figure_requirements>

<page_structure>
In this order, top to bottom:

1. HERO — the paper's title, the author line as the paper gives it, and a one-paragraph TL;DR in
   plain language: what was asked, what was found, and the single number that carries the finding.
   Not the abstract, and not a rewrite of it. Below it, every link the links section below
   lists, each at the exact URL given there.
2. CONTRIBUTIONS — the paper's actual contributions as three to five scannable cards, each a short
   heading plus one or two sentences. If the paper claims four things, show four cards, not five.
3. METHOD — a walkthrough a technically literate non-specialist can follow: what goes in, what
   happens to it, what comes out, and why the design is the way it is. Lead with the paper's own
   method figure when it has one.
4. RESULTS — the paper's real headline numbers, read out of `paper.tex`, each next to what it was measured on and what it is being compared against.
   A number that is not in the paper does not go on the page, and neither does a comparison the
   paper did not make. If a slot has no number, drop the slot.
5. FIGURE GALLERY — every figure, each with its caption, click-to-enlarge into a lightbox that
   closes on Escape, on a click outside, and on a visible close control.
6. LIMITATIONS — what the paper says it does not show. Verbatim in substance; do not soften it.
7. FOOTER — every link from the links section again, and the citation if the paper carries one.

A sticky section navigation runs alongside all of it and marks where the reader currently is.
Do NOT write its highlighting yourself: hand-written ones kept a stale section lit after a jump
back to the top, or never reached the short last sections. Instead give the nav element a
`data-scrollspy` attribute, make each of its links `href="#<id of that section>"`, style the
current link through `a.active` (it also gets `aria-current`), and paste this script VERBATIM
into the page's script element at the end of the body. It lights the section in view, the last one once the page is
scrolled to its end, and nothing while the reader is above the first linked section:

```js
/* aii-scroll-spy v1: paste verbatim */
(function () {
  var links = [], targets = [];
  document.querySelectorAll('[data-scrollspy] a[href^="#"]').forEach(function (a) {
    var el = document.getElementById(a.getAttribute('href').slice(1));
    if (el) { links.push(a); targets.push(el); }
  });
  if (!links.length) return;
  var queued = false;
  function current() {
    var view = window.innerHeight;
    var doc = document.documentElement;
    var atEnd = window.scrollY > 0 && view + window.scrollY >= doc.scrollHeight - 2;
    var line = atEnd ? view - 1 : Math.min(view * 0.3, 200);
    var best = null, bestTop = -Infinity;
    targets.forEach(function (el) {
      var top = el.getBoundingClientRect().top;
      if (top <= line && top > bestTop) { best = el; bestTop = top; }
    });
    return best;
  }
  function update() {
    queued = false;
    var el = current();
    links.forEach(function (a, i) {
      var on = targets[i] === el;
      a.classList.toggle('active', on);
      if (on) a.setAttribute('aria-current', 'location');
      else a.removeAttribute('aria-current');
    });
  }
  function schedule() {
    if (!queued) { queued = true; window.requestAnimationFrame(update); }
  }
  window.addEventListener('scroll', schedule, { passive: true });
  window.addEventListener('resize', schedule);
  window.addEventListener('load', schedule);
  if (window.ResizeObserver) new ResizeObserver(schedule).observe(document.body);
  update();
})();
```
</page_structure>

<technical_requirements>
- ONE file. All CSS in a style element, all JavaScript in a script element, both inline in
  `index.html`. No build step, no bundler, no framework, no external script, stylesheet, web
  font or analytics — nothing fetched at load time. The page must render with the network off,
  and the only local files it may point at are the figures listed above; the PDF is linked at
  its full URL, never by its local name.
- A complete HTML document: the file opens with exactly this markup, then the title and the
  style element, and closes head before the body. The viewport tag is what makes a phone lay the
  page out at its own width; without it the page renders 980px wide and shrinks to tiny text.
```html
<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
```
- System font stack only, since no font may be downloaded.
- Light theme. Responsive from a 360px phone to a wide desktop, with no horizontal page scroll;
  wide content scrolls inside its own container.
- Honour prefers-reduced-motion: under it, transitions and any scroll-driven effect stop.
- Keyboard-navigable: every control reachable by Tab in a sensible order, a visible focus ring,
  the lightbox trapping focus while open and returning it to the thumbnail on close, and a skip
  link to the main content.
- Semantic HTML: one top-level heading, headings that descend without skipping, landmark elements,
  and alt text on every image that says what the figure shows rather than repeating its number.
- No emoji anywhere. No purple-to-blue gradients. No decorative icon fonts.
- Keep the whole file comfortably under a megabyte.
</technical_requirements>

<writing_register>
Write in the register of the field's best papers (the paper this page presents, which was written to them), not in the register of a language
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

<links>
Use these URLs VERBATIM wherever the page links to the paper, the report or the code. Do not
shorten them, do not turn any of them into a relative path, and do not compose one of your own.

- The paper PDF, labelled "Read the paper (PDF)": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/paper.pdf
- The code repository, labelled "Code repository": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L
- The full research report — every experiment, every table and every dead end: https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/report.pdf
  Label this one "Read the full research report" and place it BESIDE the paper link, never in place of it.
- The executive summary, the short read of the run, labelled "Read the executive summary": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/exec_summary.pdf
  Place it right beside "Read the full research report".
- The report of each research round, as ONE compact line introduced by "Round reports:" under the document links, each round labelled as given:
  - "Round 1": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/round-1/report.pdf
  - "Round 2": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/round-2/report.pdf
  - "Round 3": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/round-3/report.pdf
  - "Round 4": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/round-4/report.pdf
  - "Round 5": https://cdn.jsdelivr.net/gh/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new@fork/run_F1tk5OGtH84L/round-5/report.pdf

Each carries the branch this run publishes to. A link without it opens a DIFFERENT run's work —
it resolves and looks correct, which is why it must be copied rather than derived. They begin
resolving only after this run finishes publishing, so do NOT try to open or verify them.

`paper.tex` carries a third kind of link, per claim rather than per paper: where it attaches a
\footnote{Code: \url{...}} to a sentence, that URL points at the exact code behind THAT claim.
Carry each one onto the page as an inline link on the corresponding sentence, using the URL
verbatim, the same way you use the ones above. Do not collapse them into the repository link.

Every artifact this run produced is published with its code. Link EACH of these, verbatim, from the part of the page that discusses that artifact, labelled as given or as the page's own name for it; one the page does not otherwise discuss goes in a short code list above the footer:
- "Code: New science concepts and their papers": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-1/dataset-1
- "Code: New MeSH medical terms as a held-out check set": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-1/dataset-3
- "Code: Labelled science phrases and new-term pool": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-1/dataset-4
- "Code: Prior art and plan for concept-spread study": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-1/research-1
- "Code: All concept papers downloaded, with field labels": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-2/dataset-5
- "Code: Cleaning and grounding emerging science concepts": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-2/experiment-1
- "Code: Do concept citation chains survive in new fields?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-2/experiment-2
- "Code: How new science concepts grow in a knowledge network": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-2/experiment-3
- "Code: Network signs of emergence in new medical terms": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-2/experiment-4
- "Code: Is openness before take-off brokerage or churn?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-3/experiment-5
- "Code: Do open concepts spread across more fields?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-3/experiment-6
- "Code: Do borrowed ideas stick when grafted locally?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-3/experiment-7
- "Code: How new concepts spread: types, roles, timing": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-3/experiment-8
- "Code: Checking the report's numbers and the closure effect": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-3/evaluation-1
- "Code: One-time held-out check of the idea-grafting result": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-4/evaluation-2
- "Code: Idea grafting replicates in biomedical MeSH concepts": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-4/experiment-9
- "Code: One-time held-out check of closure and D3 link": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-4/evaluation-3
- "Code: Checking concept spread types on unseen and medical data": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-4/evaluation-4
- "Code: Do adopters already know the partner words?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-4/evaluation-5
- "Code: Does host vocabulary start uptake or grow it?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-5/evaluation-6
- "Code: Host-specific or just common words?": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-5/evaluation-7
- "Code: Check every paper number against its source": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-5/evaluation-8
- "Code: Where the host-vocabulary finding sits in the literature": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-5/research-2
- "Code: Paper figures drawn straight from result files": https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/tree/fork/run_F1tk5OGtH84L/round-5/evaluation-9
</links>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.

<todos>
TODO 1. Read and STRICTLY follow these skills: aii-web-tools.
TODO 2. Read `paper.tex` end to end and list `figures/`. Write down the
paper's title, its author line, its contributions, and every headline number together with the
sentence it appears in — those sentences are the only numbers allowed on the page. Note which
figures are PDFs and so need a PNG rendered.
TODO 3. Render a PNG at about 200 DPI, into `figures/`, for every figure not already
in a browser-renderable format, then LOOK at each image you plan to use so you know what it shows
and how large it has to be on the page to stay legible.
TODO 4. Write `index.html` following the page_structure and technical_requirements sections
above: one file, inline CSS and JavaScript, every image referenced through the published figure
prefix.
TODO 5. VERIFY THE NUMBERS: for each number on the page, grep `paper.tex` for it and
confirm it appears there with the same meaning. Delete any number you cannot find. Then confirm
every claim on the page is one the paper actually makes.
TODO 6. VERIFY THE PAGE: confirm `index.html` has no external script, stylesheet or font
reference; that every image path starts with the published figure prefix and names a file that
exists in `figures/`; and that the PDF, repository and artifact code links are
character-for-character the URLs given in the links section — including the research report,
executive summary and round report links when they are listed there — and not `paper.pdf` nor any URL you composed. Then open the page in a browser, screenshot it at a phone width and a desktop width,
read both screenshots, and fix anything cramped, overlapping or cut off. At the desktop width,
also screenshot the page scrolled to the top, the middle and the end, and confirm the nav marks
nothing, the section in view, and the last section respectively. `chromium-headless-shell`
is already installed: drive it with Playwright (`uv pip install playwright` in a scratch virtual
environment, then launch Chromium with `executable_path` set to the output of
`which chromium-headless-shell`, with no `playwright install`). Only if that command finds
nothing, run `playwright install --with-deps chromium` instead.
TODO 7. ACCESSIBILITY PASS: tab through the whole page and confirm every control is reachable with a
visible focus ring, the lightbox traps focus and closes on Escape, headings descend without
skipping, and every image has alt text. Fix what fails.
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "PaperSiteExpectedFiles": {
      "description": "All expected output files from paper-site generation.",
      "properties": {
        "site_html_path": {
          "description": "Path to the single self-contained HTML page. Example: 'index.html'",
          "title": "Site Html Path",
          "type": "string"
        }
      },
      "required": [
        "site_html_path"
      ],
      "title": "PaperSiteExpectedFiles",
      "type": "object"
    }
  },
  "description": "Paper site \u2014 structured output from presentation-page generation.",
  "properties": {
    "summary": {
      "description": "Brief summary of the page you built: the sections it carries, which figures it shows, which numbers it quotes and where each came from in the paper.",
      "maxLength": 5000,
      "minLength": 300,
      "title": "Summary",
      "type": "string"
    },
    "out_expected_files": {
      "$ref": "#/$defs/PaperSiteExpectedFiles",
      "description": "All output files you created. Must include index.html."
    }
  },
  "required": [
    "summary",
    "out_expected_files"
  ],
  "title": "PaperSite",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.
````

### [2] SKILL-INPUT — aii-web-tools · 2026-09-30 07:04:02 UTC

The agent loaded the **aii-web-tools** skill; its `SKILL.md` (the instructions injected into the agent's context) follows verbatim.

````
---
name: aii-web-tools
description: "Runs web search, page fetch as markdown, and regex grep over full HTML or PDF text via this skill's own scripts (aii_fast_web_search.py, aii_fast_web_fetch.py) — a free-first keyless search stack with Serper fallback that works even where built-in WebSearch and WebFetch are absent. Use when a query, page, or paper must be searched, read, or mined for an exact quote, number, table value, or methodology sentence, and whenever a lossy summary would lose the detail. Triggers: web search, scholarly search, OpenAlex, Crossref, Serper, fetch a URL as markdown, read a PDF, arXiv, regex grep a page, exact quote, table value, citation check. NOT for: planning a broad multi-source literature review or mass verification campaign — use aii-web-research-tools; NOT for a PDF file already on disk — extraction, form filling, merging and PDF creation are anthropic-pdf; NOT for driving a browser or testing a UI."
---

## Web tools

You have three web capabilities: **search**, **fetch**, and **grep** (exact
regex extraction over a full page or PDF).

**Pick where they come from, in this order:**

1. **If you have built-in `WebSearch` / `WebFetch` tools, PREFER those over the
   scripts below.** They may be **deferred tools** (listed by name but with
   schemas not yet loaded) — if so, call `ToolSearch("select:WebSearch,WebFetch")`
   ONCE to load them, then use them normally. Do not skip them just because they
   need that one extra load step; they are the preferred path. Pair them with the
   `aii_web_tools__fetch_grep` script below when you need exact text / numbers /
   methodology that a summary would miss, or when reading a PDF.
2. **Only if you have NO built-in `WebSearch` / `WebFetch`** (e.g. the OpenHands
   backend), use the scripts in this skill (below). They are our own
   implementations — free-first web search (keyless general/scholarly engines,
   Serper fallback), html2text + PyMuPDF for fetch, and regex grep over the full
   document text. They work without any built-in web tools.

Workflow either way: **search** (discover) → **fetch** (read for the gist) →
**grep** (pull exact details / read PDFs).

---

## Running the scripts

Run every script with the skill's pre-provisioned interpreter (it already has
`requests`, `html2text`, `pymupdf`, `python-dotenv`). Set `PY` once:

```bash
export SKILL_DIR="$(git rev-parse --show-toplevel 2>/dev/null || echo /ai-inventor)/.claude/skills/aii-web-tools"
export PY="$SKILL_DIR/../.ability_client_venv/bin/python"
```

### 1. Search the web (free-first: general or scholarly)

```bash
# general web (default): keyless engines (ddgs, marginalia); Serper only if they miss
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation LLM" --max-results 10
# scholarly mode: OpenAlex + Crossref (DOIs, citation counts)
$PY "$SKILL_DIR/scripts/aii_fast_web_search.py" --query "neuro-symbolic FOL translation" --mode scholarly
```

Returns ranked title / URL / snippet lines. `--mode general` (default) uses
keyless general engines; `--mode scholarly` uses academic APIs. Both fall back
to Serper (paid) only when the free engines miss. Use search first to scan the
landscape; snippets are for discovery only — fetch a page before judging it.

### 2. Fetch a page as markdown (HTML or PDF)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" fetch --url "https://arxiv.org/abs/2303.11366" --max-chars 10000
```

`--max-chars` caps output (default 10000); `--char-offset N` pages further in.
Handles PDFs transparently via PyMuPDF.

### 3. Grep a page or PDF (exact regex extraction)

```bash
$PY "$SKILL_DIR/scripts/aii_fast_web_fetch.py" grep --url "https://arxiv.org/pdf/2303.11366" --pattern "verbal reinforcement" --max-matches 20 --context-chars 200
```

Returns only the matching sections with surrounding context — the right tool
for exact numbers, table values, methodology, or long PDFs where a summary
would lose the detail. `-i` for case-insensitive.

**Parallelize** independent searches/fetches in one turn; only sequence a
fetch after the search that produced its URL.

---

## Notes

- The scripts call our ability server. If a script prints
  `Ability service not available`, the server is down — say so rather than
  silently improvising a different search method.
- Do **not** hand-roll your own `requests`/scraping for search when these
  tools are available: Serper returns clean Google results and the fetch/grep
  scripts already handle HTML, PDFs, and encoding.
````

### [3] SYSTEM-USER prompt · 2026-09-30 07:04:55 UTC

```
[Image: original 3840x1648, displayed at 2000x858. Multiply coordinates by 1.92 to map to original image.]
```

### [4] SYSTEM-USER prompt · 2026-09-30 07:04:55 UTC

```
[Image: original 3312x2480, displayed at 2000x1498. Multiply coordinates by 1.66 to map to original image.]
```

### [5] SYSTEM-USER prompt · 2026-09-30 07:24:58 UTC

```
SITE VERIFICATION FAILED: 1 problem(s) in index.html.

- image source '' does not start with 'figures/', so it will not resolve once the page is published beside its figures folder

You MUST:
1. Fix every problem listed above in index.html.
2. Keep the page ONE self-contained file — all CSS and JavaScript inline, no external scripts, stylesheets or web fonts, nothing fetched at load time.
3. Point every image at figures/<filename>, where <filename> is a browser-renderable image that really exists in your figures/ folder. A vector PDF figure needs a PNG rendered beside it first; reference the PNG.
4. Keep the page a complete document that opens with <!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
5. Re-open the page and confirm it still renders before finishing.
```
