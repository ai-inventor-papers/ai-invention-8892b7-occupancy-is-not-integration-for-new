# gen_demo_art_evaluation_5 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `iter5_6136aaed9367` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_evaluation_5` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-09-30 03:52:33 UTC

```
model: Claude Opus 5.5 | effort: high | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-09-30 03:52:43 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/`:
GOOD: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/file.py`, `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/results/out.json`
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
id: art_FZ2OCJwV6xHs
type: evaluation
title: Do adopters already know the partner words?
summary: >-
  Adopter-level test (screen fold only; mechanism evidence, not confirmation) of the absorptive-capacity mechanism behind
  D2's host-share effect (A_cont, co-primary IRR/SD 1.30). Reproduction gate passed (b_A 4.739106, N 1,544, G 140; exp_7 code
  vendored byte-identical). Cases: W2 author-disjoint newcomer adopters (21,941 pairs; 87% have no prior corpus work, so the
  frozen corpus-primary design keeps exposure-measurable adopters). Controls: incidence-density risk-set samples (same host,
  adoption year, Pset/c-author exclusions), exact-matched on prior-works/team/activity/first-year bins (SMDs <= 0.032). 1,013
  1:1 strata, 422 entries, 109 concepts. mech_spec.json + MDEs frozen before exposure (MDE80 OR 1.5, interaction 1.3, mediation
  share 0.2). OpenAlex: 0 credits (key-wide remaining below the 2,500 reserve), so exposure = corpus works <= e-1 ('corpus-exposure,
  coverage-limited'); no API kappa. RESULTS (conditional logit, concept-bootstrap B=1000): OR(E_any|NEG,prior)=3.09 [2.32,4.28];
  NEG 0.62 [0.49,0.77]; placebo partners 0.72 [0.57,0.90]; partner/NEG 5.02, partner/PLAC 4.53; swapped partner set 1.11 n.s.;
  permutation null centred at 1.00 -> pre-declared reading SUPPORT. Interaction with A_cont null (0.87 [0.70,1.14]). Vocabulary
  class: FOREIGN 2.88 > ADJACENT 1.91 > NATIVE 1.47 (native/foreign 0.51 [0.33,0.89]); origin-companion 3.10 vs non-companion
  1.36 -> adopters already speak c's origin/toolkit vocabulary, not host-native vocabulary (contradicts a literal grafting
  reading at actor level; label not pre-declared). Post-hoc: enrichment survives origin-subfield activity (2.52 [1.91,3.43]).
  Entry-level Gelbach/PPML: M2 (pre-exposed host pool) attenuates b_A by 0.05 [-0.08,0.23], M1 0.01 -> A_cont not reducible
  to pool size; reverse attenuation 0.68. Robust: 1:3 match 2.96, uncapped 1,541 strata 2.62, all field groups >2.7. Audit
  re-derived exposures (100% agreement), OR (statsmodels 3.095, McNemar 3.12) and attenuation (pyfixest 0.052) independently;
  placebos fail. Caveat: prior partner use is also consistent with plain topical proximity to c. Files: eval_out.json, results/*.json,
  figures F1-F5, frames/ (frozen), mech_spec.json.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5
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
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] TOOL CALL — Skill · 2026-09-30 03:52:45 UTC

```
aii-colab
```

### [4] TOOL RESULT — Skill · 2026-09-30 03:52:45 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [5] TOOL CALL — Skill · 2026-09-30 03:52:45 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-09-30 03:52:45 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [7] TOOL CALL — Bash · 2026-09-30 03:52:47 UTC

```
Inspect artifact workspace and own workspace:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; ls -la $W; du -sh $W/* | sort -h | tail -30; wc -l $W/eval.py; ls -la; ls -la .aii
```

### [8] TOOL RESULT — Bash · 2026-09-30 03:52:53 UTC

```
{"stdout": "total 17795\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 .\ndrwxrwxrwx  7 aii-agent aii-agent 2022069 Sep 29 06:27 ..\ndrwxrwxrwx  2 aii-agent aii-agent   71100 Sep 29 07:22 .aii\n-rw-rw-rw-  1 aii-agent aii-agent      54 Sep 29 06:28 .aii_claude_session.json\n-rw-rw-rw-  1 aii-agent aii-agent    5713 Sep 29 07:22 .aii_worker_result.json\n-rw-rw-rw-  1 aii-agent aii-agent  891291 Sep 29 07:22 .repl_agent.ptylog\n-rw-rw-rw-  1 aii-agent aii-agent    2780 Sep 29 07:18 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   13596 Sep 29 07:20 README.md\ndrwxrwxrwx  2 aii-agent aii-agent       1 Sep 29 06:29 api_cache\n-rw-rw-rw-  1 aii-agent aii-agent    8484 Sep 29 07:16 audit_rederive.py\n-rw-rw-rw-  1 aii-agent aii-agent   44704 Sep 29 07:00 eval.py\n-rw-rw-rw-  1 aii-agent aii-agent 2341086 Sep 29 07:10 eval_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1048354 Sep 29 07:09 figures\ndrwxrwxrwx  2 aii-agent aii-agent 2000133 Sep 29 06:47 frames\n-rw-rw-rw-  1 aii-agent aii-agent 2645814 Sep 29 07:14 full_eval_out.json\ndrwxrwxrwx  2 aii-agent aii-agent 1006764 Sep 29 07:16 logs\n-rw-rw-rw-  1 aii-agent aii-agent     907 Sep 29 07:00 make_variants.py\n-rw-rw-rw-  1 aii-agent aii-agent   12304 Sep 29 06:47 mech_spec.json\n-rw-rw-rw-  1 aii-agent aii-agent      81 Sep 29 06:47 mech_spec.sha256\n-rw-rw-rw-  1 aii-agent aii-agent    7876 Sep 29 06:53 mech_spec_power.json\n-rw-rw-rw-  1 aii-agent aii-agent   32655 Sep 29 07:14 mini_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent   32655 Sep 29 07:14 preview_eval_out.json\n-rw-rw-rw-  1 aii-agent aii-agent    2039 Sep 29 07:15 pyproject.toml\n-rw-rw-rw-  1 aii-agent aii-agent    7567 Sep 29 07:18 reproducibility.md\n-rw-rw-rw-  1 aii-agent aii-agent    1287 Sep 29 07:15 requirements.lock.txt\ndrwxrwxrwx  3 aii-agent aii-agent 2000702 Sep 29 07:17 results\ndrwxrwxrwx  2 aii-agent aii-agent       1 Sep 29 06:31 sealed\ndrwxrwxrwx  2 aii-agent aii-agent 1007543 Sep 29 09:04 src\ndrwxrwxrwx  2 aii-agent aii-agent 1005230 Sep 29 09:04 vendor\n512\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/api_cache\n512\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec.sha256\n512\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/sealed\n1.0K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/make_variants.py\n1.5K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/requirements.lock.txt\n2.0K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/pyproject.toml\n7.5K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/reproducibility.md\n8.0K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec_power.json\n8.5K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/audit_rederive.py\n13K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mech_spec.json\n14K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/README.md\n32K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/mini_eval_out.json\n32K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/preview_eval_out.json\n44K\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/eval.py\n1.1M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/logs\n1.1M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src\n1.1M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/vendor\n1.5M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/figures\n2.3M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/eval_out.json\n2.6M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/full_eval_out.json\n3.3M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/frames\n11M\t/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results\n776 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/eval.py\ntotal 2963\ndrwxrwxrwx 3 aii-agent aii-agent 1002901 Sep 30 03:52 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000316 Sep 30 03:51 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:51 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Sep 30 03:52 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   29662 Sep 30 03:52 .repl_agent.ptylog\ntotal 980\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:51 .\ndrwxrwxrwx 3 aii-agent aii-agent 1002901 Sep 30 03:52 ..", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [9] TOOL CALL — Read · 2026-09-30 03:52:57 UTC

```
/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/eval.py
```

### [10] TOOL RESULT — Read · 2026-09-30 03:52:58 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [11] TOOL CALL — Bash · 2026-09-30 03:52:57 UTC

```
List source, vendor, frames, results:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; ls -la $W/src $W/vendor $W/frames $W/results $W/results/* $W/figures | head -80; cat $W/pyproject.toml; cat $W/make_variants.py
```

### [12] TOOL RESULT — Bash · 2026-09-30 03:52:57 UTC

```
{"stdout": "-rw-rw-rw- 1 aii-agent aii-agent     333 Sep 29 06:54 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/api_results.json\n-rw-rw-rw- 1 aii-agent aii-agent     900 Sep 29 07:17 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/audit_rederive.json\n-rw-rw-rw- 1 aii-agent aii-agent    8889 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/enrichment.json\n-rw-rw-rw- 1 aii-agent aii-agent  199924 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/exposures_expanded.parquet\n-rw-rw-rw- 1 aii-agent aii-agent  149691 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/exposures_primary.parquet\n-rw-rw-rw- 1 aii-agent aii-agent    2073 Sep 29 06:47 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/frame_summary.json\n-rw-rw-rw- 1 aii-agent aii-agent     295 Sep 29 06:45 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/gate.json\n-rw-rw-rw- 1 aii-agent aii-agent    7002 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/interaction.json\n-rw-rw-rw- 1 aii-agent aii-agent  146545 Sep 29 06:29 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/main_population_hydrated.json\n-rw-rw-rw- 1 aii-agent aii-agent     525 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/match_balance.json\n-rw-rw-rw- 1 aii-agent aii-agent  121081 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/mechanism_results.json\n-rw-rw-rw- 1 aii-agent aii-agent   54123 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/mediation.json\n-rw-rw-rw- 1 aii-agent aii-agent    6378 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/model_terms.csv\n-rw-rw-rw- 1 aii-agent aii-agent    4920 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/permutation.json\n-rw-rw-rw- 1 aii-agent aii-agent    7876 Sep 29 06:53 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/power.json\n-rw-rw-rw- 1 aii-agent aii-agent    1606 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/ratios.json\n-rw-rw-rw- 1 aii-agent aii-agent   24132 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/supplementary.json\n-rw-rw-rw- 1 aii-agent aii-agent    3857 Sep 29 07:10 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/vocab_class.json\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/figures:\ntotal 3465\ndrwxrwxrwx  2 aii-agent aii-agent 1048354 Sep 29 07:09 .\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   23245 Sep 29 07:10 F1_forest_ORs.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  110912 Sep 29 07:10 F1_forest_ORs.png\n-rw-rw-rw-  1 aii-agent aii-agent   16202 Sep 29 07:10 F2_OR_by_Acont_tercile.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   48262 Sep 29 07:10 F2_OR_by_Acont_tercile.png\n-rw-rw-rw-  1 aii-agent aii-agent   15194 Sep 29 07:10 F3_exposure_prevalence.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   58838 Sep 29 07:10 F3_exposure_prevalence.png\n-rw-rw-rw-  1 aii-agent aii-agent   18569 Sep 29 07:10 F4_attenuation_bootstrap.pdf\n-rw-rw-rw-  1 aii-agent aii-agent   44551 Sep 29 07:10 F4_attenuation_bootstrap.png\n-rw-rw-rw-  1 aii-agent aii-agent   22740 Sep 29 07:10 F5_power_curves.pdf\n-rw-rw-rw-  1 aii-agent aii-agent  136639 Sep 29 07:10 F5_power_curves.png\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/frames:\ntotal 5276\ndrwxrwxrwx  2 aii-agent aii-agent 2000133 Sep 29 06:47 .\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   25636 Sep 29 06:47 api_jobs.parquet\n-rw-rw-rw-  1 aii-agent aii-agent    8699 Sep 29 06:47 api_jobs_key.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  263786 Sep 29 06:46 cases_all.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  392601 Sep 29 06:46 entries.parquet\n-rw-rw-rw-  1 aii-agent aii-agent   43937 Sep 29 06:46 risk_balance_pre.parquet\n-rw-rw-rw-  1 aii-agent aii-agent   59323 Sep 29 06:47 risk_balance_pre_expanded.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  102059 Sep 29 06:46 strata_long.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  140223 Sep 29 06:47 strata_long_expanded.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  362093 Sep 29 06:46 targets.parquet\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results:\ntotal 6591\ndrwxrwxrwx  3 aii-agent aii-agent 2000702 Sep 29 07:17 .\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent     333 Sep 29 06:54 api_results.json\n-rw-rw-rw-  1 aii-agent aii-agent     900 Sep 29 07:17 audit_rederive.json\ndrwxrwxrwx  2 aii-agent aii-agent 2000632 Sep 29 09:04 cache\n-rw-rw-rw-  1 aii-agent aii-agent    8889 Sep 29 07:10 enrichment.json\n-rw-rw-rw-  1 aii-agent aii-agent  199924 Sep 29 07:10 exposures_expanded.parquet\n-rw-rw-rw-  1 aii-agent aii-agent  149691 Sep 29 07:10 exposures_primary.parquet\n-rw-rw-rw-  1 aii-agent aii-agent    2073 Sep 29 06:47 frame_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent     295 Sep 29 06:45 gate.json\n-rw-rw-rw-  1 aii-agent aii-agent    7002 Sep 29 07:10 interaction.json\n-rw-rw-rw-  1 aii-agent aii-agent  146545 Sep 29 06:29 main_population_hydrated.json\n-rw-rw-rw-  1 aii-agent aii-agent     525 Sep 29 07:10 match_balance.json\n-rw-rw-rw-  1 aii-agent aii-agent  121081 Sep 29 07:10 mechanism_results.json\n-rw-rw-rw-  1 aii-agent aii-agent   54123 Sep 29 07:10 mediation.json\n-rw-rw-rw-  1 aii-agent aii-agent    6378 Sep 29 07:10 model_terms.csv\n-rw-rw-rw-  1 aii-agent aii-agent    4920 Sep 29 07:10 permutation.json\n-rw-rw-rw-  1 aii-agent aii-agent    7876 Sep 29 06:53 power.json\n-rw-rw-rw-  1 aii-agent aii-agent    1606 Sep 29 07:10 ratios.json\n-rw-rw-rw-  1 aii-agent aii-agent   24132 Sep 29 07:10 supplementary.json\n-rw-rw-rw-  1 aii-agent aii-agent    3857 Sep 29 07:10 vocab_class.json\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/results/cache:\ntotal 10384\ndrwxrwxrwx 2 aii-agent aii-agent 2000632 Sep 29 09:04 .\ndrwxrwxrwx 3 aii-agent aii-agent 2000702 Sep 29 07:17 ..\n-rw-rw-rw- 1 aii-agent aii-agent 6630760 Sep 29 06:32 author_raw_ids.npy\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src:\ntotal 3017\n[project]\nname = \"d2-adopter-mechanism\"\nversion = \"0.1.0\"\ndescription = \"Adopter-level absorptive-capacity case-control test of the D2 host-share effect (iteration 4)\"\nrequires-python = \">=3.12,<3.13\"\ndependencies = [\n    \"aiohappyeyeballs==2.7.1\",\n    \"aiohttp==3.14.3\",\n    \"aiosignal==1.4.0\",\n    \"asttokens==3.0.2\",\n    \"attrs==26.1.0\",\n    \"babel==2.18.0\",\n    \"cffi==2.1.1\",\n    \"click==8.5.0\",\n    \"cloudpickle==3.1.2\",\n    \"contourpy==1.4.0\",\n    \"cycler==0.12.1\",\n    \"executing==2.2.1\",\n    \"faicons==0.2.2\",\n    \"fonttools==4.66.0\",\n    \"formulaic==1.2.2\",\n    \"frozenlist==1.8.0\",\n    \"great-tables==1.0.0\",\n    \"htmltools==0.7.0\",\n    \"idna==3.20\",\n    \"importlib-metadata==9.0.1\",\n    \"importlib-resources==7.1.0\",\n    \"iniconfig==2.3.0\",\n    \"interface-meta==2.0.1\",\n    \"ipython==9.17.1\",\n    \"ipython-pygments-lexers==1.1.1\",\n    \"jedi==0.20.0\",\n    \"joblib==1.6.0\",\n    \"kiwisolver==1.5.1\",\n    \"loguru==0.7.3\",\n    \"lxml==6.1.3\",\n    \"maketables==0.1.8\",\n    \"matplotlib==3.11.2\",\n    \"matplotlib-inline==0.2.2\",\n    \"multidict==6.9.1\",\n    \"multimark==0.3.2\",\n    \"narwhals==2.26.0\",\n    \"nokap==0.1.0\",\n    \"numpy==2.5.3\",\n    \"orjson==3.12.0\",\n    \"packaging==26.3\",\n    \"pandas==3.0.6\",\n    \"parso==0.8.7\",\n    \"patsy==1.0.3\",\n    \"pexpect==4.9.0\",\n    \"pillow==12.3.0\",\n    \"pluggy==1.6.0\",\n    \"prompt-toolkit==3.0.53\",\n    \"propcache==0.5.4\",\n    \"psutil==7.2.2\",\n    \"ptyprocess==0.7.0\",\n    \"pure-eval==0.2.4\",\n    \"pyarrow==25.0.1\",\n    \"pycparser==3.0\",\n    \"pyfixest==0.60.0\",\n    \"pygments==2.21.0\",\n    \"pyparsing==3.3.3\",\n    \"pytest==9.1.1\",\n    \"python-dateutil==2.9.0.post0\",\n    \"python-docx==1.2.0\",\n    \"pyyaml==6.0.3\",\n    \"scikit-learn==1.9.1\",\n    \"scipy==1.18.1\",\n    \"seaborn==0.13.2\",\n    \"six==1.17.0\",\n    \"stack-data==0.6.3\",\n    \"statsmodels==0.15.0\",\n    \"tabulate==0.10.0\",\n    \"threadpoolctl==3.7.0\",\n    \"tqdm==4.70.1\",\n    \"traitlets==5.16.1\",\n    \"typing-extensions==4.16.0\",\n    \"wcwidth==0.9.1\",\n    \"websockets==17.1\",\n    \"wrapt==2.5.0\",\n    \"yarl==1.25.1\",\n    \"zipp==4.1.0\",\n]\n#!/usr/bin/env python3\n\"\"\"Write mini_eval_out.json (first 3 examples per dataset) and preview_eval_out.json (mini + strings cut to 200 chars).\"\"\"\nimport json\nfrom pathlib import Path\n\nWS = Path(__file__).resolve().parent\n\n\ndef trunc(o):\n    if isinstance(o, str):\n        return o[:200]\n    if isinstance(o, list):\n        return [trunc(x) for x in o]\n    if isinstance(o, dict):\n        return {k: trunc(v) for k, v in o.items()}\n    return o\n\n\ndef main() -> None:\n    full = json.loads((WS / \"eval_out.json\").read_text())\n    mini = dict(full)\n    mini[\"datasets\"] = [{\"dataset\": d[\"dataset\"], \"examples\": d[\"examples\"][:3]} for d in full[\"datasets\"]]\n    (WS / \"mini_eval_out.json\").write_text(json.dumps(mini, indent=1))\n    (WS / \"preview_eval_out.json\").write_text(json.dumps(trunc(mini), indent=1))\n    print(\"wrote mini_eval_out.json, preview_eval_out.json\")\n\n\nif __name__ == \"__main__\":\n    main()", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-09-30 03:53:01 UTC

```
Inspect src modules and preview output:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; ls -la $W/src $W/vendor; wc -l $W/src/*.py; head -c 3000 $W/preview_eval_out.json; python3 -c "
import json;d=json.load(open('$W/preview_eval_out.json'));print(d['datasets'][0]['examples'][0]);print(d['datasets'][1]['examples'][0]); print(len(d['metrics_agg']))"
```

### [14] TOOL RESULT — Bash · 2026-09-30 03:53:01 UTC

```
{"stdout": "/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src:\ntotal 3017\ndrwxrwxrwx  2 aii-agent aii-agent 1007543 Sep 29 09:04 .\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent   20189 Sep 29 06:59 analysis.py\n-rw-rw-rw-  1 aii-agent aii-agent    8860 Sep 29 06:40 api_pull.py\n-rw-rw-rw-  1 aii-agent aii-agent    7042 Sep 29 06:59 figs.py\n-rw-rw-rw-  1 aii-agent aii-agent   26758 Sep 29 06:41 frame.py\n-rw-rw-rw-  1 aii-agent aii-agent    3768 Sep 29 06:31 mech_common.py\n-rw-rw-rw-  1 aii-agent aii-agent    5973 Sep 29 06:40 power_sim.py\n-rw-rw-rw-  1 aii-agent aii-agent    4653 Sep 29 06:39 stats_core.py\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/vendor:\ntotal 2991\ndrwxrwxrwx  2 aii-agent aii-agent 1005230 Sep 29 09:04 .\ndrwxrwxrwx 11 aii-agent aii-agent 2001479 Sep 29 09:04 ..\n-rw-rw-rw-  1 aii-agent aii-agent     459 Sep 29 06:29 SHA256SUMS\n-rw-rw-rw-  1 aii-agent aii-agent    7559 Sep 29 06:29 config.py\n-rw-rw-rw-  1 aii-agent aii-agent   11916 Sep 29 06:29 features.py\n-rw-rw-rw-  1 aii-agent aii-agent   11221 Sep 29 06:29 io_load.py\n-rw-rw-rw-  1 aii-agent aii-agent   12069 Sep 29 06:29 models.py\n-rw-rw-rw-  1 aii-agent aii-agent    5326 Sep 29 06:29 outcomes.py\n-rw-rw-rw-  1 aii-agent aii-agent    5013 Sep 29 06:29 ppml.py\n  420 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/analysis.py\n  201 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/api_pull.py\n  156 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/figs.py\n  521 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/frame.py\n  110 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/mech_common.py\n  138 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/power_sim.py\n  121 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5/src/stats_core.py\n 1667 total\n{\n  \"metadata\": {\n    \"evaluation_name\": \"adopter-level absorptive-capacity test of the D2 host-share effect\",\n    \"label\": \"screen-fold mechanism evidence, not confirmation\",\n    \"exposure_label\": \"corpus-exposure, coverage-limited\",\n    \"reading\": {\n      \"verdict\": \"SUPPORT\",\n      \"interaction\": \"null: enrichment uniform across A_cont\",\n      \"mediation\": \"A_cont is not reducible to pool size (M2) [lower bound under mediator noise]\",\n      \"vocabulary\": \"FOREIGN > NATIVE (CI excludes 0): origin-vocabulary / boundary-spanner reading - NOT a pre-declared label, reported as-is; contradicts the grafting reading at the adopter level\",\n      \"MDE80_primary_at_p0\": {\n        \"p0_observed\": 0.6080947680157947,\n        \"grid_point\": 0.6,\n        \"MDE80\": 1.5\n      },\n      \"criteria\": {\n        \"primary_CI_excludes_1_above\": true,\n        \"ratio_neg_CI_excludes_1_above\": true,\n        \"ratio_plac_CI_excludes_1_above\": true,\n        \"OR_plac_significant\": true,\n        \"OR_neg_significant\": true\n      },\n      \"label\": \"screen-fold mechanism evidence, not confirmation\",\n      \"exposure_label\": \"corpus-exposure, coverage-limited\"\n    },\n    \"mech_spec_sha256\": \"96e697c6970be67be182841fd76eb7e2a583e675eef09d7c482ddbce1f93c293\",\n    \"depends_on\": [\n      \"art_2Cd2JJypeGuA\",\n      \"art_eR1Z7fMlOcxs\"\n    ],\n    \"notes\": \"metrics_agg keys: m<model>_<term>_OR / _OR_ci_lo/_hi (concept-cluster bootstrap) / _p_boot / _p_crv; ratio_*; med_* (entry-level PPML attenuation); MDE80_*; sup_*; api_*\"\n  },\n  \"metrics_agg\": {\n    \"n_cases\": 1013.0,\n    \"n_controls\": 1013.0,\n    \"n_strata\": 1013.0,\n    \"n_concepts\": 109.0,\n    \"n_entries\": 422.0,\n    \"prev_case_E_any\": 0.7877591312931885,\n    \"prev_control_E_any\": 0.6080947680157947,\n    \"prev_case_E_neg\": 0.1964461994076999,\n    \"prev_control_E_neg\": 0.2754195459032576,\n    \"prev_case_E_plac\": 0.3425468904244817,\n    \"prev_control_E_plac\": 0.39486673247778875,\n    \"prev_case_E_nat\": 0.14313919052319843,\n    \"prev_control_E_nat\": 0.11056268509378085,\n    \"prev_case_E_adj\": 0.4846989141164857,\n    \"prev_control_E_adj\": 0.36623889437314905,\n    \"prev_case_E_for\": 0.5567620927936822,\n    \"prev_control_E_for\": 0.36327739387956565,\n    \"prev_case_E_unprof\": 0.04244817374136229,\n    \"prev_control_E_unprof\": 0.013820335636722606,\n    \"prev_case_E_comp\": 0.7186574531095755,\n    \"prev_control_E_comp\": 0.527147087857848,\n    \"prev_case_E_noncomp\": 0.25765054294175715,\n    \"prev_control_E_noncomp\": 0.20533070088845015,\n    \"prev_case_E_swap\": 0.543928923988154,\n    \"prev_control_E_swap\": 0.5241855873642646,\n    \"prev_case_E_any_incl_c\": 0.7877591312931885,\n    \"prev_control_E_any_incl_c\": 0.6080947680157947,\n    \"mean_case_E_w\": 0.19007583641112707,\n    \"mean_control_E_w\": 0.11530482314689493,\n    \"discordant_case_only\": 268.0,\n    \"discordant_control_only\": 86.0,\n    \"discordant_pairs\": 354.0,\n    \"m1_E_any_OR\": 3.1405163801505096,\n    \"m1_E_any_OR_ci_lo\": 2.3661825796818037,\n    \"m1_E_any_OR_ci_hi\": 4.294801107331676,\n    \"m1_E_an{'input': '{\"entry_id\": \"c_007a7950eb4d|1312|2010\", \"A_tercile\": 3, \"stratum\": 0, \"d\": 1312, \"e\": 2010, \"adoption_year\": 2011, \"author\": \"A5080878843\"}', 'output': '1', 'metadata_role': 'case', 'metadata_concept_id': 'c_007a7950eb4d', 'metadata_field_group': 'other', 'metadata_relax_level': 0, 'metadata_exposure_source': 'corpus (coverage-limited)', 'eval_E_any': 0.0, 'eval_E_w': 0.0, 'eval_E_neg': 0.0, 'eval_E_plac': 0.0, 'eval_E_nat': 0.0, 'eval_E_adj': 0.0, 'eval_E_for': 0.0, 'eval_E_unprof': 0.0, 'eval_E_comp': 0.0, 'eval_log1p_prior_corpus': 0.6931471805599453, 'eval_A_cont': 0.052282466177153444}\n{'input': '{\"entry_id\": \"c_9cceb3c510be|1312|2019\", \"concept_id\": \"c_9cceb3c510be\", \"d\": 1312, \"e\": 2019, \"A_tercile\": 1}', 'output': '0', 'metadata_n_entry_papers': 1, 'eval_A_cont': 0.006534156814543768, 'eval_CT': 0.7142857142857143, 'eval_M2': 5.176149732573829, 'eval_M2_share': 0.03542673107890499, 'eval_M2_native': 0.0, 'eval_M2_adjacent': 0.0, 'eval_M1': 4.19476071177253, 'eval_n_host_authors_pre': 4968.0, 'eval_Y_strict': 0.0}\n535", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [15] TOOL CALL — Bash · 2026-09-30 03:53:03 UTC

```
Read analysis, stats_core, mech_common modules:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; cat $W/src/analysis.py $W/src/stats_core.py $W/src/mech_common.py
```

### [16] TOOL RESULT — Bash · 2026-09-30 03:53:03 UTC

```
{"stdout": "\"\"\"STEP 4: exposures and all metrics (M-i enrichment, M-ii interaction, M-iii vocabulary class, M-iv mediation,\nbalance, placebo/sanity, supplementary). Runs only after the mech_spec hash check in eval.py.\"\"\"\nfrom __future__ import annotations\n\nimport multiprocessing as mp\nimport warnings\nfrom concurrent.futures import ProcessPoolExecutor\n\nimport numpy as np\nimport pandas as pd\nfrom loguru import logger\nfrom scipy import stats\n\nimport mech_common... [truncated, 30367 chars total]
```

### [17] ASSISTANT · 2026-09-30 03:53:25 UTC

```
Reading done; the notebook will re-run the adopter-level matched-pair analysis stage on a 100-row subset of the frozen exposure frame. Checking the exposure frame's columns next.
```

### [18] TOOL CALL — Bash · 2026-09-30 03:53:25 UTC

```
Inspect exposures frame columns and power file:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; cd $W && ls .venv 2>/dev/null | head -2; python3 -c "
import pandas as pd
L=pd.read_parquet('results/exposures_primary.parquet')
print(L.shape); print(L.dtypes.to_string()); print(L.role.value_counts()); print(L.head(3).T.to_string())
D=L[L.role.isin(['case','control'])]
print(D.stratum.nunique(), D.has_plac_stratum.mean(), D.A_tercile.value_counts(), D.field_group.value_counts())
"; cat results/gate.json; python3 -c "
import json;p=json.load(open('$W/mech_spec_power.json'));print(p['pairs']['MDE80']); print(p['pairs'].keys())"
```

### [19] TOOL RESULT — Bash · 2026-09-30 03:53:27 UTC

```
{"stdout": "(3750, 46)\nstratum                 int64\nentry_id               object\nconcept_id             object\nd                       int64\ne                       int64\nY                       int64\nA_tercile               int64\nA_cont                float64\nfield_group            object\nsingle_paper_entry       bool\nrelax                   int64\nwidened                  bool\nau                      int64\ncase                    int64\nrole                   object\nn_prior_corpus          int64\nfirst_year              int32\nact                     int64\nteam_index            float64\nraw_author_id           int64\nteam_bin                int64\nact_bin                 int64\nfy_bin                  int64\nprior_bin               int64\nE_any                   int64\nE_w                   float64\nE_nat                   int64\nE_adj                   int64\nE_for                   int64\nE_unprof                int64\nE_comp                  int64\nE_noncomp               int64\nE_neg                   int64\nE_neg_w               float64\nE_plac                  int64\nE_swap                  int64\nhas_plac                int64\nE_any_incl_c            int64\nn_prior_used            int64\nn_target_works          int64\ncluster                object\nlp                    float64\nzA                    float64\nE_any_x_zA            float64\nhas_plac_stratum        int64\nE_origin                int64\nrole\ncase        1013\ncontrol     1013\nreserve1     903\nreserve2     821\nName: count, dtype: int64\n                                           0                         1                         2\nstratum                                    0                         0                         0\nentry_id            c_007a7950eb4d|1312|2010  c_007a7950eb4d|1312|2010  c_007a7950eb4d|1312|2010\nconcept_id                    c_007a7950eb4d            c_007a7950eb4d            c_007a7950eb4d\nd                                       1312                      1312                      1312\ne                                       2010                      2010                      2010\nY                                       2011                      2011                      2011\nA_tercile                                  3                         3                         3\nA_cont                              0.052282                  0.052282                  0.052282\nfield_group                            other                     other                     other\nsingle_paper_entry                      True                      True                      True\nrelax                                      0                         0                         0\nwidened                                False                     False                     False\nau                                    519780                    747712                    311008\ncase                                       1                         0                         0\nrole                                    case                   control                  reserve1\nn_prior_corpus                             1                         1                         1\nfirst_year                              2006                      2007                      2007\nact                                        1                         1                         1\nteam_index                               8.0                       6.0                       9.0\nraw_author_id                     5080878843                5108194775                5048324575\nteam_bin                                   2                         2                         2\nact_bin                                    0                         0                         0\nfy_bin                                     1                         1                         1\nprior_bin                                  1                         1                         1\nE_any                                      0                         0                         1\nE_w                                      0.0                       0.0                  0.083333\nE_nat                                      0                         0                         0\nE_adj                                      0                         0                         0\nE_for                                      0                         0                         1\nE_unprof                                   0                         0                         0\nE_comp                                     0                         0                         1\nE_noncomp                                  0                         0                         0\nE_neg                                      0                         0                         1\nE_neg_w                                  0.0                       0.0                       0.1\nE_plac                                     0                         0                         0\nE_swap                                     0                         0                         0\nhas_plac                                   1                         1                         1\nE_any_incl_c                               0                         0                         1\nn_prior_used                               1                         1                         1\nn_target_works                             0                         0                         1\ncluster                       c_007a7950eb4d            c_007a7950eb4d            c_007a7950eb4d\nlp                                  0.693147                  0.693147                  0.693147\nzA                                  0.115154                  0.115154                  0.115154\nE_any_x_zA                               0.0                       0.0                  0.115154\nhas_plac_stratum                           1                         1                         1\nE_origin                                   0                         0                         0\n1013 0.9644619940769991 A_tercile\n3    1322\n2     476\n1     228\nName: count, dtype: int64 field_group\nother            940\nCS               702\nPhysics/Astro    384\nName: count, dtype: int64\n{\n \"b_A\": 4.739105939721475,\n \"N\": 1544,\n \"G\": 140,\n \"irr_sd\": 1.300076888024346,\n \"ci_irr_sd\": [\n  1.1639421314281162,\n  1.452133975682496\n ],\n \"p\": 6.434696662407287e-06,\n \"target\": {\n  \"b_A\": 4.7391,\n  \"N\": 1544,\n  \"G\": 140\n },\n \"pass\": true,\n \"vendor_sha256_ok\": true,\n \"n_sealed_ids\": 119\n}{'OR_p0_0.1': 1.5, 'inter_ratio_p0_0.1': 1.5, 'OR_p0_0.25': 1.5, 'inter_ratio_p0_0.25': 1.3, 'OR_p0_0.4': 1.5, 'inter_ratio_p0_0.4': 1.3, 'OR_p0_0.6': 1.5, 'inter_ratio_p0_0.6': 1.3}\ndict_keys(['grid', 'reps', 'icc', 'n_pairs', 'n_concepts', 'MDE80', 'tercile'])", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [20] TOOL CALL — Bash · 2026-09-30 03:53:41 UTC

```
Inspect balance frame, mechanism results, entries:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5; cd $W && python3 -c "
import pandas as pd, json
p=pd.read_parquet('frames/risk_balance_pre.parquet'); print(p.shape, p.columns.tolist()); print(p.head(2).T)
m=json.load(open('results/mechanism_results.json')); print(m.keys()); print(json.dumps(m['mediation']['point']['att'])); print(json.dumps(m['mediation']['boot'].get('att_M2')))
print(json.dumps(m['match_balance'])); print(json.dumps(m['permutation'])[:300])
E=pd.read_parquet('frames/entries.parquet'); print(E.A_cont.mean(), E.A_cont.std(), len(E))
print(json.dumps(m['power']['pairs']['tercile'])[:600])
"; cat README.md | head -60
```

### [21] TOOL RESULT — Bash · 2026-09-30 03:53:43 UTC

```
{"stdout": "(1013, 7) ['case_i', 'risk_team_bin_mean', 'risk_act_bin_mean', 'risk_prior_bin_mean', 'risk_log1p_prior_mean', 'risk_fy_bin_mean', 'n_risk']\n                                0           1\ncase_i                   0.000000    1.000000\nrisk_team_bin_mean       1.677249    0.864603\nrisk_act_bin_mean        0.312169    0.640232\nrisk_prior_bin_mean      1.619048    1.783366\nrisk_log1p_prior_mean    1.056814    1.176458\nrisk_fy_bin_mean         1.449735    1.332689\nn_risk                 189.000000  517.000000\ndict_keys(['label', 'exposure_label', 'mech_spec_sha256', 'descriptives', 'enrichment', 'ratios', 'interaction', 'vocab_class', 'checks', 'match_balance', 'attributable_fraction_exposed', 'permutation', 'supplementary', 'mediation', 'power', 'reading'])\n{\"b_base\": 4.7391059397214885, \"att_M2\": 0.051875033323050074, \"b_full_M2\": 4.493264661176972, \"att_M2_split\": -0.3731585059499272, \"b_full_M2_split\": 6.507543631726385, \"att_M1\": 0.013914586843885622, \"b_full_M1\": 4.67316323856086, \"att_M2_share\": -0.008929026546577812, \"b_full_M2_share\": 4.781421542464306, \"reverse_att_M2\": 0.6792247115419506}\n{\"ci95\": [-0.08019738013338919, 0.22503184778717103], \"p_boot_vs0\": 0.448, \"valid\": 1000, \"median\": 0.04618331773592974}\n{\"smd_after_team_bin\": -0.0025387505746984995, \"smd_after_act_bin\": 0.01111645594332484, \"smd_after_fy_bin\": -0.032017660719965424, \"smd_after_prior_bin\": 0.0037478060479285073, \"smd_after_lp\": -0.027949924119715534, \"smd_after_first_year\": -0.015410458493078368, \"smd_before_team_bin\": -0.24262797987981227, \"smd_before_act_bin\": -0.38499050434023213, \"smd_before_prior_bin\": -0.14445106491892495, \"smd_before_lp\": -0.1723842309450537, \"relax_counts\": {\"0\": 909, \"1\": 58, \"2\": 18, \"3\": 25, \"4\": 3}}\n{\"n\": 200, \"mean_logOR\": 0.004408029126612332, \"sd_logOR\": 0.1179070295837742, \"mean_OR\": 1.0044177587779453, \"q025_OR\": 0.8045136293860693, \"q975_OR\": 1.2681039232877647, \"draws\": [-0.06324492268973417, -0.0736940173565731, 0.053031127433566076, -0.08558225757362499, -0.14022928910721233, -0.043903\n0.04590593508922317 0.05537403271640128 1544\n{\"T1\": {\"n_pairs\": 114, \"grid\": [{\"p0\": 0.25, \"OR\": 1.3, \"power\": 0.12}, {\"p0\": 0.25, \"OR\": 1.5, \"power\": 0.28}, {\"p0\": 0.25, \"OR\": 2.0, \"power\": 0.63}, {\"p0\": 0.25, \"OR\": 3.0, \"power\": 0.97}, {\"p0\": 0.4, \"OR\": 1.3, \"power\": 0.2}, {\"p0\": 0.4, \"OR\": 1.5, \"power\": 0.38}, {\"p0\": 0.4, \"OR\": 2.0, \"power\": 0.64}, {\"p0\": 0.4, \"OR\": 3.0, \"power\": 0.98}], \"MDE80_p0_0.25\": 3.0, \"MDE80_p0_0.4\": 3.0}, \"T2\": {\"n_pairs\": 238, \"grid\": [{\"p0\": 0.25, \"OR\": 1.3, \"power\": 0.2}, {\"p0\": 0.25, \"OR\": 1.5, \"power\": 0.48}, {\"p0\": 0.25, \"OR\": 2.0, \"power\": 0.93}, {\"p0\": 0.25, \"OR\": 3.0, \"power\": 0.99}, {\"p0\": 0.4, \"OR\"\n# Do adopters already speak the partner language?\n\nThis is an adopter-level test of the absorptive-capacity mechanism behind the D2 host-share effect. D2's result is A_cont, with a co-primary IRR/SD of 1.30. The test was run on the **screen fold only**, so every number here is *screen-fold mechanism evidence, not confirmation*. Exposure is measured from the 463k-work corpus, and every exposure row is labelled **\"corpus-exposure, coverage-limited\"**. Iteration 4, gen_art_evaluation_5.\n\n## Question\nD2 found that host entries whose partner concepts are already host-native attract more author-disjoint newcomer uptake. If this reflects concept-level absorptive capacity, then the **actors** who adopt c in host d should already have used c's partner vocabulary before the entry year e. They should do so more than matched host authors who did not adopt.\n\n## Design, all frozen and hashed before any exposure was read\n- **Cases.** Newcomer adopters are authors of the W2 = [e+1, e+5] d-papers of c that are counted in `Y_strict`, i.e. papers with no author in Pset(c,e). The source is the 1,544 co-primary entries (140 concepts) of art_2Cd2JJypeGuA. The exp_7 code (`vendor/`) is byte-identical to the original, and its sha256 values are in `vendor/SHA256SUMS`.\n- **Controls.** Controls are drawn by incidence-density sampling from in-corpus authors with a d-paper in the adoption year.\n  - Excluded: Pset(c,e), every c-author 2000-2024, and every adopter of the same entry.\n  - Exact match on four bins: prior-corpus-works bin, team-size bin, host-activity bin and first-year bin. A fixed relaxation order applies when no exact match exists.\n  - Per case: 1 control plus 2 reserves. The reserves are used in the 1:3 supplementary.\n- **Caps.** At most 6 cases per entry and 25 per concept, with a target of 500 per A_cont tercile and a hard cap of 1,500. The result is **1,013 matched strata** from 422 entries and 109 concepts.\n- **Targets.** Partners P are the top-60 partners of each entry. They are classed NATIVE / ADJACENT / FOREIGN / UNPROFILED using G2's cut points (0.3, 0.05), with an origin-companion flag. Two comparison sets sit beside them:\n  - NEG: up to 20 frequency-matched negative-control concepts.\n  - PLAC: up to 20 placebo partners, taken from another concept's entry into the same host with |e'-e| <= 1.\n- **Exposure.** Use of these concepts in the member's corpus works published **<= e-1**, excluding c-papers, under the vendored partner-tag rule.\n- **Freeze.** `mech_spec.json` records the rules, formulas, reading rules and sha256 of every input and frame. Its hash is `mech_spec.sha256` (96e697c6…). `mech_spec_power.json` holds the simulated MDEs and was written before exposure. The analysis refuses to run if either hash differs.\n\n## Headline results\nAll ORs below come from conditional logit with a 95% concept-cluster bootstrap CI (B = 1,000). In the vocabulary tables, \"vs FOREIGN\" means the OR ratio against FOREIGN with its bootstrap CI.\n\n**Primary enrichment (M-i).** This is the primary estimand.\n\n| | Value |\n|---|---|\n| OR(E_any \\| E_neg, prior) | **3.09 [2.32, 4.28]** |\n| Exposure prevalence, cases vs controls | 0.79 vs 0.61 |\n| Discordant pairs | 354 (268 vs 86) |\n| Negative-control OR (NEG) | **0.62 [0.49, 0.77]** |\n| Placebo OR (PLAC) | **0.72 [0.57, 0.90]** |\n| OR_partner / OR_neg | 5.02 [3.45, 7.51] |\n| OR_partner / OR_plac | 4.53 [3.05, 7.21] |\n| Swapped partner set (label shuffle) | 1.11 [0.86, 1.39] |\n| Permutation null | mean OR 1.00 (95% range 0.80-1.27) |\n| LPM check (pyfixest, stratum FE, CRV1 by concept) | +0.50, p 4e-14 |\n| statsmodels ConditionalLogit | identical to within 7e-5 |\n\nMatch balance: every SMD is at most 0.032 after matching; before matching they reach up to 0.38. The attributable fraction among exposed cases is 0.53.\n\n**Pre-declared reading: SUPPORT.** All three SUPPORT criteria are met. Adopters used c's specific partner vocabulary before e, and they are *less* likely than matched host authors to use generic host vocabulary (NEG) or another concept's partner vocabulary (PLAC). The ACTIVITY-ARTEFACT and GENERIC-HOST-VOCABULARY readings are both rejected.\n\n**Interaction with A_cont (M-ii).**\n- OR ratio per SD of A_cont: 0.87 [0.70, 1.14], so **enrichment is uniform across A_cont**. The MDE80 for the ratio is 1.3.\n- Tercile ORs:\n\n| Tercile | n | OR (95% CI) | MDE80 |\n|---|---|---|---|\n| T1 | 114 | 3.55 [1.85, 10.4] | ~3.0 |\n| T2 | 238 | 4.18 [2.26, 8.46] | ~2.0 |\n| T3 | 661 | 2.74 [1.90, 4.16] | ~1.5 |\n\n**Vocabulary class (M-iii).** These readings were not pre-declared as outcomes, and are reported as-is.\n\n| Partner class | OR (95% CI) | vs FOREIGN |\n|---|---|---|\n| NATIVE | 1.47 [1.02, 2.33] | 0.51 [0.33, 0.89] |\n| ADJACENT | 1.91 [1.43, 2.73] | 0.66 [0.47, 0.96] |\n| FOREIGN | 2.88 [2.28, 3.69] | — |", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [22] TOOL CALL — Write · 2026-09-30 03:54:03 UTC

```
File: /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/build_demo_data.py

#!/usr/bin/env python3
"""Build mini_demo_data.json: 50 matched 1:1 strata (100 case/control rows) from the artifact's frozen primary
exposure frame, plus the small frozen inputs eval.py's analyze stage reads (A_cont mean/SD over the 1,544 entries,
pre-match risk-set means, the MDE file, the full-run mediation block) and full-run reference numbers for comparison."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

SRC = Path("/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5")
OUT = Path(__file__).resolve().parent / "mini_demo_data.json"
N_STRATA = 50
SEED = 20260929

L = pd.read_parquet(SRC / "results" / "exposures_primary.parquet")
D = L[L.role.isin(["case", "control"])]
# stratified draw over A_cont terciles (so every tercile is represented), then field groups mix naturally
rng = np.random.default_rng(SEED)
st = D.drop_duplicates("stratum")[["stratum", "A_tercile"]]
quota = {1: 12, 2: 13, 3: 25}
pick = []
for t, q in quota.items():
    pool = st[st.A_tercile == t].stratum.to_numpy()
    pick += rng.choice(pool, q, replace=False).tolist()
S = D[D.stratum.isin(pick)].sort_values(["stratum", "case"], ascending=[True, False])
# columns produced by frame.build (the frozen frame) + analysis.compute_exposures (the corpus-dependent step)
cols = ["stratum", "entry_id", "concept_id", "d", "e", "Y", "A_tercile", "A_cont", "field_group", "single_paper_entry",
        "relax", "widened", "case", "role", "n_prior_corpus", "first_year", "team_bin", "act_bin", "fy_bin", "prior_bin",
        "E_any", "E_w", "E_nat", "E_adj", "E_for", "E_unprof", "E_comp", "E_noncomp", "E_neg", "E_neg_w", "E_plac",
        "E_swap", "has_plac", "E_any_incl_c", "n_prior_used", "n_target_works"]
rows = json.loads(S[cols].to_json(orient="records"))

E = pd.read_parquet(SRC / "frames" / "entries.parquet")
pre = pd.read_parquet(SRC / "frames" / "risk_balance_pre.parquet")
power = json.loads((SRC / "mech_spec_power.json").read_text())
mech = json.loads((SRC / "results" / "mechanism_results.json").read_text())
full = json.loads((SRC / "full_eval_out.json").read_text())
M = full["metrics_agg"]
ref_keys = ["m1_E_any", "m2_E_any", "m2_E_neg", "m3_E_w", "m_plac_E_plac", "m_swap_E_swap", "m_int_E_any_x_zA",
            "m_voc_E_nat", "m_voc_E_adj", "m_voc_E_for", "m_comp_E_comp", "m_comp_E_noncomp"]
ref = {k: {"OR": M.get(f"{k}_OR"), "ci": [M.get(f"{k}_OR_ci_lo"), M.get(f"{k}_OR_ci_hi")]} for k in ref_keys}
for r in ("partner_over_neg", "partner_over_plac", "native_vs_foreign", "companion_vs_noncompanion"):
    ref[f"ratio_{r}"] = {"OR": M.get(f"ratio_{r}"), "ci": [M.get(f"ratio_{r}_ci_lo"), M.get(f"ratio_{r}_ci_hi")]}

out = {
    "metadata": {
        "description": "50 matched 1:1 case-control strata (100 rows) drawn from the 1,013-stratum primary frame of the "
                       "adopter-level absorptive-capacity test, with corpus exposures already computed (the corpus "
                       "itself is not shipped). Stratified by A_cont tercile (12/13/25 strata), seed 20260929.",
        "label": mech["label"], "exposure_label": mech["exposure_label"], "mech_spec_sha256": mech["mech_spec_sha256"],
        "n_rows": len(rows), "n_strata": int(S.stratum.nunique()), "n_concepts": int(S.concept_id.nunique()),
        "full_frame": {"n_strata": int(D.stratum.nunique()), "n_rows": int(len(D))},
    },
    "frozen_inputs": {
        "A_cont_mean_1544_entries": float(E.A_cont.mean()), "A_cont_sd_1544_entries": float(E.A_cont.std()),
        "risk_balance_pre_means": {c: float(pre[c].mean()) for c in pre.columns if c.startswith("risk_")},
        "power": {"pairs": {"MDE80": power["pairs"]["MDE80"], "tercile": power["pairs"]["tercile"]},
                  "mediation": {"MDE80_share": power["mediation"]["MDE80_share"]}},
        "mediation_full_run": {"point": {"att": mech["mediation"]["point"]["att"]},
                               "boot": {"att_M2": mech["mediation"]["boot"]["att_M2"]}},
        "gate": json.loads((SRC / "results" / "gate.json").read_text()),
    },
    "full_run_reference": {"B": 1000, "n_strata": 1013, "reading": mech["reading"], "ORs": ref,
                           "descriptives": {k: M[k] for k in ("prev_case_E_any", "prev_control_E_any",
                                                               "prev_case_E_neg", "prev_control_E_neg",
                                                               "discordant_case_only", "discordant_control_only")},
                           "permutation_mean_OR": M.get("permutation_mean_OR")},
    "examples": rows,
}
OUT.write_text(json.dumps(out, indent=1))
print(f"wrote {OUT.name}: {len(rows)} rows, {S.stratum.nunique()} strata, {S.concept_id.nunique()} concepts, "
      f"{OUT.stat().st_size / 1024:.1f} KB")
print(S.groupby("A_tercile").stratum.nunique().to_dict(), S.field_group.value_counts().to_dict(),
      "has_plac strata", S.groupby("stratum").has_plac.max().sum())
```

### [23] TOOL RESULT — Write · 2026-09-30 03:54:03 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/build_demo_data.py", "content": "#!/usr/bin/env python3\n\"\"\"Build mini_demo_data.json: 50 matched 1:1 strata (100 case/control rows) from the artifact's frozen primary\nexposure frame, plus the small frozen inputs eval.py's analyze stage reads (A_cont mean/SD over the 1,544 entries,\npre-match risk-set means, the MDE file, the full-run mediation block) and full-run reference numbers for comparison.\"\"\"\nimport json\nfrom pathlib import Path\n\nimport numpy as np\nimport pandas as pd\n\nSRC = Path(\"/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_4/gen_art/gen_art_evaluation_5\")\nOUT = Path(__file__).resolve().parent / \"mini_demo_data.json\"\nN_STRATA = 50\nSEED = 20260929\n\nL = pd.read_parquet(SRC / \"results\" / \"exposures_primary.parquet\")\nD = L[L.role.isin([\"case\", \"control\"])]\n# stratified draw over A_cont terciles (so every tercile is represented), then field groups mix naturally\nrng = np.random.default_rng(SEED)\nst = D.drop_duplicates(\"stratum\")[[\"stratum\", \"A_tercile\"]]\nquota = {1: 12, 2: 13, 3: 25}\npick = []\nfor t, q in quota.items():\n    pool = st[st.A_tercile == t].stratum.to_numpy()\n    pick += rng.choice(pool, q, replace=False).tolist()\nS = D[D.stratum.isin(pick)].sort_values([\"stratum\", \"case\"], ascending=[True, False])\n# columns produced by frame.build (the frozen frame) + analysis.compute_exposures (the corpus-dependent step)\ncols = [\"stratum\", \"entry_id\", \"concept_id\", \"d\", \"e\", \"Y\", \"A_tercile\", \"A_cont\", \"field_group\", \"single_paper_entry\",\n        \"relax\", \"widened\", \"case\", \"role\", \"n_prior_corpus\", \"first_year\", \"team_bin\", \"act_bin\", \"fy_bin\", \"prior_bin\",\n        \"E_any\", \"E_w\", \"E_nat\", \"E_adj\", \"E_for\", \"E_unprof\", \"E_comp\", \"E_noncomp\", \"E_neg\", \"E_neg_w\", \"E_plac\",\n        \"E_swap\", \"has_plac\", \"E_any_incl_c\", \"n_prior_used\", \"n_target_works\"]\nrows = json.loads(S[cols].to_json(orient=\"records\"))\n\nE = pd.read_parquet(SRC / \"frames\" / \"entries.parquet\")\npre = pd.read_parquet(SRC / \"frames\" / \"risk_balance_pre.parquet\")\npower = json.loads((SRC / \"mech_spec_power.json\").read_text())\nmech = json.loads((SRC / \"results\" / \"mechanism_results.json\").read_text())\nfull = json.loads((SRC / \"full_eval_out.json\").read_text())\nM = full[\"metrics_agg\"]\nref_keys = [\"m1_E_any\", \"m2_E_any\", \"m2_E_neg\", \"m3_E_w\", \"m_plac_E_plac\", \"m_swap_E_swap\", \"m_int_E_any_x_zA\",\n            \"m_voc_E_nat\", \"m_voc_E_adj\", \"m_voc_E_for\", \"m_comp_E_comp\", \"m_comp_E_noncomp\"]\nref = {k: {\"OR\": M.get(f\"{k}_OR\"), \"ci\": [M.get(f\"{k}_OR_ci_lo\"), M.get(f\"{k}_OR_ci_hi\")]} for k in ref_keys}\nfor r in (\"partner_over_neg\", \"partner_over_plac\", \"native_vs_foreign\", \"companion_vs_noncompanion\"):\n    ref[f\"ratio_{r}\"] = {\"OR\": M.get(f\"ratio_{r}\"), \"ci\": [M.get(f\"ratio_{r}_ci_lo\"), M.get(f\"ratio_{r}_ci_hi\")]}\n\nout = {\n    \"metadata\": {\n        \"description\": \"50 matched 1:1 case-control strata (100 rows) drawn from the 1,013-stratum primary frame of the \"\n                       \"adopter-level absorptive-capacity test, with corpus exposures already computed (the corpus \"\n                       \"itself is not shipped). Stratified by A_cont tercile (12/13/25 strata), seed 20260929.\",\n        \"label\": mech[\"label\"], \"exposure_label\": mech[\"exposure_label\"], \"mech_spec_sha256\": mech[\"mech_spec_sha256\"],\n        \"n_rows\": len(rows), \"n_strata\": int(S.stratum.nunique()), \"n_concepts\": int(S.concept_id.nunique()),\n        \"full_frame\": {\"n_strata\": int(D.stratum.nunique()), \"n_rows\": int(len(D))},\n    },\n    \"frozen_inputs\": {\n        \"A_cont_mean_1544_entries\": float(E.A_cont.mean()), \"A_cont_sd_1544_entries\": float(E.A_cont.std()),\n        \"risk_balance_pre_means\": {c: float(pre[c].mean()) for c in pre.columns if c.startswith(\"risk_\")},\n        \"power\": {\"pairs\": {\"MDE80\": power[\"pairs\"][\"MDE80\"], \"tercile\": power[\"pairs\"][\"tercile\"]},\n                  \"mediation\": {\"MDE80_share\": power[\"mediation\"][\"MDE80_share\"]}},\n        \"mediation_full_run\": {\"point\": {\"att\": mech[\"mediation\"][\"point\"][\"att\"]},\n                               \"boot\": {\"att_M2\": mech[\"mediation\"][\"boot\"][\"att_M2\"]}},\n        \"gate\": json.loads((SRC / \"results\" / \"gate.json\").read_text()),\n    },\n    \"full_run_reference\": {\"B\": 1000, \"n_strata\": 1013, \"reading\": mech[\"reading\"], \"ORs\": ref,\n                           \"descriptives\": {k: M[k] for k in (\"prev_case_E_any\", \"prev_control_E_any\",\n                                                               \"prev_case_E_neg\", \"prev_control_E_neg\",\n                                                               \"discordant_case_only\", \"discordant_control_only\")},\n                           \"permutation_mean_OR\": M.get(\"permutation_mean_OR\")},\n    \"examples\": rows,\n}\nOUT.write_text(json.dumps(out, indent=1))\nprint(f\"wrote {OUT.name}: {len(rows)} rows, {S.stratum.nunique()} strata, {S.concept_id.nunique()} concepts, \"\n      f\"{OUT.stat().st_size / 1024:.1f} KB\")\nprint(S.groupby(\"A_tercile\").stratum.nunique().to_dict(), S.field_group.value_counts().to_dict(),\n      \"has_plac strata\", S.groupby(\"stratum\").has_plac.max().sum())\n", "structuredPatch": [], "originalFile": null, "userModified": false}
```

### [24] TOOL CALL — Bash · 2026-09-30 03:54:07 UTC

```
Build mini demo data file:
python3 build_demo_data.py && python3 -c "
import json;d=json.load(open('mini_demo_data.json'));print(json.dumps(d['full_run_reference'])[:1500])"
```

### [25] TOOL RESULT — Bash · 2026-09-30 03:54:09 UTC

```
{"stdout": "wrote mini_demo_data.json: 100 rows, 50 strata, 37 concepts, 78.6 KB\n{1: 12, 2: 13, 3: 25} {'other': 42, 'CS': 38, 'Physics/Astro': 20} has_plac strata 46\n{\"B\": 1000, \"n_strata\": 1013, \"reading\": {\"verdict\": \"SUPPORT\", \"interaction\": \"null: enrichment uniform across A_cont\", \"mediation\": \"A_cont is not reducible to pool size (M2) [lower bound under mediator noise]\", \"vocabulary\": \"FOREIGN > NATIVE (CI excludes 0): origin-vocabulary / boundary-spanner reading - NOT a pre-declared label, reported as-is; contradicts the grafting reading at the adopter level\", \"MDE80_primary_at_p0\": {\"p0_observed\": 0.6080947680157947, \"grid_point\": 0.6, \"MDE80\": 1.5}, \"criteria\": {\"primary_CI_excludes_1_above\": true, \"ratio_neg_CI_excludes_1_above\": true, \"ratio_plac_CI_excludes_1_above\": true, \"OR_plac_significant\": true, \"OR_neg_significant\": true}, \"label\": \"screen-fold mechanism evidence, not confirmation\", \"exposure_label\": \"corpus-exposure, coverage-limited\"}, \"ORs\": {\"m1_E_any\": {\"OR\": 3.1405163801505096, \"ci\": [2.3661825796818037, 4.294801107331676]}, \"m2_E_any\": {\"OR\": 3.094953030274428, \"ci\": [2.3206549316354717, 4.278592641692452]}, \"m2_E_neg\": {\"OR\": 0.617055902705693, \"ci\": [0.4909739578035307, 0.7708027373076457]}, \"m3_E_w\": {\"OR\": 175.79592679660956, \"ci\": [48.36239318036408, 803.935860658533]}, \"m_plac_E_plac\": {\"OR\": 0.7227395882297841, \"ci\": [0.5747998841473335, 0.9022208004607865]}, \"m_swap_E_swap\": {\"OR\": 1.1109922052436059, \"ci\": [0.8632864180360361, 1.3937477070354867]}, \"m_int_E_any_x_zA\": {\"OR\": 0.8694087063598213, \"ci\": [0.7046821088273688, 1.141427219675185]}, \"m_voc_E_nat\": {\"OR\": 1.4717252217846675, \"ci\": [1.019405925334", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [26] TOOL CALL — Bash · 2026-09-30 03:54:16 UTC

```
Create test venv and dry-run pyfixest resolution:
E=/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4; UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install --dry-run --python $E/bin/python numpy==2.0.2 pandas==2.2.2 scipy==1.16.3 scikit-learn==1.6.1 matplotlib==3.10.0 statsmodels==0.14.6 pyfixest loguru 2>&1 | tail -40
```

### [27] TOOL RESULT — Bash · 2026-09-30 03:54:20 UTC

```
{"stdout": "Would install 39 packages\n + click==8.5.0\n + cloudpickle==3.1.2\n + contourpy==1.4.0\n + cycler==0.12.1\n + faicons==0.2.2\n + fonttools==4.66.1\n + formulaic==1.2.2\n + great-tables==1.0.0\n + htmltools==0.7.0\n + importlib-metadata==9.0.1\n + importlib-resources==7.1.0\n + interface-meta==2.0.1\n + joblib==1.6.0\n + kiwisolver==1.5.1\n + loguru==0.7.3\n + lxml==6.1.3\n + maketables==0.1.8\n + matplotlib==3.10.0\n + multimark==0.3.2\n + narwhals==2.26.0\n + nokap==0.1.0\n + numpy==2.0.2\n + pandas==2.2.2\n + patsy==1.0.3\n + pillow==12.3.0\n + pyfixest==0.60.0\n + pyparsing==3.3.3\n + python-docx==1.2.0\n + pytz==2026.4\n + scikit-learn==1.6.1\n + scipy==1.16.3\n + seaborn==0.13.2\n + statsmodels==0.14.6\n + tabulate==0.10.0\n + threadpoolctl==3.7.0\n + tqdm==4.70.1\n + websockets==17.1\n + wrapt==2.5.0\n + zipp==4.1.0", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [28] TOOL CALL — Write · 2026-09-30 03:56:36 UTC

```
File: /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/make_notebook.py

#!/usr/bin/env python3
"""Write code_demo.ipynb (cells below). Re-run after editing a cell; the test harness then executes the notebook."""
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "code_demo.ipynb"
cells = []


def md(s):
    cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")}... [truncated, 37252 chars total]
```

### [29] TOOL RESULT — Write · 2026-09-30 03:56:36 UTC

```
{"type": "create", "filePath": "/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs/make_notebook.py", "content": "#!/usr/bin/env python3\n\"\"\"Write code_demo.ipynb (cells below). Re-run after editing a cell; the test harness then executes the notebook.\"\"\"\nimport json\nfrom pathlib import Path\n\nOUT = Path(__file__).resolve().parent / \"code_demo.ipynb\"\ncells = []\n\n\ndef md(s):\n    cells.append({... [truncated, 39495 chars total]
```

### [30] ASSISTANT · 2026-09-30 03:56:42 UTC

```
I've built the data file (100 rows, 50 strata) and the notebook generator. Now running the first test at minimum config (B=20, 20 permutations).
```

### [31] TOOL CALL — Bash · 2026-09-30 03:56:42 UTC

```
Generate notebook and test-run it in clean venv:
python3 make_notebook.py && E=/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && S=$(date +%s) && $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -30; echo "runtime $(( $(date +%s) - S ))s"
```

### [32] TOOL RESULT — Bash · 2026-09-30 03:58:28 UTC

```
{"stdout": "wrote code_demo.ipynb: 26 cells\n    raise CellExecutionError.from_cell_and_msg(cell, exec_reply_content)\nnbclient.exceptions.CellExecutionError: An error occurred while executing the following cell:\n------------------\nres = {\"label\": LABEL, \"exposure_label\": \"corpus-exposure, coverage-limited\", \"mech_spec_sha256\": data[\"metadata\"][\"mech_spec_sha256\"]}\nfz = data[\"frozen_inputs\"]\nmA, sdA = fz[\"A_cont_mean_1544_entries\"], fz[\"A_cont_sd_1544_entries\"]   # eval.py: E.A_cont.mean(), E.A_cont.std()\npower = fz[\"power\"]                                                       # eval.py: mech_spec_power.json (MDEs, frozen before exposure)\n\nL = pd.DataFrame(data[\"examples\"])                  # replaces: pd.read_parquet(FR / fn) + A.compute_exposures(G, C, L, T)\nL[\"cluster\"] = L.concept_id\nL = add_design(L, sdA, mA)\nL[\"has_plac_stratum\"] = L.groupby(\"stratum\").has_plac.transform(\"max\")\nD = L[L.role.isin([\"case\", \"control\"])].copy()\nprint(D.shape, \"| strata:\", D.stratum.nunique(), \"| concepts:\", D.cluster.nunique(),\n      \"| strata with a placebo entry:\", int(D.drop_duplicates('stratum').has_plac_stratum.sum()))\nD[[\"stratum\", \"role\", \"case\", \"A_tercile\", \"field_group\", \"E_any\", \"E_neg\", \"E_plac\", \"E_nat\", \"E_adj\", \"E_for\", \"lp\"]].head(6)\n------------------\n\n\n\u001b[31m---------------------------------------------------------------------------\u001b[39m\n\u001b[31mKeyError\u001b[39m                                  Traceback (most recent call last)\n\u001b[36mCell\u001b[39m\u001b[36m \u001b[39m\u001b[32mIn[8]\u001b[39m\u001b[32m, line 2\u001b[39m\n\u001b[32m      1\u001b[39m res = {\u001b[33m\"label\"\u001b[39m: LABEL, \u001b[33m\"exposure_label\"\u001b[39m: \u001b[33m\"corpus-exposure, coverage-limited\"\u001b[39m, \u001b[33m\"mech_spec_sha256\"\u001b[39m: data[\u001b[33m\"metadata\"\u001b[39m][\u001b[33m\"mech_spec_sha256\"\u001b[39m]}\n\u001b[32m----> \u001b[39m\u001b[32m2\u001b[39m fz = data[\u001b[33m\"frozen_inputs\"\u001b[39m]\n\u001b[32m      3\u001b[39m mA, sdA = fz[\u001b[33m\"A_cont_mean_1544_entries\"\u001b[39m], fz[\u001b[33m\"A_cont_sd_1544_entries\"\u001b[39m]   \u001b[38;5;66;03m# eval.py: E.A_cont.mean(), E.A_cont.std()\u001b[39;00m\n\u001b[32m      4\u001b[39m power = fz[\u001b[33m\"power\"\u001b[39m]                                                       \u001b[38;5;66;03m# eval.py: mech_spec_power.json (MDEs, frozen before exposure)\u001b[39;00m\n\u001b[32m      5\u001b[39m \n\n\u001b[31mKeyError\u001b[39m: 'frozen_inputs'\n\nruntime 105s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] ASSISTANT · 2026-09-30 03:58:32 UTC

```
The notebook fetched a file that already exists at the GitHub URL, left by an earlier round, and that file has a different structure. Checking it:
```

### [34] TOOL CALL — Bash · 2026-09-30 03:58:32 UTC

```
Fetch the existing remote data file and list sibling workspaces:
curl -s -m 20 "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json" | head -c 1500; echo; cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/ && ls; ls */ | head -30
```

### [35] TOOL RESULT — Bash · 2026-09-30 03:58:32 UTC

```
{"stdout": "{\n \"metadata\": {\n  \"description\": \"100 matched adopter strata (1 newcomer adopter = case, 1 matched control, up to 2 reserve controls) sampled from the 1,013-stratum primary frame of the adopter-level absorptive-capacity evaluation (screen fold; corpus-exposure, coverage-limited). Stratified by A_cont tercile ({1: 30, 2: 30, 3: 40}), seed 20260929.\",\n  \"label\": \"screen-fold mechanism evidence, not confirmation\",\n  \"exposure_label\": \"corpus-exposure, coverage-limited\",\n  \"mech_spec_sha256\": \"96e697c6970be67be182841fd76eb7e2a583e675eef09d7c482ddbce1f93c293\",\n  \"A_cont_mean_1544_entries\": 0.04590593508922317,\n  \"A_cont_sd_1544_entries\": 0.05537403271640128,\n  \"power\": {\n   \"pairs\": {\n    \"MDE80\": {\n     \"OR_p0_0.1\": 1.5,\n     \"inter_ratio_p0_0.1\": 1.5,\n     \"OR_p0_0.25\": 1.5,\n     \"inter_ratio_p0_0.25\": 1.3,\n     \"OR_p0_0.4\": 1.5,\n     \"inter_ratio_p0_0.4\": 1.3,\n     \"OR_p0_0.6\": 1.5,\n     \"inter_ratio_p0_0.6\": 1.3\n    },\n    \"tercile\": {\n     \"T1\": {\n      \"n_pairs\": 114,\n      \"grid\": [\n       {\n        \"p0\": 0.25,\n        \"OR\": 1.3,\n        \"power\": 0.12\n       },\n       {\n        \"p0\": 0.25,\n        \"OR\": 1.5,\n        \"power\": 0.28\n       },\n       {\n        \"p0\": 0.25,\n        \"OR\": 2.0,\n        \"power\": 0.63\n       },\n       {\n        \"p0\": 0.25,\n        \"OR\": 3.0,\n        \"power\": 0.97\n       },\n       {\n        \"p0\": 0.4,\n        \"OR\": 1.3,\n        \"power\": 0.2\n       },\n       {\n        \"p0\": 0.4,\n        \"OR\": 1.5,\n        \"power\": 0.38\n       },\n       {\n        \"p0\":\nart_FZ2OCJwV6xHs\nart_WZ8fbLn79nCq\nart_XGdzjWgi-a88\nart_mu0h0npvNX_u\nart_zw_JJGsUFSnd\nart_FZ2OCJwV6xHs/:\nbuild_demo_data.py\ncode_demo.ipynb\nmake_notebook.py\nmini_demo_data.json\n\nart_WZ8fbLn79nCq/:\nREADME.md\nbuild_mini_data.py\ncode_demo.ipynb\nmini_demo_data.json\n\nart_XGdzjWgi-a88/:\nREADME.md\ncode_demo.ipynb\nmake_mini_demo_data.py\nmini_demo_data.json\n\nart_mu0h0npvNX_u/:\ncode_demo.ipynb\nmini_demo_data.json\nscripts\n\nart_zw_JJGsUFSnd/:\nREADME.md\ncode_demo.ipynb\neval_ws\nmini_demo_data.json", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_4/art_FZ2OCJwV6xHs", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [36] THINKING · 2026-09-30 03:58:44 UTC

```
I'll block only the raw.githubusercontent fetch with a dead proxy while keeping PyPI reachable, so the test uses the local file instead of the stale remote one. I'm also raising B=20 to 100 for this run since the last one spent most of its time on installs.
```

### [37] TOOL CALL — Bash · 2026-09-30 03:58:44 UTC

```
Test notebook with local data fallback:
sed -i 's/^B = 20 /B = 100/; s/^N_PERM = 20 /N_PERM = 50/' make_notebook.py && grep -n "^B = \|^N_PERM" make_notebook.py && python3 make_notebook.py && E=/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && S=$(date +%s) && https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 no_proxy=pypi.org,files.pythonhosted.org NO_PROXY=pypi.org,files.pythonhosted.org $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -30; echo "runtime $(( $(date +%s) - S ))s"
```

### [38] TOOL RESULT — Bash · 2026-09-30 03:59:50 UTC

```
{"stdout": "120:B = 100            # bootstrap reps for the model suite     (original full run: 1000)\n121:N_PERM = 50       # permutation-null draws                 (original full run: 200; --mini: 50)\nwrote code_demo.ipynb: 26 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 187716 bytes to code_demo.ipynb\nruntime 62s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [39] TOOL CALL — Bash · 2026-09-30 03:59:54 UTC

```
Print executed notebook outputs:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code': continue
    for o in c['outputs']:
        if o['output_type']=='stream': print(i, o['text'][-2500:])
        elif o['output_type']=='error': print(i,'ERR',o['ename'],o['evalue'])
        else: print(i, o['output_type'], list(o.get('data',{}).keys()))
"
```

### [40] TOOL RESULT — Bash · 2026-09-30 03:59:54 UTC

```
{"stdout": "7 ['{\\n', ' \"description\": \"50 matched 1:1 case-control strata (100 rows) drawn from the 1,013-stratum primary frame of the adopter-level absorptive-capacity test, with corpus exposures already computed (the corpus itself is not shipped). Stratified by A_cont tercile (12/13/25 strata), seed 20260929.\",\\n', ' \"label\": \"screen-fold mechanism evidence, not confirmation\",\\n', ' \"exposure_label\": \"corpus-exposure, coverage-limited\",\\n', ' \"mech_spec_sha256\": \"96e697c6970be67be182841fd76eb7e2a583e675eef09d7c482ddbce1f93c293\",\\n', ' \"n_rows\": 100,\\n', ' \"n_strata\": 50,\\n', ' \"n_concepts\": 37,\\n', ' \"full_frame\": {\\n', '  \"n_strata\": 1013,\\n', '  \"n_rows\": 2026\\n', ' }\\n', '}\\n', \"rows: 100 | example row: {'stratum': 12, 'entry_id': 'c_029ea7c780b8|2205|2018', 'concept_id': 'c_029ea7c780b8', 'd': 2205, 'e': 2018, 'Y': 2019, 'A_tercile': 1, 'A_cont': 0.0090478021, 'field_group': 'CS', 'single_paper_entry': True, 'relax': 0, 'widened': False, 'case': 1, 'role': 'case', 'n_prior_corpus': 1, 'first_year': 2010, 'team_bin': 1, 'act_bin': 0, 'fy_bin': 1, 'prior_bin': 1, 'E_any': 0, 'E_w': 0.0, 'E_nat': 0, 'E_adj': 0, 'E_for': 0, 'E_unprof': 0, 'E_comp': 0, 'E_noncomp': 0, 'E_neg': 0, 'E_neg_w': 0.0, 'E_plac': 0, 'E_swap': 0, 'has_plac': 1, 'E_any_incl_c': 0, 'n_prior_used': 1, 'n_target_works': 0}\\n\"]\n15 ['(100, 41) | strata: 50 | concepts: 37 | strata with a placebo entry: 46\\n']\n15 execute_result ['text/html', 'text/plain']\n17 ['03:59:45|INFO   |primary model suite + bootstrap B=100 in 1s\\n']\n17 ['{\\n', ' \"n_strata\": 50,\\n', ' \"prev_case_E_any\": 0.84,\\n', ' \"prev_control_E_any\": 0.66,\\n', ' \"discordant_case_only\": 13,\\n', ' \"discordant_control_only\": 4\\n', '}\\n', 'statsmodels vs own clogit, max |diff beta|: 0.0007782823741675493\\n', \"LPM (pyfixest, stratum FE, CRV1 concept): {'coef_E_any': 0.521, 'se_E_any': 0.2463, 'p_E_any': 0.0414, 'coef_E_neg': -0.1485, 'p_E_neg': 0.5714, 'n': 100}\\n\", \"match balance: {'smd_after_team_bin': 0.0, 'smd_after_act_bin': 0.0, 'smd_after_fy_bin': 0.0, 'smd_after_prior_bin': 0.0, 'smd_after_lp': -0.035, 'smd_after_first_year': 0.019, 'smd_before_team_bin': -0.078, 'smd_before_act_bin': -0.476, 'smd_before_prior_bin': -0.213, 'smd_before_lp': -0.257, 'relax_counts': {0: 46, 1: 4}}\\n\"]\n19 ['03:59:46|INFO   |permutation null in 0s\\n']\n19 [\"{'n': 50, 'mean_logOR': -0.08980923915919878, 'sd_logOR': 0.5498781833383216, 'mean_OR': 0.9141055441824625, 'q025_OR': 0.2764455178279643, 'q975_OR': 2.5946745340193913}\\n\"]\n21 ['field_Physics_Astro      not identified (n_strata=10)\\n', 'field_CS                 not identified (n_strata=19)\\n', 'field_other              not identified (n_strata=21)\\n', 'single_paper_entries     OR(E_any)=3.78 CI=[0.76, 14.5]\\n', 'multi_paper_entries      not identified (n_strata=14)\\n']\n23 ['{\\n', ' \"verdict\": \"UNDERPOWERED\",\\n', ' \"interaction\": \"null: enrichment uniform across A_cont\",\\n', ' \"mediation\": \"A_cont is not reducible to pool size (M2) [lower bound under mediator noise]\",\\n', ' \"vocabulary\": \"no class contrast resolved (CIs include 0)\",\\n', ' \"MDE80_primary_at_p0\": {\\n', '  \"p0_observed\": 0.66,\\n', '  \"grid_point\": 0.6,\\n', '  \"MDE80\": 1.5\\n', ' },\\n', ' \"criteria\": {\\n', '  \"primary_CI_excludes_1_above\": false,\\n', '  \"ratio_neg_CI_excludes_1_above\": false,\\n', '  \"ratio_plac_CI_excludes_1_above\": true,\\n', '  \"OR_plac_significant\": true,\\n', '  \"OR_neg_significant\": false\\n', ' },\\n', ' \"label\": \"screen-fold mechanism evidence, not confirmation\",\\n', ' \"exposure_label\": \"corpus-exposure, coverage-limited\"\\n', '}\\n']\n25 ['Demo: 50 strata, B=100   |   Full run: 1013 strata, B=1000\\n', '                                      demo_OR  demo_lo  demo_hi  full_OR  full_lo  full_hi\\n', 'term                                                                                      \\n', 'Partner use E_any (primary)      3.220000e+00     0.91    12.44     3.09     2.32     4.28\\n', 'Negative-control vocab E_neg     7.000000e-01     0.18     2.39     0.62     0.49     0.77\\n', 'Placebo partners E_plac          1.900000e-01     0.05     0.48     0.72     0.57     0.90\\n', 'Swapped partner set E_swap       5.100000e-01     0.15     1.42     1.11     0.86     1.39\\n', 'E_any x z(A_cont)                4.900000e-01     0.00     1.90     0.87     0.70     1.14\\n', 'NATIVE partners                  2.901911e+11     0.04     4.94     1.47     1.02     2.33\\n', 'ADJACENT partners                1.440000e+00     0.35     7.90     1.91     1.43     2.73\\n', 'FOREIGN partners                 2.710000e+00     1.25    24.86     2.88     2.28     3.69\\n', 'Origin-companion partners        2.330000e+00     1.12    19.10     3.10     2.38     4.26\\n', 'Non-companion partners           4.130000e+00     0.60    33.06     1.36     1.02     1.87\\n', 'Ratio partner / NEG              4.590000e+00     0.89    45.37     5.02     3.45     7.51\\n', 'Ratio partner / PLAC             1.482000e+01     2.15    85.85     4.53     3.05     7.21\\n', 'Ratio NATIVE / FOREIGN           1.069987e+11     0.01     1.08     0.51     0.33     0.89\\n', 'Ratio companion / non-companion  5.600000e-01     0.16     4.02     2.27     1.64     3.21\\n', '\\n', 'Permutation null mean OR: demo 0.91 | full 1.00\\n', 'Pre-declared verdict: demo = UNDERPOWERED  |  full run = SUPPORT\\n', 'Vocabulary reading (demo): no class contrast resolved (CIs include 0)\\n']\n25 display_data ['image/png', 'text/plain']", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [41] THINKING · 2026-09-30 04:00:08 UTC

```
The run finished in 62s with analysis taking ~1s, so I can restore the original values (B=1000, N_PERM=200). I'll also fix the NATIVE point estimate display, which spikes to ~3e11 with 50 strata, by clipping it in the plot and formatting the table without scientific notation.
```

### [42] TOOL CALL — Bash · 2026-09-30 04:00:08 UTC

```
Scale to original B and permutations, re-test:
python3 - <<'EOF'
from pathlib import Path
p = Path("make_notebook.py"); s = p.read_text()
rep = [
 ('B = 100            # bootstrap reps for the model suite     (original full run: 1000)',
  'B = 1000           # bootstrap reps for the model suite     (original full run: 1000; smallest tested: 20)'),
 ('N_PERM = 50       # permutation-null draws                 (original full run: 200; --mini: 50)',
  'N_PERM = 200      # permutation-null draws                 (original full run: 200; --mini: 50)'),
 ('print(T.round(2).to_string())',
  'print(T.to_string(float_format=lambda v: f"{v:.3g}" if abs(v) < 1e3 else f"{v:.1e}"))'),
 ('ax.set_xscale("log")\n',
  'ax.set_xscale("log")\nax.set_xlim(0.01, 200)   # display only: a separated point estimate in the 50-stratum demo is drawn at the edge\n'),
 ('    o, lo, hi = T[f"{pre_}_OR"], T[f"{pre_}_lo"], T[f"{pre_}_hi"]\n',
  '    o, lo, hi = (T[f"{pre_}_{c}"].clip(0.01, 200) for c in ("OR", "lo", "hi"))\n'),
 ("SUPPORT, since the reading rules need CIs that exclude 1.",
  "SUPPORT, since the reading rules need CIs that exclude 1. A term with no discordant exposure in the small sample (e.g.\nNATIVE) can also show a separated, huge point estimate. That is a small-sample artefact, and the plot clips it at the axis edge."),
]
for a, b in rep:
    assert a in s, a
    s = s.replace(a, b)
p.write_text(s)
EOF
python3 make_notebook.py && E=/tmp/aii_nb_test_envs/art_FZ2OCJwV6xHs-3d579ff540c4 && UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && S=$(date +%s) && https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 no_proxy=pypi.org,files.pythonhosted.org NO_PROXY=pypi.org,files.pythonhosted.org $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -5; echo "runtime $(( $(date +%s) - S ))s"; python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
for i,c in enumerate(nb['cells']):
    if c['cell_type']!='code' or i<17: continue
    for o in c['outputs']:
        if o['output_type']=='stream': print(i, ''.join(o['text'])[-2200:])
        elif o['output_type']=='error': print(i,'ERR',o['ename'],o['evalue'])
"
```

### [43] TOOL RESULT — Bash · 2026-09-30 04:01:10 UTC

```
{"stdout": "wrote code_demo.ipynb: 26 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 189264 bytes to code_demo.ipynb\nruntime 60s\n17 04:01:04|INFO   |primary model suite + bootstrap B=1000 in 9s\n\n17 {\n \"n_strata\": 50,\n \"prev_case_E_any\": 0.84,\n \"prev_control_E_any\": 0.66,\n \"discordant_case_only\": 13,\n \"discordant_control_only\": 4\n}\nstatsmodels vs own clogit, max |diff beta|: 0.0007782823741675493\nLPM (pyfixest, stratum FE, CRV1 concept): {'coef_E_any': 0.521, 'se_E_any': 0.2463, 'p_E_any': 0.0414, 'coef_E_neg': -0.1485, 'p_E_neg': 0.5714, 'n': 100}\nmatch balance: {'smd_after_team_bin': 0.0, 'smd_after_act_bin': 0.0, 'smd_after_fy_bin': 0.0, 'smd_after_prior_bin': 0.0, 'smd_after_lp': -0.035, 'smd_after_first_year': 0.019, 'smd_before_team_bin': -0.078, 'smd_before_act_bin': -0.476, 'smd_before_prior_bin': -0.213, 'smd_before_lp': -0.257, 'relax_counts': {0: 46, 1: 4}}\n\n19 04:01:05|INFO   |permutation null in 0s\n\n19 {'n': 200, 'mean_logOR': -0.00468957247411784, 'sd_logOR': 0.5620053367158504, 'mean_OR': 0.9953214064020938, 'q025_OR': 0.3018417152100331, 'q975_OR': 2.5567438635716417}\n\n21 field_Physics_Astro      not identified (n_strata=10)\nfield_CS                 not identified (n_strata=19)\nfield_other              not identified (n_strata=21)\nsingle_paper_entries     OR(E_any)=3.78 CI=[1.04, 17.88]\nmulti_paper_entries      not identified (n_strata=14)\n\n23 {\n \"verdict\": \"SUPPORT\",\n \"interaction\": \"null: enrichment uniform across A_cont\",\n \"mediation\": \"A_cont is not reducible to pool size (M2) [lower bound under mediator noise]\",\n \"vocabulary\": \"no class contrast resolved (CIs include 0)\",\n \"MDE80_primary_at_p0\": {\n  \"p0_observed\": 0.66,\n  \"grid_point\": 0.6,\n  \"MDE80\": 1.5\n },\n \"criteria\": {\n  \"primary_CI_excludes_1_above\": true,\n  \"ratio_neg_CI_excludes_1_above\": true,\n  \"ratio_plac_CI_excludes_1_above\": true,\n  \"OR_plac_significant\": true,\n  \"OR_neg_significant\": false\n },\n \"label\": \"screen-fold mechanism evidence, not confirmation\",\n \"exposure_label\": \"corpus-exposure, coverage-limited\"\n}\n\n25 Demo: 50 strata, B=1000   |   Full run: 1013 strata, B=1000\n                                 demo_OR  demo_lo  demo_hi  full_OR  full_lo  full_hi\nterm                                                                                 \nPartner use E_any (primary)         3.22     1.04       20     3.09     2.32     4.28\nNegative-control vocab E_neg       0.701    0.172     2.61    0.617    0.491    0.771\nPlacebo partners E_plac            0.186   0.0417    0.544    0.723    0.575    0.902\nSwapped partner set E_swap         0.506    0.105     1.58     1.11    0.863     1.39\nE_any x z(A_cont)                  0.486 0.000148     1.92    0.869    0.705     1.14\nNATIVE partners                  2.9e+11    0.614      1.6     1.47     1.02     2.33\nADJACENT partners                   1.44     0.32     10.2     1.91     1.43     2.73\nFOREIGN partners                    2.71     1.08     23.4     2.88     2.28     3.69\nOrigin-companion partners           2.33    0.882     16.6      3.1     2.38     4.26\nNon-companion partners              4.13    0.659     21.7     1.36     1.02     1.87\nRatio partner / NEG                 4.59     1.05     58.1     5.02     3.45     7.51\nRatio partner / PLAC                14.8     3.01      150     4.53     3.05     7.21\nRatio NATIVE / FOREIGN           1.1e+11   0.0405     1.09     0.51    0.327    0.886\nRatio companion / non-companion    0.564    0.137     6.45     2.27     1.64     3.21\n\nPermutation null mean OR: demo 1.00 | full 1.00\nPre-declared verdict: demo = SUPPORT  |  full run = SUPPORT\nVocabulary reading (demo): no class contrast resolved (CIs include 0)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] ASSISTANT · 2026-09-30 04:01:20 UTC

```
The notebook now runs at the original values (B=1000, 200 permutations) in 60 s, and the demo verdict is SUPPORT, matching the full run. Checking the figure:
```

### [45] TOOL CALL — Bash · 2026-09-30 04:01:20 UTC

```
Extract figure and verify URL string:
mkdir -p /tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-4-art-FZ2OCJwV6xHs/a6fddd13-99f0-4f9f-9109-c15a6189b1cc/scratchpad && python3 -c "
import json,base64
nb=json.load(open('code_demo.ipynb'))
for o in nb['cells'][25]['outputs']:
    if 'data' in o and 'image/png' in o['data']:
        open('/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-4-art-FZ2OCJwV6xHs/a6fddd13-99f0-4f9f-9109-c15a6189b1cc/scratchpad/fig.png','wb').write(base64.b64decode(o['data']['image/png']))
"; grep -c 'GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json"' code_demo.ipynb; du -sh *
```

### [46] TOOL RESULT — Bash · 2026-09-30 04:01:20 UTC

```
{"stdout": "0\n5.0K\tbuild_demo_data.py\n185K\tcode_demo.ipynb\n37K\tmake_notebook.py\n79K\tmini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [47] TOOL CALL — Bash · 2026-09-30 04:01:24 UTC

```
Verify exact GitHub URL in notebook source:
python3 -c "
import json
nb=json.load(open('code_demo.ipynb'))
src=''.join(''.join(c['source']) for c in nb['cells'])
print('GITHUB_DATA_URL = \"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-4/evaluation-5/demo/mini_demo_data.json\"' in src, 'urlopen(GITHUB_DATA_URL)' in src)"
```

### [48] TOOL RESULT — Bash · 2026-09-30 04:01:24 UTC

```
{"stdout": "True True", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [49] TOOL CALL — Read · 2026-09-30 04:01:24 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-4-art-FZ2OCJwV6xHs/a6fddd13-99f0-4f9f-9109-c15a6189b1cc/scratchpad/fig.png
```

### [50] TOOL RESULT — Read · 2026-09-30 04:01:24 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [51] ASSISTANT · 2026-09-30 04:01:36 UTC

```
The figure is fine. Next I'll write the README, the manifest (there are no heavy files) and the struct output.
```

### [52] TOOL CALL — Bash · 2026-09-30 04:01:36 UTC

````
Write manifest, README, and struct output JSON:
cat > .aii/manifest.yaml <<'EOF'
# No heavy paths: every file in this workspace is small text/JSON (< 1 MB total); nothing to keep or delete.
entries: []
EOF
cat > README.md <<'EOF'
# Demo: do adopters already know the partner words?

This is a runnable Colab/Jupyter demo of `eval.py`, the adopter-level test of the absorptive-capacity mechanism behind
D2's host-share effect (`A_cont`). All results come from the screen fold only, so they are *mechanism evidence, not
confirmation*.

The notebook re-runs the `analyze` stage's matched-pair analysis using the original code from `eval.py`,
`src/analysis.py` and `src/stats_core.py`. It covers:
- conditional-logit enrichment (M-i), with the NEG, placebo and swapped-partner comparisons;
- the interaction with `A_cont` (M-ii);
- the partner vocabulary class and origin companions (M-iii);
- the concept-cluster bootstrap, the permutation null, match balance, and the statsmodels and pyfixest cross-checks;
- subgroup fits and the pre-declared reading rules.

It runs on 50 matched 1:1 strata (100 authors) drawn from the 1,013-stratum primary frame. The corpus-dependent exposure
step and the entry-level PPML mediation (M-iv) are not re-run. The data file carries their outputs and the full-run
mediation result instead.

## Layout
| Path | What it is |
|---|---|
| `code_demo.ipynb` | The demo notebook, executed. It runs in about 60 s at the original settings (B = 1000, 200 permutations). |
| `mini_demo_data.json` | 100 case/control rows with exposure columns, plus frozen inputs (A_cont mean/SD, pre-match risk-set means, MDEs, full-run mediation) and full-run reference estimates. |
| `build_demo_data.py` | Builds `mini_demo_data.json` from the artifact's `results/exposures_primary.parquet`, `frames/` and result JSONs. |
| `make_notebook.py` | Writes `code_demo.ipynb` cell by cell. |

## How to run
Open `code_demo.ipynb` in Colab and run all cells. The first cell installs `pyfixest` and `loguru`. The notebook reads
`mini_demo_data.json` from the GitHub raw URL, or from the local file when the URL is unreachable.

To run it locally:
```bash
jupyter nbconvert --to notebook --execute code_demo.ipynb --output code_demo.ipynb
```

## Restoring removed files
Nothing was marked for deletion (`.aii/manifest.yaml` has no entries), so there is nothing to restore.
EOF
cat > .terminal_claude_agent_struct_out.json <<'EOF'
{"out_expected_files": {"notebook": "code_demo.ipynb", "mini_data_file": "mini_demo_data.json"}}
EOF
cat .terminal_claude_agent_struct_out.json; ls -la
````

### [53] TOOL RESULT — Bash · 2026-09-30 04:01:36 UTC

```
{"stdout": "{\"out_expected_files\": {\"notebook\": \"code_demo.ipynb\", \"mini_data_file\": \"mini_demo_data.json\"}}\ntotal 3782\ndrwxrwxrwx 3 aii-agent aii-agent 1076209 Sep 30 04:01 .\ndrwxrwxrwx 7 aii-agent aii-agent 2000613 Sep 30 03:51 ..\ndrwxrwxrwx 2 aii-agent aii-agent   12100 Sep 30 04:01 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Sep 30 03:52 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent  465766 Sep 30 04:01 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent      97 Sep 30 04:01 .terminal_claude_agent_struct_out.json\n-rw-rw-rw- 1 aii-agent aii-agent    2143 Sep 30 04:01 README.md\n-rw-rw-rw- 1 aii-agent aii-agent    4965 Sep 30 03:54 build_demo_data.py\n-rw-rw-rw- 1 aii-agent aii-agent  189288 Sep 30 04:01 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent   37510 Sep 30 04:00 make_notebook.py\n-rw-rw-rw- 1 aii-agent aii-agent   80444 Sep 30 03:54 mini_demo_data.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [54] ASSISTANT · 2026-09-30 04:01:46 UTC

```
I've built `code_demo.ipynb` and `mini_demo_data.json`. The notebook ran start to finish in a clean Python 3.12 environment in about 60 s, using the original settings of 1,000 bootstrap reps and 200 permutations.

**What the notebook runs.** It re-runs the part of `eval.py` that fits the case-control models. The code is copied unchanged from `eval.py` and the artifact's two helper modules, split into cells with explanations in between:
- the enrichment models, including the negative-control, placebo and swapped-partner comparisons;
- the interaction with `A_cont`;
- the vocabulary-class models;
- the concept bootstrap, the permutation null, match balance, the statsmodels and pyfixest cross-checks, subgroup fits and `reading()`.

The notebook ends with a table and a forest plot comparing the demo estimates with the full-run estimates.

**What it doesn't re-run.** The earlier pipeline stages, the step that computes each author's prior exposure, and the entry-level mediation analysis all need the 463k-work corpus. That corpus isn't shipped. Instead, the data file carries the already-computed exposure columns and the full run's mediation result. The notebook's markdown says this at each point.

**Data.** The data file holds 50 matched pairs (100 authors), drawn from the 1,013 pairs and stratified by `A_cont` tercile. That uses the full 100-example limit.

**Demo vs. full run:**

| | Demo (50 pairs) | Full run (1,013 pairs) |
|---|---|---|
| Primary odds ratio | 3.22 [1.04, 20] | 3.09 [2.32, 4.28] |
| Pre-declared verdict | SUPPORT | SUPPORT |
| Permutation null, mean odds ratio | 1.00 | 1.00 |

With only 50 pairs there are small-sample effects:
- Most subgroups fall below the original 30-pair minimum, so they are reported as not identified.
- The NATIVE point estimate blows up (odds ratio about 3e11). The plot clips it at the axis edge, and the markdown explains why.

**Issues to know about:**
- **Stale file at the GitHub URL.** An earlier attempt already put a `mini_demo_data.json` at that URL, with a different structure. It broke my first test run. Publishing this workspace should overwrite it. Until then, the notebook fails if it loads the remote file, which it tries before the local copy. To test against the local file, I blocked only the GitHub fetch with a dead proxy and left PyPI reachable.
- **No todo list.** No todo-tracking tool was available in this session, so the TODO list wasn't recorded. All six steps were done.

The notebook contains the exact `GITHUB_DATA_URL` and uses the GitHub-then-local loading pattern. I also added `README.md`, a manifest with no entries (nothing in the workspace is large), `.terminal_claude_agent_struct_out.json`, and the two scripts that rebuild the data file and the notebook.

Files are in `art_FZ2OCJwV6xHs/`:
- code_demo.ipynb
- mini_demo_data.json
- README.md
- build_demo_data.py
- make_notebook.py
```
