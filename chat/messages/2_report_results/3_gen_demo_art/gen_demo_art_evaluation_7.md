# gen_demo_art_evaluation_7 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `iter5_6136aaed9367` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_evaluation_7` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-09-30 03:59:22 UTC

```
model: Claude Opus 5.5 | effort: high | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-09-30 03:59:30 UTC

````
<conversion_philosophy>
**MINIMAL CHANGES — PRESERVE THE ORIGINAL CODE**

The goal is to make the artifact's code READABLE, UNDERSTANDABLE, and RUNNABLE in a short time
to someone reviewing the research, with the option to easily scale parameters back to original
values for a full run (which can take much longer). Think of this as annotating and reformatting,
not refactoring.

**DO:**
- Split the original script into logical notebook cells (imports, setup, processing, results)
- Add markdown cells BETWEEN code cells explaining what each section does and why
- Add inline comments where the logic is non-obvious
- Add a visualization/summary cell at the end showing key outputs
- Fix hardcoded file paths to use the GitHub data loading pattern

**DO NOT:**
- Rewrite functions or change algorithms
- Rename variables or restructure logic
- Add error handling, type hints, or "improvements" that weren't in the original
- Simplify or "clean up" the original code
- Remove any original comments or logic
- Change the computational approach

The reader should recognize the original script when looking at the notebook — it's the
same code, just split into cells with explanatory markdown between sections.
</conversion_philosophy>

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
Your workspace: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/`:
GOOD: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/file.py`, `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/results/out.json`
BAD: `/tmp/file.py`, `~/output.json`, `./file.py`, any path outside the workspace
</workspace>
<disposable_outputs>
A SHARED CACHE ALREADY EXISTS FOR THIS RUN: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/.shared_cache`
`HF_HOME`, `HF_HUB_CACHE`, `TRANSFORMERS_CACHE`, `HF_DATASETS_CACHE`,
`TORCH_HOME`, `PIP_CACHE_DIR` and `UV_CACHE_DIR` are ALREADY set to point
there. Every step and every iteration of this run shares it, so a model or
dataset an earlier experiment downloaded is already on disk for you.

DO NOT override those variables. In particular do NOT write the common
pattern `os.environ["HF_HOME"] = <workspace>/hf_cache` — `HF_HOME` and
`TRANSFORMERS_CACHE` are read differently by `huggingface_hub` (one has
`/hub` appended, the other does not), so pointing both at one directory
stores every weight TWICE. That mistake cost one run 25 GB of identical
blobs. If you must set them, use the values above verbatim.

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

<tool_use>
Maximize parallel tool calls. Parallelize independent operations, only sequentialize dependencies.
- Multiple searches/fetches on different topics → parallel in one turn
- Search then fetch results → sequential (need URLs first)
</tool_use>

<task>
Convert this artifact's Python script into a demo notebook with MINIMAL changes to the original code.
Split into cells, add markdown explanations between sections, add a visualization cell at the end.
Output: mini_demo_data.json + code_demo.ipynb (notebook that loads data from GitHub URL)
</task>

<artifact_info>
id: art_8qkrjl1oVzKi
type: evaluation
title: Host-specific or just common words?
summary: >-
  K2, POST-CONFIRMATION EXPLORATORY (CPU, $0). Question: is the confirmed A_cont host-entry effect host-specific or generic
  accessibility? Generality proxies: G_H (tag-weighted normalised subfield entropy) and G_F (log block frequency) from exact
  pre-entry profiles; A_lift = ln(A_cont/s_dB). Gates: A_cont rebuilt to 1e-16 and co-primary reproduced exactly in all folds.
  Spec frozen (sha256 866c60a8) before any K2 coefficient. Design analysis: P(ret>=0.5|host DGP) >= 0.99 and P(ret<0.5|generic
  DGP) = 1 in every fold. Retention b(M1)/b(M0): screen 1.01 [0.73, 1.31], held-out 1.06 [0.44, 1.80], MeSH 0.88 [0.64, 1.04],
  IVW pooled 0.97 [0.81, 1.10]. M3 A_lift|G pooled 1.34 [1.23, 1.46] (I2 0.72). Frozen rule: HOST-SPECIFIC per fold and pooled.
  Focal terms pass CRV1, wild, placebo-calibrated and 2,000-draw Freedman-Lane randomisation p (max 0.029). G_F lowers uptake
  (pooled 0.81) and G_H ~1.10; A_cont correlates negatively with generality within FE (R2 3-16%). S10 placebo host PASSES
  under M1 in all folds; ADJACENT retention (1.04) >= NATIVE (0.89). Caveats: A_lift ~ ln A_cont (within-FE r 0.997), so the
  lift leg is weak; the S2 split-generality row absorbs part of A_cont but GH_nat mechanically re-encodes the native share
  (r 0.97; post-hoc S2b keeps pooled A_cont 1.18 [1.09, 1.28]); the oracle audit check as specified fails (collinear); pyfixest,
  plain-loop and shuffled-G audits pass.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7
out_expected_files:
- eval.py
- full_eval_out.json
- mini_eval_out.json
- preview_eval_out.json
- reproducibility.md
out_demo_files:
- path: eval.py
  description: Evaluation script with metrics computation
</artifact_info>

<github_repo>
Repo URL: https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json

URLs won't work yet — files pushed to GitHub AFTER notebook creation.
Use local fallback pattern so notebook works locally (now) and in Colab (after deployment).
</github_repo>

<data_file_sizes>
Data files come in three sizes:
- preview_*_out.json — READ THIS to inspect the data structure
- mini_*_out.json (~3 examples) — use for prototyping/testing
- full_*_out.json (complete) — use for the final production run. NEVER open it directly (too large to read into context). Instead, extract values programmatically with shell commands (e.g. grep) or a Python script (use aii-long-running-tasks skill for scripts).
</data_file_sizes>

<install_dependencies_pattern>
Follow the aii-colab skill exactly. It has the install cell pattern, pre-installed package list, numpy 2.0 compat shims, and all Colab-specific rules.
</install_dependencies_pattern>

<data_loading_pattern>
`mini_demo_data.json` = curated subset for the demo.
Use this pattern for Colab compatibility (GitHub URL with local fallback):
```python
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json"
import json
from pathlib import Path

def load_data():
    try:
        import urllib.request
        with urllib.request.urlopen(GITHUB_DATA_URL) as response:
            return json.loads(response.read().decode())
    except Exception: pass
    local = Path("mini_demo_data.json")
    if local.exists(): return json.loads(local.read_text())
    raise FileNotFoundError("Could not load mini_demo_data.json")
```
</data_loading_pattern>

<notebook_structure>
--- Setup ---
Cell 1 (markdown): Title, description, what this artifact does.
Cell 2 (code): Install dependencies — follow the aii-colab skill's install cell pattern exactly. Fill in all packages imported by the artifact's code.
Cell 3 (code): Imports — copy original import block as-is, plus any additional imports needed for the notebook (e.g. matplotlib for visualization).
Cell 4 (code): Data loading helper — use the <data_loading_pattern> above.
Cell 5 (code): `data = load_data()`

--- Config ---
Config cell (code): Define ALL tunable parameters (iterations, epochs, n_samples, hidden_size, etc.) as variables at the top of this cell. Start with the ABSOLUTE MINIMUM values — the smallest that produce any output at all (e.g. 1 iteration, 2 samples, smallest array size). These get gradually increased during testing — see TODOs.

--- Processing ---
Remaining cells: One code cell per logical section of the original script. Add a markdown cell BEFORE each code cell. Copy code as closely as possible, with these changes:
  1. Replace file paths to use the loaded `data` variable.
  2. Use the config variables from the config cell (NOT hardcoded values).
  3. Minimal fixes are allowed if something doesn't work in notebook context (e.g. adjusting paths, removing CLI args, fixing imports), but keep changes to the absolute minimum.

--- Results ---
Visualization cell (code): Print key results in a readable table, plot numeric data with matplotlib if appropriate.
</notebook_structure>

<priority>
WORKING > OPTIMIZED. A small-scale demo that runs correctly is the goal. Once the notebook passes with minimum config values, scale up only if time permits — do NOT spend multiple retries chasing larger parameters. If a working version exists, finish and move on.
</priority>

<max_notebook_total_runtime>600s (10 min)</max_notebook_total_runtime>

<test_environment>
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
```
The timeout is set to <max_notebook_total_runtime>. The entire notebook must finish within this time.
`UV_VENV_CLEAR=1` recreates the venv empty at the start of every test, so each test starts clean. Do NOT delete it yourself: the pipeline removes it after you finish. If you run a test in the background, wait for its result before starting the next test.

What happens: the venv starts with only pip, jupyter and ipykernel. When the notebook's install cell runs, `google.colab` is NOT in sys.modules, so ALL packages get installed — non-Colab packages unconditionally, and Colab packages (numpy, pandas, etc.) at Colab's exact versions via the guard block. The result mirrors Colab's environment as closely as possible. If a cell fails, fix the notebook and re-run.
</test_environment>

FIRST, add ALL of these to your todo list using your task/todo-tracking tool:

CRITICAL: Todo content must be copied exactly as is written here, with NO CHANGES. These todos are intentionally detailed so that another LLM could read each one without any external context and understand exactly what it has to do.


<todos>
TODO 1. Read and STRICTLY follow these skills: aii-colab, aii-long-running-tasks.
TODO 2. Read demo file and relevant preview_* files (preview only). Understand script structure: imports, setup, processing, output. Identify ALL tunable parameters (iterations, epochs, n_samples, hidden_size, batch_size, etc.) — these go in the config cell.
TODO 3. Create `mini_demo_data.json`: curated subset from at most ONE dataset (no more than 100 diverse examples). CRITICAL: do NOT read/grep full output file — may crash. Use `head -c 5000` or stream first entries with Python to pick examples.
TODO 4. Create `code_demo.ipynb` via NotebookEdit following <notebook_structure>. Set ALL config parameters to ABSOLUTE MINIMUM values — the smallest that produce any output (e.g. 1 iteration, 2 samples, smallest array sizes). Test-run using <test_environment>. Fix all errors until it passes.
TODO 5. GRADUALLY SCALE (but don't overdo it): increase config params step by step (e.g. ~2x each round). After each increase: test-run, record runtime, fix errors. STOP SCALING as soon as results look meaningful — a working small-scale demo beats a failed large-scale one. If full original params fit within <max_notebook_total_runtime> (10% margin), use them. Otherwise keep whatever works and comment out the true original values. Do NOT spend more than 2-3 scaling rounds.
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
</todos>

---

Output the result as JSON to: `./.terminal_claude_agent_struct_out.json`

JSON Schema:
```json
{
  "$defs": {
    "DemoExpectedFiles": {
      "description": "Expected output files from code demo notebook generation.",
      "properties": {
        "notebook": {
          "default": "",
          "description": "Path to the generated demo notebook. Example: 'code_demo.ipynb'",
          "title": "Notebook",
          "type": "string"
        },
        "mini_data_file": {
          "default": "",
          "description": "Path to the mini demo data JSON (curated subset). Example: 'mini_demo_data.json'",
          "title": "Mini Data File",
          "type": "string"
        }
      },
      "title": "DemoExpectedFiles",
      "type": "object"
    }
  },
  "description": "Dataset/experiment/evaluation \u2192 Jupyter notebook demo.\n\nTitle and summary come from the parent artifact (gen_art step),\nnot from the demo agent. The agent only outputs expected files.",
  "properties": {
    "out_expected_files": {
      "$ref": "#/$defs/DemoExpectedFiles",
      "description": "All output files you created. Must include the demo notebook."
    }
  },
  "required": [],
  "title": "CodeDemo",
  "type": "object"
}
```

IMPORTANT: this task is NOT complete until `./.terminal_claude_agent_struct_out.json` exists and contains JSON matching the schema above.
````

### [3] TOOL CALL — Skill · 2026-09-30 03:59:34 UTC

```
aii-colab
```

### [4] TOOL RESULT — Skill · 2026-09-30 03:59:34 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [5] TOOL CALL — Skill · 2026-09-30 03:59:34 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-09-30 03:59:34 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [7] TOOL CALL — Bash · 2026-09-30 03:59:38 UTC

```
List artifact workspace and own workspace:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7; ls -la $W; wc -l $W/eval.py; ls -la; ls -la .aii
```

### [8] TOOL RESULT — Bash · 2026-09-30 03:59:38 UTC

```
{"stdout": "total 24160\ndrwxrwxrwx 13 aii-agent aii-agent 2002118 Sep 29 10:52 .\ndrwxrwxrwx  7 aii-agent aii-agent 2005516 Sep 29 09:11 ..\ndrwxrwxrwx  2 aii-agent aii-agent   79500 Sep 29 10:01 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Sep 29 09:45 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    4830 Sep 29 10:01 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent  330974 Sep 29 10:01 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    2004 Sep 29 09:59 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   12689 Sep 29 09:57 README.md\ndrwxrwxrwx  2 aii-agent aii-agent 1002657 Sep 29 09:47 audit\ndrwxrwxrwx  2 aii-agent aii-agent       1 Sep 29 10:52 cache\ndrwxrwxrwx  7 aii-agent aii-agent 1019787 Sep 29 09:18 d2\n-rw-rw-rw-  1 aii-agent aii-agent   13607 Sep 29 09:54 eval.py\n-rw-rw-rw-  1 aii-agent aii-agent 4348875 Sep 29 09:54 eval_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1089120 Sep 29 09:54 figures\n-rw-rw-rw-  1 aii-agent aii-agent 4655435 Sep 29 09:55 full_eval_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1002701 Sep 29 15:27 g\ndrwxrwxrwx  2 aii-agent aii-agent 1097086 Sep 29 09:17 inputs\ndrwxrwxrwx  2 aii-agent aii-agent 1008417 Sep 29 15:27 k2\ndrwxrwxrwx  2 aii-agent aii-agent 1002484 Sep 29 09:57 logs\ndrwxrwxrwx  9 aii-agent aii-agent 2000726 Sep 29 09:18 mesh\n-rw-rw-rw-  1 aii-agent aii-agent   24574 Sep 29 09:55 mini_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   22722 Sep 29 09:55 preview_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    1716 Sep 29 09:35 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    5507 Sep 29 09:57 reproducibility.md\ndrwxrwxrwx  3 aii-agent aii-agent 2000276 Sep 29 09:53 results\n259 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/eval.py\ntotal 1992\ndrwxrwxrwx 3 aii-agent aii-agent 1002540 Sep 30 03:59 .\ndrwxrwxrwx 5 aii-agent aii-agent 1008939 Sep 30 03:58 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:58 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Sep 30 03:59 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   25963 Sep 30 03:59 .repl_agent.ptylog\ntotal 980\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:58 .\ndrwxrwxrwx 3 aii-agent aii-agent 1002540 Sep 30 03:59 ..", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [9] TOOL CALL — Bash · 2026-09-30 03:59:40 UTC

```
Read eval script and supporting docs:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7; cat $W/eval.py; cat $W/reproducibility.md; cat $W/pyproject.toml; ls -la $W/k2 $W/g $W/inputs $W/results | head -80
```

### [10] TOOL RESULT — Bash · 2026-09-30 03:59:40 UTC

```
{"stdout": "#!/usr/bin/env python3\n\"\"\"K2 final assembly: figures F1-F3 and eval_out.json (schema exp_eval_sol_out) + full/mini/preview variants.\n\nReads only K2 result files (results/, audit/); computes no new coefficient.\n\"\"\"\nfrom __future__ import annotations\n\nimport json\nimport sys\nfrom pathlib import Path\n\nimport matplotlib\n\nmatplotlib.use(\"Agg\")\nimport matplotlib.pyplot as plt  # noqa: E402\nimport numpy as np  # noqa: E402\nimport pandas as pd  # noq... [truncated, 26024 chars total]
```

### [11] TOOL CALL — Bash · 2026-09-30 03:59:48 UTC

```
Inspect demean helper and input tables:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7; cd $W; grep -n "def _demean" -A40 d2/src/ppml.py | head -60; grep -n "^import\|^from" d2/src/ppml.py; python3 -c "
import pandas as pd
r=pd.read_csv('results/k2_rows.csv'); print(r.shape); print(r.columns.tolist()); print(r.groupby(['fold','model']).size())
p=pd.read_parquet('results/partner_generality.parquet'); print(p.shape); print(p.columns.tolist()); print(p.fold.value_counts()); print(p.head(3).T)
print(p.groupby('fold').concept_id.nunique())
"; head -c 1500 preview_eval_out.json
```

### [12] TOOL RESULT — Bash · 2026-09-30 03:59:50 UTC

```
{"stdout": "30:def _demean(M: np.ndarray, w: np.ndarray, fes: list[np.ndarray]) -> np.ndarray:\n31-    \"\"\"Exact weighted projection off the FE space: solve (D'WD + eps I) c = D'W M with a sparse LU (D = [D1 D2]).\"\"\"\n32-    from scipy import sparse\n33-    from scipy.sparse.linalg import splu\n34-    n = len(w)\n35-    rows, cols, off = [], [], 0\n36-    for f in fes:\n37-        rows.append(np.arange(n))\n38-        cols.append(f + off)\n39-        off += int(f.max()) + 1\n40-    D = sparse.csc_matrix((np.ones(n * len(fes)), (np.concatenate(rows), np.concatenate(cols))), shape=(n, off))\n41-    DW = sparse.csc_matrix(D.multiply(w[:, None]))\n42-    A = sparse.csc_matrix(D.T @ DW) + sparse.identity(off, format=\"csc\") * 1e-9\n43-    c = splu(A).solve(np.asarray(DW.T @ M))\n44-    return M - D @ c\n45-\n46-\n47-def pd_nunique_per_level(f: np.ndarray, g: np.ndarray) -> int:\n48-    \"\"\"Max number of distinct clusters within any FE level.\"\"\"\n49-    pairs = np.unique(np.stack([f, g], 1), axis=0)\n50-    return int(np.bincount(pairs[:, 0]).max())\n51-\n52-\n53-def fit(y: np.ndarray, X: np.ndarray, fes: list[np.ndarray], offset: np.ndarray, cluster: np.ndarray,\n54-        maxit: int = 100, tol: float = 1e-9) -> dict | None:\n55-    keep = _prune(y.astype(float), fes)\n56-    if keep.sum() < X.shape[1] + 5:\n57-        return None\n58-    y, X, off, cl = y[keep].astype(float), X[keep], offset[keep], cluster[keep]\n59-    fes = [np.unique(f[keep], return_inverse=True)[1] for f in fes]\n60-    if np.linalg.matrix_rank(_demean(X, np.ones(len(y)), fes)) < X.shape[1]:\n61-        return None\n62-    mu = np.maximum(y, 0.1 * y.mean() + 1e-3)\n63-    eta = np.log(mu)\n64-    beta = np.zeros(X.shape[1])\n65-    dev_old = np.inf\n66-    for _ in range(maxit):\n67-        z = eta - off + (y - mu) / mu\n68-        M = _demean(np.column_stack([z, X]), mu, fes)\n69-        zt, Xt = M[:, 0], M[:, 1:]\n70-        WX = Xt * mu[:, None]\n7:from __future__ import annotations\n9:import numpy as np\n(123, 36)\n['fold', 'model', 'spec', 'var', 'label', 'row_type', 'focal', 'b', 'se', 'z', 'p_crv1', 'p_wild', 'p_placebo_cal', 'p_rand', 'p_holm', 'irr_sd', 'irr_sd_lo', 'irr_sd_hi', 'irr_01', 'lnirr_sd', 'lnirr_sd_se', 'sd_retained', 'N_input', 'N', 'G', 'retained_share', 'y', 'source', 'tq', 'rand_draws_ok', 'rand_z_sd', 'fl_r2_focal_on_rest', 'note', 'Q', 'p_Q', 'I2']\nfold        model \nheldout     M0        1\n            M1        3\n            M2        1\n            M3        3\n            S11_M0    1\n            S11_M1    1\n            S1_M0     1\n            S1_M1     3\n            S2        7\n            S3_G      4\n            S3_noG    2\n            S4        1\n            S5        1\n            S6        3\n            S7_M0     1\n            S7_M1     3\n            S9_M2     1\n            S9_M3     3\nmesh        M0        1\n            M1        3\n            M2        1\n            M3        3\n            S11_M0    1\n            S11_M1    1\n            S1_M0     1\n            S1_M1     3\n            S2        7\n            S3_G      4\n            S3_noG    2\n            S4        1\n            S5        1\n            S6        3\n            S7_M0     1\n            S7_M1     3\n            S8        3\npooled_IVW  M0        1\n            M1        3\n            M2        1\n            M3        3\nscreen      M0        1\n            M1        3\n            M2        1\n            M3        3\n            S11_M0    1\n            S11_M1    1\n            S1_M0     1\n            S1_M1     3\n            S2        7\n            S3_G      4\n            S3_noG    2\n            S4        1\n            S5        1\n            S6        3\n            S7_M0     1\n            S7_M1     3\ndtype: int64\n(5086, 31)\n['fold', 'concept_id', 'd', 'e', 'o', 'n_entry_papers', 'A_cont', 'A_cont_rebuilt', 'A_lift', 's_dB', 'K_B', 'G_H', 'G_F', 'G_H_ub', 'G_H_bg', 'n_prof_tags', 'n_gen_tags', 'n_exact_tags', 'cov', 'cov_exact', 'cov_gen', 'GH_nat', 'GH_adj', 'GH_for', 'GF_nat', 'GF_adj', 'GF_for', 'NAT', 'ADJ', 'A_spec', 'zeroA']\nfold\nmesh       2249\nscreen     1740\nheldout    1097\nName: count, dtype: int64\n                             0               1               2\nfold                    screen          screen          screen\nconcept_id      c_9cceb3c510be  c_9cceb3c510be  c_9cceb3c510be\nd                         1312            1702            1703\ne                         2019            2011            2019\no                         3107            3107            3107\nn_entry_papers               1               3               1\nA_cont                0.006534        0.142039        0.011077\nA_cont_rebuilt        0.006534        0.142039        0.011077\nA_lift                -1.24056        2.221236        1.002551\ns_dB                  0.022592        0.015408        0.004065\nK_B                        252             252             252\nG_H                   0.589208        0.590769        0.543893\nG_F                  12.545433       11.761598       12.122604\nG_H_ub                0.591629        0.592586        0.546046\nG_H_bg                0.589208        0.590769        0.543893\nn_prof_tags                  4              23               3\nn_gen_tags                 4.0            23.0             3.0\nn_exact_tags                 4              23               3\ncov                   0.571429        0.547619             0.6\ncov_exact             0.571429        0.547619             0.6\ncov_gen               0.571429        0.547619             0.6\nGH_nat                     0.0        0.058293             0.0\nGH_adj                     0.0        0.177267             0.0\nGH_for                0.589208        0.355209        0.543893\nGF_nat                     0.0        1.652627             0.0\nGF_adj                     0.0         3.58612             0.0\nGF_for               12.545433        6.522852       12.122604\nNAT                        0.0        0.173913             0.0\nADJ                        0.0        0.304348             0.0\nA_spec               -0.064836        0.067452       -0.040928\nzeroA                    False           False           False\nfold\nheldout     93\nmesh       187\nscreen     184\nName: concept_id, dtype: int64\n{\n  \"metadata\": {\n    \"evaluation_name\": \"K2 host-specific vs generic accessibility (POST-CONFIRMATION EXPLORATORY)\",\n    \"spec_sha256\": \"866c60a82ce4a5d3adf18e838e29effbc0d4535f0f45583895cb8f74b5156848\",\n    \"verdict_pooled\": \"HOST-SPECIFIC\",\n    \"qualifiers_pooled\": [],\n    \"verdicts_folds\": {\n      \"screen\": \"HOST-SPECIFIC\",\n      \"heldout\": \"HOST-SPECIFIC\",\n      \"mesh\": \"HOST-SPECIFIC\"\n    },\n    \"qualifiers_folds\": {\n      \"screen\": [],\n      \"heldout\": [\n        \"retention CI includes 0.5 (not decisive)\"\n      ],\n      \"mesh\": []\n    },\n    \"verdict_coding\": \"k2_verdict_*: 1 HOST-SPECIFIC, 0 MIXED, -1 GENERIC ACCESSIBILITY\",\n    \"decision_rule\": {\n      \"GENERIC ACCESSIBILITY\": \"generality controls remove > 50% of the log-IRR (ret < 0.5)\",\n      \"HOST-SPECIFIC\": \"A_lift CI excludes 1 (M3; CRV1 t(G-1) CI per fold, IVW CI pooled) AND retention >= 0.5\",\n      \"MIXED\": \"otherwise\",\n      \"implementation\": \"'excludes 1' is read as CI entirely above 1 (a CI entirely below 1 is reported as a negative lift and labelled MIXED unless ret < 0.5)\",\n      \"qualifiers\": [\n        \"retention CI includes 0.5 (not decisive)\",\n        \"fragile: randomisation p of the focal term (M1 A_cont or M3 A_lift) > 0.05 while CRV1 p < 0.05\",\n        \"retention underpowered: Step-3 P(ret_hat >= 0.5 | DGP-S) < 0.8\"\n      ],\n      \"reading\": \"the POOLED verdict is the paper's reading; fold verdicts are descriptive\"\n    },\n    \"sources\": \"results/k2_summary.json, results/k2_rows.csv, results/k2_power.", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-09-30 04:00:16 UTC

```
Check event distribution per concept and NaNs:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7; cd $W; python3 -c "
import pandas as pd, json
p=pd.read_parquet('results/partner_generality.parquet')
print(p[['A_cont','G_H','G_F']].isna().sum())
for f,g in p.groupby('fold'):
    c=g.groupby('concept_id').size().sort_values(ascending=False); print(f, c.head(8).tolist(), g.e.nunique(), g.d.nunique())
for fn in ['results/k2_summary.json','results/k2_power.json','audit/audit_k2.json','results/k2_s2b_diagnostic.json']:
    t=open(fn).read(); print(fn, len(t), 'NaN' in t, 'Infinity' in t)
"; python3 -c "import pyarrow" && echo ok
```

### [14] TOOL RESULT — Bash · 2026-09-30 04:00:18 UTC

```
{"stdout": "A_cont    0\nG_H       0\nG_F       0\ndtype: int64\nheldout [72, 71, 57, 49, 43, 42, 40, 31] 15 173\nmesh [44, 39, 37, 36, 34, 34, 32, 31] 15 70\nscreen [56, 53, 52, 51, 51, 48, 46, 36] 15 173\nresults/k2_summary.json 45291 False False\nresults/k2_power.json 3630 False False\naudit/audit_k2.json 13978 False False\nresults/k2_s2b_diagnostic.json 4143 False False\nok", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [15] THINKING · 2026-09-30 04:00:34 UTC

```
eval.py just assembles figures and metrics from precomputed K2 result files. I'll now build mini_demo_data.json, bundling those results with a curated 99-event subset of the partner-generality table.
```

### [16] TOOL CALL — Bash · 2026-09-30 04:00:34 UTC

```
Write and run the mini demo data builder:
mkdir -p /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi && cat > /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/build_mini_demo_data.py <<'EOF'
"""Build mini_demo_data.json for code_demo.ipynb from the K2 evaluation artifact's result files.

Bundles every small result file eval.py reads (summary, power, placebo, audit, gates, descriptives,
S2b diagnostic, spec, k2_rows.csv) plus ONE curated dataset: 99 entry events (33 per fold) from
results/partner_generality.parquet, chosen so that concept + e + d fixed effects leave within-FE variation.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path(sys.argv[1])  # the gen_art_evaluation_7 workspace
OUT = Path(__file__).resolve().parent / "mini_demo_data.json"
N_PER_FOLD, SEED = 33, 20261001


def recs(df: pd.DataFrame) -> list[dict]:
    return json.loads(df.to_json(orient="records"))  # NaN -> null


pg = pd.read_parquet(SRC / "results/partner_generality.parquet")
picked = []
for f in ["screen", "heldout", "mesh"]:
    g = pg[pg.fold == f]
    top = g.groupby("concept_id").size().sort_values(ascending=False).index[:3]
    g = g[g.concept_id.isin(top)]
    # keep events whose destination d and entry year e recur, so FE demeaning leaves residual variation
    g = g[g.groupby("d").d.transform("size") >= 2]
    g = g[g.groupby("e").e.transform("size") >= 2]
    picked.append(g.sample(n=min(N_PER_FOLD, len(g)), random_state=SEED).sort_values(["concept_id", "e", "d"]))
pg_mini = pd.concat(picked, ignore_index=True)

data = {
    "k2_summary": json.loads((SRC / "results/k2_summary.json").read_text()),
    "k2_power": json.loads((SRC / "results/k2_power.json").read_text()),
    "k2_placebo_host": json.loads((SRC / "results/k2_placebo_host.json").read_text()),
    "audit_k2": json.loads((SRC / "audit/audit_k2.json").read_text()),
    "gates": json.loads((SRC / "results/gates.json").read_text()),
    "k2_descriptives": json.loads((SRC / "results/k2_descriptives.json").read_text()),
    "k2_s2b_diagnostic": json.loads((SRC / "results/k2_s2b_diagnostic.json").read_text()),
    "k2_spec": json.loads((SRC / "results/k2_spec.json").read_text()),
    "k2_rows": recs(pd.read_csv(SRC / "results/k2_rows.csv")),
    "partner_generality": recs(pg_mini),
}
OUT.write_text(json.dumps(data, indent=1))
print(OUT, OUT.stat().st_size, "bytes;", len(data["k2_rows"]), "k2 rows;", len(pg_mini), "entry events",
      pg_mini.fold.value_counts().to_dict())
EOF
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi && python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7
```

### [17] TOOL RESULT — Bash · 2026-09-30 04:00:36 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/mini_demo_data.json 308970 bytes; 123 k2 rows; 99 entry events {'screen': 33, 'heldout': 33, 'mesh': 33}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [18] ASSISTANT · 2026-09-30 04:02:16 UTC

```
Now I'm writing the notebook. It keeps the original code, with the file reads swapped for the loaded `data`.
```

### [19] TOOL CALL — Bash · 2026-09-30 04:02:16 UTC

```
Generate the demo notebook:
python3 - <<'PYEOF'
import json
cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")})

md(r'''
# Host-specific or just common words? — K2 evaluation demo

**K2 is a post-confirmation exploratory analysis. It ran on CPU only and cost $0.** A confirmed result says that a new concept ... [truncated, 26799 chars total]
```

### [20] TOOL RESULT — Bash · 2026-09-30 04:02:16 UTC

```
{"stdout": "25 cells\nN_PG_PER_FOLD = 33", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [21] ASSISTANT · 2026-09-30 04:02:24 UTC

```
Now for a minimal test run with 3 events per fold:
```

### [22] TOOL CALL — Bash · 2026-09-30 04:02:24 UTC

```
Test-run notebook at minimum config in clean venv:
sed -i 's/N_PG_PER_FOLD = 33   #/N_PG_PER_FOLD = 3    #/' code_demo.ipynb && grep -o 'N_PG_PER_FOLD = [0-9]* ' code_demo.ipynb | head -1 && E=/tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && time $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -20
```

### [23] TOOL RESULT — Bash · 2026-09-30 04:02:52 UTC

```
{"stdout": "N_PG_PER_FOLD = 3 \n\u001b[32m     32\u001b[39m \n\u001b[32m     33\u001b[39m \n\u001b[32m---> \u001b[39m\u001b[32m34\u001b[39m out = main()\n\n\u001b[36mFile \u001b[39m\u001b[32m/tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b/lib/python3.12/site-packages/loguru/_logger.py:1297\u001b[39m, in \u001b[36mLogger.catch.<locals>.Catcher.__call__.<locals>.catch_wrapper\u001b[39m\u001b[34m(*args, **kwargs)\u001b[39m\n\u001b[32m   1295\u001b[39m \u001b[38;5;28;01mdef\u001b[39;00m\u001b[38;5;250m \u001b[39m\u001b[34mcatch_wrapper\u001b[39m(*args, **kwargs):\n\u001b[32m   1296\u001b[39m     \u001b[38;5;28;01mwith\u001b[39;00m catcher:\n\u001b[32m-> \u001b[39m\u001b[32m1297\u001b[39m         \u001b[38;5;28;01mreturn\u001b[39;00m \u001b[30;43mfunction\u001b[39;49m\u001b[30;43m(\u001b[39;49m\u001b[30;43m*\u001b[39;49m\u001b[30;43margs\u001b[39;49m\u001b[30;43m,\u001b[39;49m\u001b[30;43m \u001b[39;49m\u001b[30;43m*\u001b[39;49m\u001b[30;43m*\u001b[39;49m\u001b[30;43mkwargs\u001b[39;49m\u001b[30;43m)\u001b[39;49m\n\u001b[32m   1298\u001b[39m     \u001b[38;5;28;01mreturn\u001b[39;00m default\n\n\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[12]\u001b[39m\u001b[32m, line 3\u001b[39m, in \u001b[36mmain\u001b[39m\u001b[34m()\u001b[39m\n\u001b[32m      1\u001b[39m @logger.catch(reraise=\u001b[38;5;28;01mTrue\u001b[39;00m)\n\u001b[32m      2\u001b[39m \u001b[38;5;28;01mdef\u001b[39;00m main() -> \u001b[38;5;28;01mNone\u001b[39;00m:\n\u001b[32m----> \u001b[39m\u001b[32m3\u001b[39m     summ = data[\u001b[33m\"k2_summary\"\u001b[39m]          \u001b[38;5;66;03m# original: results/k2_summary.json\u001b[39;00m\n\u001b[32m      4\u001b[39m     power = data[\u001b[33m\"k2_power\"\u001b[39m]           \u001b[38;5;66;03m# original: results/k2_power.json\u001b[39;00m\n\u001b[32m      5\u001b[39m     plc = data[\u001b[33m\"k2_placebo_host\"\u001b[39m]      \u001b[38;5;66;03m# original: results/k2_placebo_host.json\u001b[39;00m\n\u001b[32m      6\u001b[39m     aud = data[\u001b[33m\"audit_k2\"\u001b[39m]             \u001b[38;5;66;03m# original: audit/audit_k2.json\u001b[39;00m\n\n\u001b[31mKeyError\u001b[39m: 'k2_summary'\n\n\nreal\t0m24.916s\nuser\t0m17.835s\nsys\t0m1.398s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [24] ASSISTANT · 2026-09-30 04:02:58 UTC

```
The run failed because `data` has no `k2_summary` key. It looks like the GitHub URL already serves a different file, so I'll check what it returns:
```

### [25] TOOL CALL — Bash · 2026-09-30 04:02:58 UTC

```
Inspect loaded data and check GitHub URL:
python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
for c in nb['cells'][4:6]:
  for o in c.get('outputs',[]): print(o.get('text', o)[:1500] if isinstance(o.get('text'),str) else o)
"; curl -s -o /dev/null -w "%{http_code} %{size_download}\n" https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json
```

### [26] TOOL RESULT — Bash · 2026-09-30 04:02:58 UTC

```
{"stdout": "200 2217917", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [27] ASSISTANT · 2026-09-30 04:03:04 UTC

```
The URL already returns 200 with a 2.2 MB file, probably a stale demo from an earlier round. I'll look at its structure:
```

### [28] TOOL CALL — Bash · 2026-09-30 04:03:04 UTC

```
Inspect structure of the existing remote file:
curl -s https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json | python3 -c "
import json,sys; d=json.load(sys.stdin); print(type(d)); print(list(d.keys())[:20] if isinstance(d,dict) else len(d)); 
print(json.dumps(d.get('metadata',{}))[:600] if isinstance(d,dict) else '')"
```

### [29] TOOL RESULT — Bash · 2026-09-30 04:03:06 UTC

```
{"stdout": "<class 'dict'>\n['metadata', 'folds', 'full_run_reference']\n{\"artifact\": \"art_8qkrjl1oVzKi (gen_art_evaluation_7, iteration 5)\", \"description\": \"K2 input samples of the three folds (screen, held-out, MeSH): one row per concept-entry event (concept c enters host subfield d in year e) with the outcome Y_strict, the host-share A_cont, the co-primary controls and the partner-generality proxies G_H / G_F. All events of every fold are included (no subsampling).\", \"label\": \"POST-CONFIRMATION EXPLORATORY\", \"seed\": 20261001, \"controls\": [\"CT\", \"prox_od\", \"RD\", \"log_n_partner_tags\", \"cov\", \"demic\", \"mean_topic_score\", \"boundary_share\", \"abstract_share\", \"mom_d\",", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [30] THINKING · 2026-09-30 04:03:16 UTC

```
I found that file is an earlier demo version, which the publish step will overwrite with my mini_demo_data.json. For now, I'll test on a copy with an unreachable URL to trigger the local fallback, then restore the correct URL in the executed notebook.
```

### [31] TOOL CALL — Bash · 2026-09-30 04:03:16 UTC

```
Test notebook using local data fallback:
cat > run_test.sh <<'EOF'
#!/usr/bin/env bash
# Test-run code_demo.ipynb in a clean venv. The published GitHub URL still serves an older demo file until the
# publish step pushes this mini_demo_data.json, so the test copy points at an unreachable URL (forcing the local
# fallback) and the exact URL is restored in the executed notebook afterwards.
set -euo pipefail
cd "$(dirname "$0")"
E=/tmp/aii_nb_test_envs/art_8qkrjl1oVzKi-07c32cee5d7b
URL="https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json"
BOGUS="https://raw.githubusercontent.com/ai-inventor-papers/__not_yet_published__/mini_demo_data.json"
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel
sed "s#$URL#$BOGUS#" code_demo.ipynb > _test_code_demo.ipynb
$E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 _test_code_demo.ipynb --output code_demo.ipynb
sed -i "s#$BOGUS#$URL#" code_demo.ipynb
rm -f _test_code_demo.ipynb
grep -c "$URL" code_demo.ipynb
EOF
chmod +x run_test.sh && time ./run_test.sh 2>&1 | tail -5
```

### [32] TOOL RESULT — Bash · 2026-09-30 04:03:44 UTC

```
{"stdout": "[NbConvertApp] Converting notebook _test_code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 279507 bytes to code_demo.ipynb\n1\n\nreal\t0m28.056s\nuser\t0m20.908s\nsys\t0m2.935s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] TOOL CALL — Bash · 2026-09-30 04:03:48 UTC

```
Print notebook outputs:
python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
  for o in c.get('outputs',[]):
    if o['output_type']=='stream': print(i, o['text'][:2500])
    elif o['output_type']=='error': print(i,'ERR',o['ename'],o['evalue'])
    else: print(i, o['output_type'], list(o.get('data',{}).keys()))
"
```

### [34] TOOL RESULT — Bash · 2026-09-30 04:03:48 UTC

```
{"stdout": "6 [\"{'k2_summary': 8, 'k2_power': 4, 'k2_placebo_host': 6, 'audit_k2': 7, 'gates': 4, 'k2_descriptives': 3, 'k2_s2b_diagnostic': 3, 'k2_spec': 24, 'k2_rows': 123, 'partner_generality': 99}\\n\"]\n22 display_data ['image/png', 'text/plain']\n22 display_data ['image/png', 'text/plain']\n22 display_data ['image/png', 'text/plain']\n22 ['04:03:42|INFO   |figures written\\n']\n22 [\"04:03:42|INFO   |eval_out.json: 297 metrics; datasets [('k2_rows', 123), ('entry_generality', 9)]\\n\"]\n24 ['Spec sha256: 866c60a82ce4a5d3 …\\n', 'Pooled verdict: HOST-SPECIFIC | qualifiers: none\\n', '           fold       verdict   ret b(M1)/b(M0) M3 A_lift|G IRR/SD  P(ret>=.5|host DGP)  P(ret<.5|generic DGP)\\n', '  Screen (main) HOST-SPECIFIC 1.01 [0.73, 1.31]  1.66 [1.36, 2.03]             1.000000                    1.0\\n', 'Held-out (main) HOST-SPECIFIC 1.06 [0.44, 1.80]  1.46 [1.15, 1.86]             1.000000                    1.0\\n', '           MeSH HOST-SPECIFIC 0.88 [0.64, 1.04]  1.24 [1.12, 1.38]             0.993333                    1.0\\n', '     IVW pooled HOST-SPECIFIC 0.97 [0.81, 1.10]  1.34 [1.23, 1.46]             1.000000                    1.0\\n', '\\n', 'Pooled M1 generality controls (IRR/SD): G_H 1.10 [1.00, 1.22], G_F 0.81 [0.74, 0.89]\\n', \"S10 placebo host passes under M1: {'screen': True, 'heldout': True, 'mesh': True}\\n\", \"S3 retention NATIVE vs ADJACENT: {'screen': (0.89, 1.01), 'heldout': (1.02, 1.01), 'mesh': (0.83, 1.1)}\\n\", \"Audit pass flags: {'a_entries': 1, 'b_pyfixest': 1, 'c_shuffled_G': 1, 'd_oracle_as_specified': 0, 'd2_oracle_total_conserved': 0, 'd3_positive_control_DGP_G': 1}\\n\", '\\n', \"297 metrics; datasets: [('k2_rows', 123), ('entry_generality', 9)]\\n\"]\n24 display_data ['image/png', 'text/plain']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [35] ASSISTANT · 2026-09-30 04:03:56 UTC

```
The minimum-config run passes in about 28 s, most of it package installs. Next I'll check that the 297 metrics match the original `full_eval_out.json`, then scale to the full 33 events per fold:
```

### [36] TOOL CALL — Bash · 2026-09-30 04:03:56 UTC

```
Compare metrics to original, then scale to 33 per fold:
python3 -c "
import json
a=json.load(open('eval_out.json'))['metrics_agg']
b=json.load(open('/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/full_eval_out.json'))['metrics_agg']
print(len(a),len(b), set(a)^set(b), max(abs(a[k]-b[k]) for k in a))
" && sed -i 's/N_PG_PER_FOLD = 3    #/N_PG_PER_FOLD = 33   #/' code_demo.ipynb && time ./run_test.sh 2>&1 | tail -2 && python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
  for o in c.get('outputs',[]):
    if o['output_type']=='stream' and i==22: print(o['text'])
    if o['output_type']=='error': print('ERR')
"; ls figures
```

### [37] TOOL RESULT — Bash · 2026-09-30 04:04:56 UTC

```
{"stdout": "297 297 set() 0.0\n[NbConvertApp] Writing 283777 bytes to code_demo.ipynb\n1\n\nreal\t0m58.470s\nuser\t0m18.892s\nsys\t0m2.608s\n['04:04:53|INFO   |figures written\\n']\n[\"04:04:53|INFO   |eval_out.json: 297 metrics; datasets [('k2_rows', 123), ('entry_generality', 99)]\\n\"]\nF1_k2_forest.pdf\nF1_k2_forest.png\nF2_retention.pdf\nF2_retention.png\nF3_generality_scatter.pdf\nF3_generality_scatter.png", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [38] ASSISTANT · 2026-09-30 04:04:58 UTC

```
All 297 metrics match the original exactly. I'll check the F3 scatter at full size:
```

### [39] TOOL CALL — Read · 2026-09-30 04:04:58 UTC

```
/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/figures/F3_generality_scatter.png
```

### [40] TOOL RESULT — Read · 2026-09-30 04:05:00 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [41] THINKING · 2026-09-30 04:05:10 UTC

```
The F3 scatter is degenerate since the fixed effects absorb nearly all variation in that 33-event subset. I'll re-select events concentrated in fewer destinations and years to preserve real within-FE variation.
```

### [42] TOOL CALL — Bash · 2026-09-30 04:05:10 UTC

```
Search for a subset with within-FE variation:
python3 - <<'EOF'
import pandas as pd, numpy as np, sys
sys.path.insert(0,'/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/d2/src')
import ppml
pg=pd.read_parquet('/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/results/partner_generality.parquet')
def within(df, cols):
    fes=[pd.factorize(df[c])[0] for c in ("concept_id","e","d")]
    return ppml._demean(df[cols].to_numpy(float), np.ones(len(df)), fes)
for f in ["screen","heldout","mesh"]:
    g=pg[pg.fold==f]
    M=within(g,["A_cont","G_H","G_F"]); print(f,'full r',np.corrcoef(M[:,0],M[:,1])[0,1].round(2),np.corrcoef(M[:,0],M[:,2])[0,1].round(2))
    for nd in (2,3,4):
        topd=g.d.value_counts().index[:nd]; h=g[g.d.isin(topd)]
        tope=h.e.value_counts().index[:6]; h=h[h.e.isin(tope)]
        s=h.sample(n=min(33,len(h)),random_state=20261001)
        M=within(s,["A_cont","G_H","G_F"])
        print(' nd',nd,len(h),s.concept_id.nunique(),'sdA',M[:,0].std().round(4),'r',np.corrcoef(M[:,0],M[:,1])[0,1].round(2),np.corrcoef(M[:,0],M[:,2])[0,1].round(2))
EOF
```

### [43] TOOL RESULT — Bash · 2026-09-30 04:05:12 UTC

```
{"stdout": "screen full r -0.22 -0.11\n nd 2 79 32 sdA 0.0 r -0.62 -0.41\n nd 3 113 32 sdA 0.0 r -0.01 -0.27\n nd 4 141 29 sdA 0.0 r -0.35 -0.48\nheldout full r -0.16 -0.06\n nd 2 48 30 sdA 0.0035 r -1.0 -1.0\n nd 3 71 26 sdA 0.0241 r -1.0 1.0\n nd 4 84 31 sdA 0.0 r -0.65 -0.76\nmesh full r -0.39 -0.25\n nd 2 107 28 sdA 0.0101 r 0.4 0.94\n nd 3 158 29 sdA 0.0 r 0.6 0.71\n nd 4 206 32 sdA 0.0 r -0.38 -0.35", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] TOOL CALL — Bash · 2026-09-30 04:05:24 UTC

```
Grid-search subset maximizing residual degrees of freedom:
python3 - <<'EOF'
import pandas as pd, numpy as np
pg=pd.read_parquet('/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/results/partner_generality.parquet')
def dof(s):
    D=np.column_stack([pd.get_dummies(s[c].astype(str)).to_numpy(float) for c in ("concept_id","e","d")])
    return len(s)-np.linalg.matrix_rank(D)
for f in ["screen","heldout","mesh"]:
    g=pg[pg.fold==f]; best=(0,None)
    cs=g.concept_id.value_counts().index
    for K in (2,3,4,6):
        for nd in (1,2,3,4,6):
            for ne in (3,5,8,15):
                h=g[g.concept_id.isin(cs[:K])]
                h=h[h.d.isin(h.d.value_counts().index[:nd])]; h=h[h.e.isin(h.e.value_counts().index[:ne])]
                if len(h)<33: continue
                for seed in range(5):
                    s=h.sample(n=33,random_state=seed); v=dof(s)
                    if v>best[0]: best=(v,(K,nd,ne,seed))
    print(f,best)
EOF
```

### [45] TOOL RESULT — Bash · 2026-09-30 04:05:26 UTC

```
{"stdout": "screen (0, None)\nheldout (0, None)\nmesh (np.int64(13), (6, 6, 15, 3))", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [46] TOOL CALL — Bash · 2026-09-30 04:05:34 UTC

```
Search subsets sharing destinations across concepts:
python3 - <<'EOF'
import pandas as pd, numpy as np
pg=pd.read_parquet('/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7/results/partner_generality.parquet')
def dof(s):
    D=np.column_stack([pd.get_dummies(s[c].astype(str)).to_numpy(float) for c in ("concept_id","e","d")])
    return len(s)-np.linalg.matrix_rank(D)
def prune(h):
    while True:
        n=len(h)
        for c in ("concept_id","e","d"): h=h[h.groupby(c)[c].transform("size")>=2]
        if len(h)==n: return h
for f in ["screen","heldout","mesh"]:
    g=pg[pg.fold==f]; best=(0,None)
    for nd in (2,3,4,6,10,20):
        for ne in (3,5,8,15):
            h=g[g.d.isin(g.d.value_counts().index[:nd])]; h=prune(h[h.e.isin(h.e.value_counts().index[:ne])])
            if len(h)<33: continue
            # keep the concepts with most events until >=33, then prune and sample
            cs=h.concept_id.value_counts()
            for K in range(2,len(cs)+1):
                hk=prune(h[h.concept_id.isin(cs.index[:K])])
                if len(hk)>=33: break
            for seed in range(8):
                s=hk.sample(n=33,random_state=seed); v=dof(s)
                if v>best[0]: best=(v,(nd,ne,K,seed,len(hk)))
    print(f,best)
EOF
```

### [47] TOOL RESULT — Bash · 2026-09-30 04:05:38 UTC

```
{"stdout": "screen (np.int64(17), (20, 3, 5, 3, 35))\nheldout (np.int64(16), (10, 3, 8, 0, 35))\nmesh (np.int64(16), (6, 3, 10, 0, 33))", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [48] ASSISTANT · 2026-09-30 04:05:52 UTC

```
This finds subsets with 16–17 residual degrees of freedom per fold. I'll put the search into the builder and rebuild:
```

### [49] TOOL CALL — Bash · 2026-09-30 04:05:52 UTC

```
Update builder selection and rebuild mini data:
python3 - <<'EOF'
from pathlib import Path
p=Path('build_mini_demo_data.py'); s=p.read_text()
old=s[s.index('pg = pd.read_parquet'):s.index('pg_mini = pd.concat')]
new='''def fe_dof(s: pd.DataFrame) -> int:
    """Residual degrees of freedom left after concept + e + d fixed effects."""
    D = np.column_stack([pd.get_dummies(s[c].astype(str)).to_numpy(float) for c in ("concept_id", "e", "d")])
    return len(s) - np.linalg.matrix_rank(D)


def prune(h: pd.DataFrame) -> pd.DataFrame:
    """Drop events whose concept, e or d level is a singleton (fully absorbed by its FE), until stable."""
    while True:
        n = len(h)
        for c in ("concept_id", "e", "d"):
            h = h[h.groupby(c)[c].transform("size") >= 2]
        if len(h) == n:
            return h


pg = pd.read_parquet(SRC / "results/partner_generality.parquet")
picked = []
for f in ["screen", "heldout", "mesh"]:
    g = pg[pg.fold == f]
    # small grid: events in the nd most common destinations d and ne most common entry years e, from the fewest
    # concepts that still give >= N_PER_FOLD events; keep the draw with most within-FE degrees of freedom.
    # A random subset would be almost fully absorbed by concept + e + d FE (within-FE residuals ~1e-10).
    best = (-1, None)
    for nd in (2, 3, 4, 6, 10, 20):
        for ne in (3, 5, 8, 15):
            h = g[g.d.isin(g.d.value_counts().index[:nd])]
            h = prune(h[h.e.isin(h.e.value_counts().index[:ne])])
            if len(h) < N_PER_FOLD:
                continue
            cs = h.concept_id.value_counts()
            for K in range(2, len(cs) + 1):
                hk = prune(h[h.concept_id.isin(cs.index[:K])])
                if len(hk) >= N_PER_FOLD:
                    break
            for seed in range(8):
                s = hk.sample(n=N_PER_FOLD, random_state=seed)
                v = fe_dof(s)
                if v > best[0]:
                    best = (v, s)
    print(f, "within-FE dof", best[0])
    picked.append(best[1].sort_values(["concept_id", "e", "d"]))
'''
p.write_text(s.replace(old,new).replace("plus ONE curated dataset: 99 entry events (33 per fold) from\nresults/partner_generality.parquet, chosen so that concept + e + d fixed effects leave within-FE variation.",
 "plus ONE curated dataset: 99 entry events (33 per fold) from\nresults/partner_generality.parquet, chosen so that concept + e + d fixed effects leave within-FE variation\n(about 16 residual degrees of freedom per fold)."))
EOF
python3 build_mini_demo_data.py /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_5/gen_art/gen_art_evaluation_7 && head -8 build_mini_demo_data.py
```

### [50] TOOL RESULT — Bash · 2026-09-30 04:05:56 UTC

```
{"stdout": "screen within-FE dof 17\nheldout within-FE dof 16\nmesh within-FE dof 16\n/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/mini_demo_data.json 309699 bytes; 123 k2 rows; 99 entry events {'screen': 33, 'heldout': 33, 'mesh': 33}\n\"\"\"Build mini_demo_data.json for code_demo.ipynb from the K2 evaluation artifact's result files.\n\nBundles every small result file eval.py reads (summary, power, placebo, audit, gates, descriptives,\nS2b diagnostic, spec, k2_rows.csv) plus ONE curated dataset: 99 entry events (33 per fold) from\nresults/partner_generality.parquet, chosen so that concept + e + d fixed effects leave within-FE variation\n(about 16 residual degrees of freedom per fold).\n\"\"\"\nimport json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [51] TOOL CALL — Bash · 2026-09-30 04:06:02 UTC

```
Update F3 note and re-test notebook:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb'))
for c in nb['cells']:
    if c['cell_type']=='markdown' and c['source'].startswith('## F3'):
        c['source']=c['source'].replace("In the full data, the within-FE correlations are negative, with an R² of 3–16%.",
          "In the full data (5,086 events), the within-FE correlations are negative, with an R² of 3–16%. The demo subset has only 33 events per fold, selected so that about 16 residual degrees of freedom per fold survive the fixed effects. Its per-fold `r` values are therefore noisy and illustrative only.")
json.dump(nb,open('code_demo.ipynb','w'),indent=1)
EOF
time ./run_test.sh 2>&1 | tail -2; python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
print([o['ename'] for c in nb['cells'] for o in c.get('outputs',[]) if o['output_type']=='error'])"
```

### [52] TOOL RESULT — Bash · 2026-09-30 04:06:30 UTC

```
{"stdout": "Traceback (most recent call last):\n  File \"<stdin>\", line 4, in <module>\nAttributeError: 'list' object has no attribute 'startswith'\n[NbConvertApp] Writing 291149 bytes to code_demo.ipynb\n1\n\nreal\t0m28.132s\nuser\t0m20.357s\nsys\t0m2.799s\n[]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [53] ASSISTANT · 2026-09-30 04:06:38 UTC

```
After nbconvert, cell sources are stored as lists of lines, so the markdown edit didn't apply. I'll redo it on the joined text:
```

### [54] TOOL CALL — Bash · 2026-09-30 04:06:38 UTC

```
Apply F3 markdown note edit:
python3 - <<'EOF'
import json
nb=json.load(open('code_demo.ipynb')); n=0
for c in nb['cells']:
    s=''.join(c['source']) if isinstance(c['source'],list) else c['source']
    if c['cell_type']=='markdown' and s.startswith('## F3'):
        c['source']=s.replace("In the full data, the within-FE correlations are negative, with an R² of 3–16%.",
          "In the full data (5,086 events), the within-FE correlations are negative, with an R² of 3–16%. The demo subset has only 33 events per fold, selected so that about 16 residual degrees of freedom per fold survive the fixed effects. Its per-fold `r` values are therefore noisy and illustrative only."); n+=1
json.dump(nb,open('code_demo.ipynb','w'),indent=1); print(n, 'noisy' in open('code_demo.ipynb').read())
EOF
```

### [55] TOOL RESULT — Bash · 2026-09-30 04:06:38 UTC

```
{"stdout": "1 True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [56] TOOL CALL — Read · 2026-09-30 04:06:38 UTC

```
/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_5/art_8qkrjl1oVzKi/figures/F3_generality_scatter.png
```

### [57] TOOL RESULT — Read · 2026-09-30 04:06:39 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [58] ASSISTANT · 2026-09-30 04:06:47 UTC

```
The scatter now shows real within-FE variation. I'll do a final clean run after the markdown edit, then write the README, manifest and structured output:
```

### [59] TOOL CALL — Bash · 2026-09-30 04:06:47 UTC

```
Final test run, verification and size check:
time ./run_test.sh 2>&1 | tail -1; python3 -c "
import json; nb=json.load(open('code_demo.ipynb'))
print('errors',[o['ename'] for c in nb['cells'] for o in c.get('outputs',[]) if o['output_type']=='error'])
src=''.join(''.join(c['source']) for c in nb['cells'])
print('url exact', 'GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-5/evaluation-7/demo/mini_demo_data.json\"' in src, 'urlopen' in src)"; du -ah --max-depth=2 . | sort -h | tail -8
```

### [60] TOOL RESULT — Bash · 2026-09-30 04:07:13 UTC

```
{"stdout": "1\n\nreal\t0m26.212s\nuser\t0m19.106s\nsys\t0m2.628s\nerrors []\nurl exact True True\n107K\t./figures/F3_generality_scatter.png\n172K\t./figures/F1_k2_forest.png\n249K\t./eval_out.json\n285K\t./code_demo.ipynb\n303K\t./mini_demo_data.json\n393K\t./.repl_agent.ptylog\n1.5M\t./figures\n4.6M\t.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [61] ASSISTANT · 2026-09-30 04:07:33 UTC

```
Nothing in the workspace is over 10 MB, so the manifest needs no entries. Writing the README, manifest and structured output:
```

### [62] TOOL CALL — Bash · 2026-09-30 04:07:33 UTC

```
Write manifest, README and structured output:
cat > .aii/manifest.yaml <<'EOF'
# Nothing heavy in this workspace: every file is text/code or under the 10 MB auto-keep floor
# (largest: mini_demo_data.json ~0.3 MB, code_demo.ipynb ~0.3 MB, figures/ ~1.5 MB).
# The test venv lives outside the workspace (/tmp) and is removed by the pipeline.
entries: []
EOF
cat > README.md <<'EOF'
# K2 demo: host-specific effect or just common words?

This folder is a runnable Colab and Jupyter demo of the evaluation `art_8qkrjl1oVzKi`, "Host-specific or just common words?".

## The question

K2 is a post-confirmation exploratory analysis that ran on CPU only and cost $0. It asks whether the confirmed host-entry effect of the host share `A_cont` is host-specific, or whether it is generic accessibility: the concept simply uses words that are common everywhere.

Partner generality is measured two ways:
- `G_H`: normalised subfield entropy.
- `G_F`: log block frequency.

The analysis compares two quantities:
- **Retention**, `b(M1)/b(M0)`: how much of the `A_cont` effect survives the generality controls.
- **The M3 lift**, `A_lift = ln(A_cont/s_dB)` with the controls.

Both are judged by a decision rule frozen before any K2 coefficient was computed (spec sha256 `866c60a8…`).

## Result

Pooled retention is 0.97 [0.81, 1.10], and the pooled M3 `A_lift|G` IRR/SD is 1.34 [1.23, 1.46]. The verdict is **HOST-SPECIFIC** in every fold and pooled.

## What the notebook does

`code_demo.ipynb` is the original `eval.py` from the artifact, split into cells with explanations between them. The original script is the K2 final-assembly step. It computes no new coefficient. Instead, it:
- reads the K2 result files;
- draws F1 (forest plot), F2 (retention with the design-analysis bands) and F3 (within-FE scatter of generality);
- flattens 297 metrics into `metrics_agg`;
- writes `eval_out.json`.

All 297 metrics reproduce the original `full_eval_out.json` exactly, with a maximum absolute difference of 0.0.

The only changes to the code are these:
- File reads now come from the loaded `data` dict.
- `matplotlib.use("Agg")` is disabled, and `plt.show()` is called before each `plt.close`.
- `ppml._demean` is copied verbatim from the vendored `d2/src/ppml.py` instead of being imported from that path.
- The loguru file sink is dropped.
- `main()` returns `out` so the final cell can show it.

## Layout

| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook, already executed. It runs in about 30 s, most of which is package installs. |
| `mini_demo_data.json` | Every result file `eval.py` reads (`k2_summary`, `k2_power`, `k2_placebo_host`, `audit_k2`, `gates`, `k2_descriptives`, `k2_s2b_diagnostic`, `k2_spec`, the 123-row `k2_rows` table), plus one curated dataset of 99 entry events, 33 per fold, from `partner_generality.parquet`. |
| `build_mini_demo_data.py` | Rebuilds `mini_demo_data.json` from the artifact's workspace. It picks the entry events so that about 16 residual degrees of freedom per fold survive the concept + e + d fixed effects. |
| `run_test.sh` | Runs the notebook in a clean Python 3.12 venv. While the published URL still serves an older file, it points the test copy at an unreachable URL so the local fallback is used, then restores the exact URL. |
| `figures/` | F1–F3 as PNG and PDF, written by the notebook. |
| `eval_out.json` | The evaluation output written by the notebook, in the `exp_eval_sol_out` layout. |

## How to run

- **Colab**: open `code_demo.ipynb` and choose Run all. The data is fetched from the GitHub raw URL.
- **Locally**: run `jupyter nbconvert --to notebook --execute code_demo.ipynb`, or use `./run_test.sh`. The notebook falls back to the local `mini_demo_data.json`.

The config cell has one knob, `N_PG_PER_FOLD`. The bundle holds at most 33 events per fold, while the original run used all 5,086 events (screen 1,740, held-out 1,097, MeSH 2,249). This knob affects only the F3 scatter and the `entry_generality` dataset. Every metric and verdict comes from the complete result files.

## Restoring removed files

No files are marked for deletion (`.aii/manifest.yaml` has no entries), so there is nothing to restore. To regenerate the outputs:
- Run the notebook to rebuild `figures/` and `eval_out.json`.
- Run `python build_mini_demo_data.py <path-to-gen_art_evaluation_7-workspace>` to rebuild `mini_demo_data.json`.
EOF
echo '{"out_expected_files": {"notebook": "code_demo.ipynb", "mini_data_file": "mini_demo_data.json"}}' > .terminal_claude_agent_struct_out.json; cat .terminal_claude_agent_struct_out.json; git status --short | head
```

### [63] TOOL RESULT — Bash · 2026-09-30 04:07:33 UTC

```
{"stdout": "{\"out_expected_files\": {\"notebook\": \"code_demo.ipynb\", \"mini_data_file\": \"mini_demo_data.json\"}}\nfatal: not a git repository (or any parent up to mount point /ai-inventor)\nStopping at filesystem boundary (GIT_DISCOVERY_ACROSS_FILESYSTEM not set).", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [64] ASSISTANT · 2026-09-30 04:07:45 UTC

```
I've built the demo notebook and its data file, and both pass a clean test run. Before the notebook shows the right results in Colab, the publish step has to overwrite the file at the GitHub URL, which currently holds an older demo of this artifact.

**About the GitHub URL:** the `GITHUB_DATA_URL` in the notebook is exactly the required one. It already returns a 2.2 MB file from an earlier demo, in a different format. Run against that file, the notebook fails with `KeyError: 'k2_summary'`. So `run_test.sh` tests a copy pointed at an unreachable URL, which makes it use the local `mini_demo_data.json`, then puts the exact URL back in the executed notebook.

**Test results:**
- The notebook runs with no errors in the clean Python 3.12 venv in about 26–30 s, mostly package installs.
- All 297 headline numbers match the original `full_eval_out.json` exactly (largest difference 0.0).
- The verdict is HOST-SPECIFIC in every fold and pooled. Pooled retention is 0.97 [0.81, 1.10] and the pooled lift is 1.34 [1.23, 1.46].

**What I built:**
- **`code_demo.ipynb`** is `eval.py` split into cells, with an explanation before each one. The code changes are small:
  - Files are read from the loaded `data` instead of disk.
  - Figures display inline.
  - The helper that removes fixed effects (`_demean`) is copied in verbatim instead of imported from the original's `d2/src` folder.
  - The log-file output is dropped.
  - `main()` returns its output so the last cell can show it.
  - A final cell prints a results table and a retention chart.
- **`mini_demo_data.json`** (0.3 MB) holds every result file `eval.py` reads, plus 99 entry events (33 per fold) out of the 5,086 in the full data. `eval.py` computes no new coefficients; it only reads results that were computed earlier. So every metric and verdict comes from the complete results, and only the F3 scatter uses the 99-event subset.

**Choosing the subset:** my first pick of events gave a useless F3 scatter. The fixed effects absorbed almost all of the variation, leaving values around 1e-10. `build_mini_demo_data.py` now picks events that keep about 16 degrees of freedom per fold, and the scatter shows real spread. With only 33 events per fold, the correlations it prints are noisy, and the notebook says so.

**Scaling:** I ran the notebook first with 3 events per fold, then went straight to the full 33. The run takes seconds, so the usual gradual scaling steps weren't needed. The config cell's comment gives the original full-run size.

`README.md` and `.aii/manifest.yaml` are written. Nothing is over the 10 MB limit, so the manifest has no entries. `.terminal_claude_agent_struct_out.json` lists the notebook and the data file.

Files are in the workspace:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `build_mini_demo_data.py`
- `run_test.sh`
- `README.md`
```
