# gen_demo_art_dataset_1 — report_results

> Phase: `gen_paper_repo` · `gen_demo_art`
> Run: `iter5_6136aaed9367` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries
>
> Full, verbatim transcript of this agent task — every system/user prompt, assistant response, thinking block, tool call and tool result — in the order they occurred. Nothing truncated.

## Task: `gen_demo_art_dataset_1` (terminal_claude_agent, claude-opus-5-5)

### [1] CONFIG · 2026-09-30 03:18:35 UTC

```
model: Claude Opus 5.5 | effort: high | permission: bypassPermissions
```

### [2] SYSTEM-USER prompt · 2026-09-30 03:18:43 UTC

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
Your workspace: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK`

CRITICAL: Every file you create, write, or save MUST be inside this workspace directory (subdirectories OK). You MUST NOT write files anywhere outside this path — external paths are READ-ONLY. Use absolute paths for all file operations.

EVERY file write MUST start with `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK/`:
GOOD: `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK/file.py`, `/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK/results/out.json`
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
id: art_94GEMUsgAmgK
type: dataset
title: New science concepts and their papers
summary: >-
  Outcome-blind pool of emerging scientific concepts (noun phrases first used 2005-2016 by OpenAlex title+abstract surface-form
  counts; frame frozen+sha256-hashed before any post-F+2 data) plus a stationary reference arm, with COMPLETE OpenAlex work
  lists 2000-2024. Five datasets, exported row-per-example in full_data_out/full_data_out_{1,2}.json (exp_sel_data_out): (1)
  concept_pool_2005_2016: 206 concepts = 184 main + 22 reference; input JSON has phrase, surface forms, F, screen counts <=F+2,
  early volume V, origin field/subfield; output JSON has oa_counts_by_year 2000-2024, n_works, work_ids; metadata: fold (screen
  123 / heldout_concept 61 / reference), F_band, volume tercile, focal_years_screen (2010-14) / heldout (2016-18), retrieval_route
  (26 OpenAlex-native, 180 S2-index->OpenAlex mapped, mapping rate 0.93), flags (sense_check_fail 21). (2) concept_work_links:
  214,798 verified concept->work links [concept_id, work_id, year] -> match_evidence. (3) openalex_works: 208,374 unique works;
  input array (feature_names in top-level metadata: year, type, source, topics, refs_in_corpus, author_ids, keyword/legacy-concept
  ids, has_abstract, cited_by_count, dup_group) -> primary-topic subfield id; full referenced_works, institutions and scores
  are in works/works_part_00..03.parquet. (4) subfield_year_totals: 25,195 rows, subfield x year 2000-2024 totals in 4 variants
  (all, typed, has_abstract, has_references) for per-10^4 normalisation. (5) venue_habitat: 15,261 venues with subfield shares,
  dominant subfield, megajournal/coverage flags (4,292 covered). Also context/quality_report (Gate-A: main host traced share
  0.552), recall_audit (median ratio vs S2 0.84, Spearman 0.976), taxonomy.json, keywords_dict.json, pending_hydration.json
  (220 concepts; resume with hydrate.py). Caveats: 363/366 eligible concepts come from the arXiv-mined arm, so the pool is
  dominated by Physics/Astronomy, CS and physical sciences; realised N (184 main) is below the planned 400 because the shared
  free OpenAlex key ran out of credits; route mixes native and S2-mapped discovery; co-authorship is within-corpus only.
workspace_path: >-
  /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1
out_expected_files:
- data.py
- full_data_out.json
- preview_data_out.json
- mini_data_out.json
- reproducibility.md
out_demo_files:
- path: data.py
  description: Dataset fetching/generation script
</artifact_info>

<github_repo>
Repo URL: https://github.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new
Raw data URL: https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json

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
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json"
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
To test-run the notebook in a clean environment (simulating Colab), use the disposable venv at `/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea`. It is on this machine's local disk, outside your workspace, which is on a slow network volume: never create a venv inside your workspace.
```bash
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 /tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea
UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python /tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea/bin/python jupyter ipykernel
/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb
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
TODO 6. Verify: (1) code_demo.ipynb contains GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json" exactly, (2) mini_demo_data.json exists, (3) uses GitHub URL pattern not just open('mini_demo_data.json').
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

### [3] TOOL CALL — Skill · 2026-09-30 03:18:45 UTC

```
aii-colab
```

### [4] TOOL RESULT — Skill · 2026-09-30 03:18:45 UTC

```
{"success": true, "commandName": "aii-colab"}
```

### [5] TOOL CALL — Skill · 2026-09-30 03:18:45 UTC

```
aii-long-running-tasks
```

### [6] TOOL RESULT — Skill · 2026-09-30 03:18:45 UTC

```
{"success": true, "commandName": "aii-long-running-tasks"}
```

### [7] TOOL CALL — Bash · 2026-09-30 03:18:47 UTC

```
List artifact workspace and current dir:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1; ls -la $W; ls -la $W/* | head -80; wc -l $W/data.py; pwd; ls -la
```

### [8] TOOL RESULT — Bash · 2026-09-30 03:18:49 UTC

```
{"stdout": "total 34648\ndrwxrwxrwx  17 aii-agent aii-agent 3000159 Sep 28 20:07 .\ndrwxrwxrwx   7 aii-agent aii-agent 3000586 Sep 28 11:16 ..\ndrwxrwxrwx   2 aii-agent aii-agent 1000109 Sep 28 19:06 .aii\n-rw-rw-rw-   1 aii-agent aii-agent      54 Sep 28 18:23 .aii_claude_session.json\n-rw-rw-rw-   1 aii-agent aii-agent    3751 Sep 28 19:07 .aii_worker_result.json\n-rw-rw-rw-   1 aii-agent aii-agent      40 Sep 28 11:17 .env\n-rw-rw-rw-   1 aii-agent aii-agent      61 Sep 28 11:17 .gitignore\n-rw-rw-rw-   1 aii-agent aii-agent   56260 Sep 28 19:06 .repl_agent.ptylog\n-rw-rw-rw-   1 aii-agent aii-agent    2884 Sep 28 18:26 .terminal_claude_agent_struct_out.json\n-rw-rw-rw-   1 aii-agent aii-agent   22850 Sep 28 17:54 README.md\n-rw-rw-rw-   1 aii-agent aii-agent    3753 Sep 28 16:48 TODO.md\ndrwxrwxrwx   2 aii-agent aii-agent       1 Sep 28 20:07 arxiv_raw\n-rw-rw-rw-   1 aii-agent aii-agent   29424 Sep 28 13:32 assemble.py\n-rw-rw-rw-   1 aii-agent aii-agent    5647 Sep 28 16:03 audit.py\n-rw-rw-rw-   1 aii-agent aii-agent   10997 Sep 28 11:38 build_vocab.py\n-rw-rw-rw-   1 aii-agent aii-agent   11258 Sep 28 12:55 common.py\n-rw-rw-rw-   1 aii-agent aii-agent 1480093 Sep 28 17:19 concept_work.parquet\ndrwxrwxrwx   2 aii-agent aii-agent 2000777 Sep 28 16:04 context\n-rw-rw-rw-   1 aii-agent aii-agent  264847 Sep 28 12:24 credit_ledger.jsonl\n-rw-rw-rw-   1 aii-agent aii-agent    8230 Sep 28 16:46 data.py\n-rw-rw-rw-   1 aii-agent aii-agent 2791678 Sep 28 17:20 data_out.json\n-rw-rw-rw-   1 aii-agent aii-agent    1724 Sep 28 11:29 denominators.py\n-rw-rw-rw-   1 aii-agent aii-agent    1392 Sep 28 11:24 download_snapshot.py\n-rw-rw-rw-   1 aii-agent aii-agent    4288 Sep 28 11:45 early_window.py\n-rw-rw-rw-   1 aii-agent aii-agent    1731 Sep 28 11:45 fetch_arxiv.py\ndrwxrwxrwx   2 aii-agent aii-agent 2014992 Sep 28 16:47 full_data_out\n-rw-rw-rw-   1 aii-agent aii-agent   13652 Sep 28 17:15 hydrate.py\n-rw-rw-rw-   1 aii-agent aii-agent    7241 Sep 28 17:15 hydrate_lib.py\n-rw-rw-rw-   1 aii-agent aii-agent  565495 Sep 28 17:19 keywords_dict.json\n-rw-rw-rw-   1 aii-agent aii-agent    2773 Sep 28 11:31 llm_utils.py\ndrwxrwxrwx   2 aii-agent aii-agent 2000494 Sep 28 16:47 logs\ndrwxrwxrwx   2 aii-agent aii-agent       1 Sep 28 20:07 mesh_raw\n-rw-rw-rw-   1 aii-agent aii-agent     960 Sep 28 17:15 migrate_store.py\n-rw-rw-rw-   1 aii-agent aii-agent    4572 Sep 28 11:43 mine_arxiv.py\n-rw-rw-rw-   1 aii-agent aii-agent   19650 Sep 28 16:47 mini_data_out.json\n-rw-rw-rw-   1 aii-agent aii-agent   33646 Sep 28 17:18 pending_hydration.json\n-rw-rw-rw-   1 aii-agent aii-agent    1085 Sep 28 11:27 prefilter_tags.py\n-rw-rw-rw-   1 aii-agent aii-agent    9776 Sep 28 16:47 preview_data_out.json\ndrwxrwxrwx   2 aii-agent aii-agent 1019354 Sep 28 11:26 probes\n-rw-rw-rw-   1 aii-agent aii-agent    1707 Sep 28 16:47 pyproject.toml\ndrwxrwxrwx 258 aii-agent aii-agent 2067954 Sep 28 11:45 raw_cache\n-rw-rw-rw-   1 aii-agent aii-agent    4935 Sep 28 17:18 reproducibility.md\ndrwxrwxrwx   2 aii-agent aii-agent 2005911 Sep 28 15:58 retrieval\n-rw-rw-rw-   1 aii-agent aii-agent    8504 Sep 28 11:53 sample_frame.py\n-rw-rw-rw-   1 aii-agent aii-agent  512316 Sep 28 11:55 sample_frame_frozen.json\n-rw-rw-rw-   1 aii-agent aii-agent      91 Sep 28 11:55 sample_frame_frozen.sha256\ndrwxrwxrwx   2 aii-agent aii-agent 1033305 Sep 28 12:02 screen\n-rw-rw-rw-   1 aii-agent aii-agent    4534 Sep 28 11:31 screen.py\n-rw-rw-rw-   1 aii-agent aii-agent    3145 Sep 28 11:49 select_arxiv.py\n-rw-rw-rw-   1 aii-agent aii-agent    5895 Sep 28 11:31 select_candidates.py\ndrwxrwxrwx   9 aii-agent aii-agent 2012255 Sep 28 11:24 snapshot_entities\n-rw-rw-rw-   1 aii-agent aii-agent  341727 Sep 28 11:45 taxonomy.json\ndrwxrwxrwx   4 aii-agent aii-agent 2013210 Sep 28 12:02 temp\n-rw-rw-rw-   1 aii-agent aii-agent    3727 Sep 28 12:55 validate.py\ndrwxrwxrwx   2 aii-agent aii-agent 2001060 Sep 28 11:50 vocab\ndrwxrwxrwx   2 aii-agent aii-agent 2039248 Sep 28 17:18 work_store\ndrwxrwxrwx   2 aii-agent aii-agent 2007078 Sep 28 17:19 works\n-rw-rw-rw-   1 aii-agent aii-agent   22850 Sep 28 17:54 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/README.md\n-rw-rw-rw-   1 aii-agent aii-agent    3753 Sep 28 16:48 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/TODO.md\n-rw-rw-rw-   1 aii-agent aii-agent   29424 Sep 28 13:32 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/assemble.py\n-rw-rw-rw-   1 aii-agent aii-agent    5647 Sep 28 16:03 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/audit.py\n-rw-rw-rw-   1 aii-agent aii-agent   10997 Sep 28 11:38 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/build_vocab.py\n-rw-rw-rw-   1 aii-agent aii-agent   11258 Sep 28 12:55 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/common.py\n-rw-rw-rw-   1 aii-agent aii-agent 1480093 Sep 28 17:19 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/concept_work.parquet\n-rw-rw-rw-   1 aii-agent aii-agent  264847 Sep 28 12:24 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/credit_ledger.jsonl\n-rw-rw-rw-   1 aii-agent aii-agent    8230 Sep 28 16:46 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/data.py\n-rw-rw-rw-   1 aii-agent aii-agent 2791678 Sep 28 17:20 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/data_out.json\n-rw-rw-rw-   1 aii-agent aii-agent    1724 Sep 28 11:29 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/denominators.py\n-rw-rw-rw-   1 aii-agent aii-agent    1392 Sep 28 11:24 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/download_snapshot.py\n-rw-rw-rw-   1 aii-agent aii-agent    4288 Sep 28 11:45 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/early_window.py\n-rw-rw-rw-   1 aii-agent aii-agent    1731 Sep 28 11:45 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/fetch_arxiv.py\n-rw-rw-rw-   1 aii-agent aii-agent   13652 Sep 28 17:15 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/hydrate.py\n-rw-rw-rw-   1 aii-agent aii-agent    7241 Sep 28 17:15 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/hydrate_lib.py\n-rw-rw-rw-   1 aii-agent aii-agent  565495 Sep 28 17:19 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/keywords_dict.json\n-rw-rw-rw-   1 aii-agent aii-agent    2773 Sep 28 11:31 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/llm_utils.py\n-rw-rw-rw-   1 aii-agent aii-agent     960 Sep 28 17:15 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/migrate_store.py\n-rw-rw-rw-   1 aii-agent aii-agent    4572 Sep 28 11:43 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/mine_arxiv.py\n-rw-rw-rw-   1 aii-agent aii-agent   19650 Sep 28 16:47 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/mini_data_out.json\n-rw-rw-rw-   1 aii-agent aii-agent   33646 Sep 28 17:18 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/pending_hydration.json\n-rw-rw-rw-   1 aii-agent aii-agent    1085 Sep 28 11:27 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/prefilter_tags.py\n-rw-rw-rw-   1 aii-agent aii-agent    9776 Sep 28 16:47 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/preview_data_out.json\n-rw-rw-rw-   1 aii-agent aii-agent    1707 Sep 28 16:47 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/pyproject.toml\n-rw-rw-rw-   1 aii-agent aii-agent    4935 Sep 28 17:18 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/reproducibility.md\n-rw-rw-rw-   1 aii-agent aii-agent    8504 Sep 28 11:53 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/sample_frame.py\n-rw-rw-rw-   1 aii-agent aii-agent  512316 Sep 28 11:55 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/sample_frame_frozen.json\n-rw-rw-rw-   1 aii-agent aii-agent      91 Sep 28 11:55 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/sample_frame_frozen.sha256\n-rw-rw-rw-   1 aii-agent aii-agent    4534 Sep 28 11:31 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/screen.py\n-rw-rw-rw-   1 aii-agent aii-agent    3145 Sep 28 11:49 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/select_arxiv.py\n-rw-rw-rw-   1 aii-agent aii-agent    5895 Sep 28 11:31 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/select_candidates.py\n-rw-rw-rw-   1 aii-agent aii-agent  341727 Sep 28 11:45 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/taxonomy.json\n-rw-rw-rw-   1 aii-agent aii-agent    3727 Sep 28 12:55 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/validate.py\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/arxiv_raw:\ntotal 2931\ndrwxrwxrwx  2 aii-agent aii-agent       1 Sep 28 20:07 .\ndrwxrwxrwx 17 aii-agent aii-agent 3000159 Sep 28 20:07 ..\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/context:\ntotal 12850\ndrwxrwxrwx  2 aii-agent aii-agent 2000777 Sep 28 16:04 .\ndrwxrwxrwx 17 aii-agent aii-agent 3000159 Sep 28 20:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   56957 Sep 28 17:20 quality_report.json\n-rw-rw-rw-  1 aii-agent aii-agent    4295 Sep 28 17:20 quality_report.md\n-rw-rw-rw-  1 aii-agent aii-agent   27471 Sep 28 16:04 recall_audit.json\n-rw-rw-rw-  1 aii-agent aii-agent  355352 Sep 28 17:19 subfield_year_totals.json\n-rw-rw-rw-  1 aii-agent aii-agent  315299 Sep 28 11:30 subfield_year_totals_raw.json\n-rw-rw-rw-  1 aii-agent aii-agent 7395734 Sep 28 17:20 venue_habitat.json\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/full_data_out:\ntotal 158421\ndrwxrwxrwx  2 aii-agent aii-agent  2014992 Sep 28 16:47 .\ndrwxrwxrwx 17 aii-agent aii-agent  3000159 Sep 28 20:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent 90000945 Sep 28 16:46 full_data_out_1.json\n-rw-rw-rw-  1 aii-agent aii-agent 67167894 Sep 28 16:46 full_data_out_2.json\n-rw-rw-rw-  1 aii-agent aii-agent    17335 Sep 28 16:47 mini_full_data_out_1.json\n-rw-rw-rw-  1 aii-agent aii-agent     6651 Sep 28 16:47 mini_full_data_out_2.json\n-rw-rw-rw-  1 aii-agent aii-agent     7921 Sep 28 16:47 preview_full_data_out_1.json\n-rw-rw-rw-  1 aii-agent aii-agent     4763 Sep 28 16:47 preview_full_data_out_2.json\n\n/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/logs:\ntotal 9963\ndrwxrwxrwx  2 aii-agent aii-agent 2000494 Sep 28 16:47 .\ndrwxrwxrwx 17 aii-agent aii-agent 3000159 Sep 28 20:07 ..\n-rw-rw-rw-  1 aii-agent aii-agent   17363 Sep 28 17:20 assemble.log\n-rw-rw-rw-  1 aii-agent aii-agent     677 Sep 28 17:20 assemble_summary.json\n-rw-rw-rw-  1 aii-agent aii-agent    4304 Sep 28 16:04 audit.log\n-rw-rw-rw-  1 aii-agent aii-agent    3131 Sep 28 16:04 audit.out\n-rw-rw-rw-  1 aii-agent aii-agent     808 Sep 28 11:38 build_vocab.log\n-rw-rw-rw-  1 aii-agent aii-agent    2162 Sep 28 16:46 data.log\n-rw-rw-rw-  1 aii-agent aii-agent      99 Sep 28 11:30 denominators.log\n-rw-rw-rw-  1 aii-agent aii-agent      61 Sep 28 11:30 denominators.out\n-rw-rw-rw-  1 aii-agent aii-agent    1731 Sep 28 11:57 download_hf.out\n-rw-rw-rw-  1 aii-agent aii-agent      61 Sep 28 11:24 download_snapshot.log\n-rw-rw-rw-  1 aii-agent aii-agent     244 Sep 28 11:46 early_window.log\n-rw-rw-rw-  1 aii-agent aii-agent    4865 Sep 28 11:48 fetch_arxiv.log\n-rw-rw-rw-  1 aii-agent aii-agent     495 Sep 28 11:48 fetch_arxiv.out\n-rw-rw-rw-  1 aii-agent aii-agent       5 Sep 28 11:45 fetch_arxiv.pid\n172 /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/data.py\n/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK\ntotal 1983\ndrwxrwxrwx 3 aii-agent aii-agent 1002376 Sep 30 03:18 .\ndrwxrwxrwx 5 aii-agent aii-agent 1002379 Sep 30 03:17 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:17 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Sep 30 03:18 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent   24279 Sep 30 03:18 .repl_agent.ptylog", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [9] TOOL CALL — Bash · 2026-09-30 03:18:51 UTC

```
Read data.py and preview files:
W=/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1; cat $W/data.py; head -c 4000 $W/preview_data_out.json; echo; head -c 3000 $W/full_data_out/preview_full_data_out_1.json; echo; head -c 3000 $W/full_data_out/preview_full_data_out_2.json
```

### [10] TOOL RESULT — Bash · 2026-09-30 03:18:51 UTC

```
{"stdout": "# /// script\n# requires-python = \">=3.12\"\n# dependencies = [\"orjson\", \"pandas\", \"pyarrow\", \"loguru\"]\n# ///\n\"\"\"Standardise the candidate datasets to the exp_sel_data_out schema, ONE EXAMPLE PER DATA ROW, grouped by dataset.\n\nArtifact datasets (built by this repo; canonical files at the workspace root):\n  concept_pool_2005_2016   D1  data_out.json            1 row / concept      output = oa_counts_by_year+work_ids (JSON)\n  concept_work_links       D3  concept_work.parquet     1 row / link         output = match_evidence\n  openalex_works           D2  works/*.parquet          1 row / work         output = primary-topic subfield_id\n  subfield_year_totals     D4  context/subfield_year_totals.json  1 row / (variant, year, subfield)  output = count\n  venue_habitat            D5  context/venue_habitat.json         1 row / venue  output = dominant_subfield\n(The 5 labelled HF grounding sets in temp/datasets/ were evaluated in an earlier version and not selected.)\n\nUsage: uv run data.py   -> full_data_out.json, split into full_data_out/full_data_out_N.json when > 90 MB\"\"\"\nimport sys\nfrom pathlib import Path\n\nimport orjson\nimport pandas as pd\nimport pyarrow.parquet as pq\nfrom loguru import logger\n\nROOT = Path(__file__).resolve().parent\nPART_LIMIT = 90_000_000\nBEST5 = [\"concept_pool_2005_2016\", \"concept_work_links\", \"openalex_works\", \"subfield_year_totals\", \"venue_habitat\"]\n\nlogger.remove()\nlogger.add(sys.stdout, level=\"INFO\", format=\"{time:HH:mm:ss}|{level:<7}|{message}\")\nlogger.add(ROOT / \"logs\" / \"data.log\", rotation=\"30 MB\", level=\"DEBUG\")\n\nJ = lambda o: orjson.dumps(o).decode()  # noqa: E731\n\n\ndef concept_meta() -> dict:\n    d = orjson.loads((ROOT / \"data_out.json\").read_bytes())\n    return {e[\"metadata_concept_id\"]: e for e in d[\"datasets\"][0][\"examples\"]}\n\n\ndef ds_concept_pool() -> list[dict]:\n    d = orjson.loads((ROOT / \"data_out.json\").read_bytes())\n    return d[\"datasets\"][0][\"examples\"]\n\n\nLINK_FEATURES = [\"concept_id\", \"work_id\", \"year\"]\n\n\ndef ds_links(cm: dict) -> list[dict]:\n    \"\"\"input = JSON array ordered as LINK_FEATURES (names in top-level metadata to keep the file small).\"\"\"\n    cw = pd.read_parquet(ROOT / \"concept_work.parquet\")\n    out = []\n    for i, r in enumerate(cw.itertuples(index=False)):\n        c = cm[r.concept_id]\n        out.append({\"input\": J([r.concept_id, int(r.work_id), int(r.year)]), \"output\": str(r.match_evidence),\n                    \"metadata_fold\": c[\"metadata_fold\"], \"metadata_matched_form\": r.matched_form,\n                    \"metadata_dup_group\": None if pd.isna(r.dup_group) else int(r.dup_group)})\n    return out\n\n\nWORK_FEATURES = [\"work_id\", \"publication_year\", \"type\", \"language\", \"doi_present\", \"s2_corpus_id\", \"primary_topic_id\",\n                 \"topic_score\", \"topics_top3\", \"source_id\", \"source_type\", \"n_refs\", \"refs_in_corpus\", \"author_ids\",\n                 \"keyword_idx\", \"concept_ids\", \"has_abstract\", \"abstract_n_tokens\", \"cited_by_count\", \"dup_group\"]\n\n\ndef ds_works() -> list[dict]:\n    \"\"\"input = JSON array ordered as WORK_FEATURES; output = primary-topic subfield id (ASJC-style) or 'unknown'.\n    Full referenced_works, institution_ids and keyword/concept scores stay in works/works_part_XX.parquet.\"\"\"\n    out = []\n    cols = WORK_FEATURES + [\"subfield_id\", \"field_id\", \"domain_id\"]\n    for p in sorted((ROOT / \"works\").glob(\"works_part_*.parquet\")):\n        for r in pq.read_table(p, columns=cols).to_pylist():\n            if r[\"topic_score\"] is not None:\n                r[\"topic_score\"] = round(float(r[\"topic_score\"]), 4)\n            sf = r[\"subfield_id\"]\n            out.append({\"input\": J([r[k] for k in WORK_FEATURES]), \"output\": str(sf) if sf is not None else \"unknown\",\n                        \"metadata_field_id\": r[\"field_id\"], \"metadata_domain_id\": r[\"domain_id\"]})\n    return out\n\n\ndef ds_denominators() -> list[dict]:\n    d4 = orjson.loads((ROOT / \"context\" / \"subfield_year_totals.json\").read_bytes())\n    tax = orjson.loads((ROOT / \"taxonomy.json\").read_bytes())\n    out = []\n    for v, years in d4[\"variants\"].items():\n        for y, t in sorted(years.items()):\n            for sf, n in sorted(t[\"subfield\"].items(), key=lambda x: int(x[0])):\n                f = tax[\"subfield_field\"].get(sf)\n                out.append({\"input\": J({\"variant\": v, \"year\": int(y), \"subfield_id\": int(sf),\n                                        \"subfield_name\": tax[\"subfields\"].get(sf), \"field_id\": f,\n                                        \"domain_id\": tax[\"field_domain\"].get(str(f)) if f else None}),\n                            \"output\": str(n), \"metadata_level\": \"subfield\", \"metadata_task_type\": \"regression\",\n                            \"metadata_year_total_with_topic\": t[\"total_with_topic\"], \"metadata_year_unknown\": t[\"unknown\"]})\n    return out\n\n\ndef ds_venues() -> list[dict]:\n    d5 = orjson.loads((ROOT / \"context\" / \"venue_habitat.json\").read_bytes())\n    out = []\n    for v in d5[\"venues\"]:\n        inp = {k: v[k] for k in [\"source_id\", \"issn_l\", \"display_name\", \"type\", \"host_org\", \"works_count\",\n                                 \"max_works_per_year\", \"subfield_shares\", \"n_cpapers\"]}\n        out.append({\"input\": J(inp), \"output\": str(v[\"dominant_subfield\"]) if v[\"dominant_subfield\"] is not None else \"unknown\",\n                    \"metadata_dominant_share\": v[\"dominant_share\"], \"metadata_megajournal\": v[\"megajournal\"],\n                    \"metadata_covered\": v[\"covered\"], \"metadata_uncovered_reason\": v[\"uncovered_reason\"],\n                    \"metadata_task_type\": \"classification\"})\n    return out\n\n\nTOP_META = {\n    \"description\": \"Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.\",\n    \"feature_names\": {\"concept_work_links\": LINK_FEATURES, \"openalex_works\": WORK_FEATURES},\n    \"notes\": {\"openalex_works\": \"input is a JSON array in feature_names order; output = primary_topic subfield_id; full \"\n                                \"refs/institutions/scores in works/works_part_XX.parquet\",\n              \"concept_work_links\": \"input = [concept_id, work_id, year]; output = match_evidence; concept details in \"\n                                    \"concept_pool_2005_2016\"}}\n\n\ndef write_parts(datasets: list[dict]) -> None:\n    for old in [ROOT / \"full_data_out.json\"] + sorted((ROOT / \"full_data_out\").glob(\"full_data_out_*.json\")):\n        old.unlink(missing_ok=True)\n    total = sum(len(orjson.dumps(e)) + 1 for d in datasets for e in d[\"examples\"])\n    if total < PART_LIMIT:\n        (ROOT / \"full_data_out.json\").write_bytes(orjson.dumps({\"metadata\": TOP_META, \"datasets\": datasets}))\n        logger.info(f\"wrote full_data_out.json ({total / 1e6:.1f} MB)\")\n        return\n    (ROOT / \"full_data_out\").mkdir(exist_ok=True)\n    parts, cur, size = [], [], 0\n    for d in datasets:\n        chunk = []\n        for e in d[\"examples\"]:\n            b = len(orjson.dumps(e)) + 1\n            if size + b > PART_LIMIT and (chunk or cur):\n                if chunk:\n                    cur.append({\"dataset\": d[\"dataset\"], \"examples\": chunk})\n                parts.append(cur)\n                cur, chunk, size = [], [], 0\n            chunk.append(e)\n            size += b\n        if chunk:\n            cur.append({\"dataset\": d[\"dataset\"], \"examples\": chunk})\n    if cur:\n        parts.append(cur)\n    for k, p in enumerate(parts, 1):\n        (ROOT / \"full_data_out\" / f\"full_data_out_{k}.json\").write_bytes(orjson.dumps({\"metadata\": TOP_META, \"datasets\": p}))\n    logger.info(f\"wrote {len(parts)} parts to full_data_out/ ({total / 1e6:.1f} MB total)\")\n\n\n@logger.catch(reraise=True)\ndef main() -> None:\n    cm = concept_meta()\n    builders = {\n        \"concept_pool_2005_2016\": ds_concept_pool,\n        \"concept_work_links\": lambda: ds_links(cm),\n        \"openalex_works\": ds_works,\n        \"subfield_year_totals\": ds_denominators,\n        \"venue_habitat\": ds_venues,\n    }\n    names = BEST5\n    datasets = []\n    for n in names:\n        try:\n            ex = builders[n]()\n        except (FileNotFoundError, KeyError, ValueError) as e:\n            logger.error(f\"{n}: failed ({e})\")\n            raise\n        logger.info(f\"{n}: {len(ex)} examples\")\n        datasets.append({\"dataset\": n, \"examples\": ex})\n    write_parts(datasets)\n\n\nif __name__ == \"__main__\":\n    main()\n{\n \"metadata\": {\n  \"description\": \"Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.\",\n  \"feature_names\": {\n   \"concept_work_links\": [\n    \"concept_id\",\n    \"work_id\",\n    \"year\"\n   ],\n   \"openalex_works\": [\n    \"work_id\",\n    \"publication_year\",\n    \"type\"\n   ]\n  },\n  \"notes\": {\n   \"openalex_works\": \"input is a JSON array in feature_names order; output = primary_topic subfield_id; full refs/institutions/scores in works/works_part_XX.parquet\",\n   \"concept_work_links\": \"input = [concept_id, work_id, year]; output = match_evidence; concept details in concept_pool_2005_2016\"\n  }\n },\n \"datasets\": [\n  {\n   \"dataset\": \"concept_pool_2005_2016\",\n   \"examples\": [\n    {\n     \"input\": \"{\\\"concept_id\\\":\\\"c_9cceb3c510be\\\",\\\"phrase\\\":\\\"einstein podolsky rosen steering\\\",\\\"surface_forms\\\":[\\\"einstein podolsky rosen steering\\\",\\\"einstein podolsky rosen steerings\\\",\\\"einstein-podolsky-rosen-steering\\\"],\\\"...\",\n     \"output\": \"{\\\"oa_counts_by_year\\\":{\\\"2000\\\":0,\\\"2001\\\":0,\\\"2002\\\":0,\\\"2003\\\":0,\\\"2004\\\":0,\\\"2005\\\":0,\\\"2006\\\":0,\\\"2007\\\":0,\\\"2008\\\":0,\\\"2009\\\":0,\\\"2010\\\":0,\\\"2011\\\":5,\\\"2012\\\":5,\\\"2013\\\":16,\\\"2014\\\":18,\\\"2015\\\":36,\\\"2016\\\":29,\\\"2017\\\":30,\\\"2018\\\":38,\\\"...\",\n     \"metadata_fold\": \"screen\",\n     \"metadata_arm\": \"main\",\n     \"metadata_concept_id\": \"c_9cceb3c510be\",\n     \"metadata_phrase\": \"einstein podolsky rosen steering\",\n     \"metadata_retrieval_route\": \"A_openalex_native\",\n     \"metadata_s2_to_oa_mapping_rate\": null,\n     \"metadata_match_evidence_mix\": {\n      \"oa_title\": 0.7003,\n      \"oa_abstract\": 0.2795,\n      \"oa_index_only\": 0.0202\n     },\n     \"metadata_hydration_complete\": true,\n     \"metadata_flags\": [\n      \"dup_groups_present\"\n     ],\n     \"metadata_sense_dominant_share\": 1.0,\n     \"metadata_sample_rank_u\": 0.001095740598455186,\n     \"metadata_design_selection_prob\": 1.0,\n     \"metadata_covered_venue_share\": 0.5821,\n     \"metadata_stratum\": \"F31:Physics and Astronomy|T1|2008-11\",\n     \"metadata_F_band\": \"2008-11\",\n     \"metadata_volume_tercile\": 1,\n     \"metadata_realized_inclusion_prob\": 0.5536,\n     \"metadata_focal_years_screen\": [\n      2014\n     ],\n     \"metadata_focal_years_heldout\": [\n      2016,\n      2017,\n      2018\n     ],\n     \"metadata_vocab_arm_tag\": \"arxiv\"\n    },\n    {\n     \"input\": \"{\\\"concept_id\\\":\\\"c_8b7be83fd666\\\",\\\"phrase\\\":\\\"mirage mediation\\\",\\\"surface_forms\\\":[\\\"mirage mediation\\\",\\\"mirage mediations\\\",\\\"mirage-mediation\\\"],\\\"acronyms_stored_not_used\\\":[],\\\"vocab_arms\\\":[\\\"arxiv_mined\\\"],\\\"links...\",\n     \"output\": \"{\\\"oa_counts_by_year\\\":{\\\"2000\\\":0,\\\"2001\\\":0,\\\"2002\\\":0,\\\"2003\\\":0,\\\"2004\\\":0,\\\"2005\\\":2,\\\"2006\\\":11,\\\"2007\\\":16,\\\"2008\\\":12,\\\"2009\\\":8,\\\"2010\\\":6,\\\"2011\\\":5,\\\"2012\\\":5,\\\"2013\\\":4,\\\"2014\\\":6,\\\"2015\\\":5,\\\"2016\\\":8,\\\"2017\\\":4,\\\"2018\\\":4,\\\"201...\",\n     \"metadata_fold\": \"screen\",\n     \"metadata_arm\": \"main\",\n     \"metadata_concept_id\": \"c_8b7be83fd666\",\n     \"metadata_phrase\": \"mirage mediation\",\n     \"metadata_retrieval_route\": \"A_openalex_native\",\n     \"metadata_s2_to_oa_mapping_rate\": null,\n     \"metadata_match_evidence_mix\": {\n      \"oa_title\": 0.4685,\n      \"oa_abstract\": 0.4414,\n      \"oa_index_only\": 0.0901\n     },\n     \"metadata_hydration_complete\": true,\n     \"metadata_flags\": [\n      \"sense_check_fail\",\n      \"dup_groups_present\"\n     ],\n     \"metadata_sense_dominant_share\": 0.45,\n     \"metadata_sample_rank_u\": 0.001683039944644027,\n     \"metadata_design_selection_prob\": 1.0,\n     \"metadata_covered_venue_share\": 0.6577,\n     \"metadata_stratum\": \"F31:Physics and Astronomy|T2|2005-07\",\n     \"metadata_F_band\": \"2005-07\",\n     \"metadata_volume_tercile\": 2,\n     \"metadata_realized_inclusion_prob\": 0.7727,\n     \"metadata_focal_years_screen\": [\n      2010,\n      2011,\n      2012\n     ],\n     \"metadata_focal_years_heldout\": [],\n     \"metadata_vocab_arm_tag\": \"arxiv\"\n    },\n    {\n     \"input\": \"{\\\"concept_id\\\":\\\"c_af151bc76848\\\",\\\"phrase\\\":\\\"full duplex cellular\\\",\\\"surface_forms\\\":[\\\"full duplex cellular\\\",\\\"full duplex cellulars\\\",\\\"full-dup\n{\n  \"metadata\": {\n    \"description\": \"Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.\",\n    \"feature_names\": {\n      \"concept_work_links\": [\n        \"concept_id\",\n        \"work_id\",\n        \"year\"\n      ],\n      \"openalex_works\": [\n        \"work_id\",\n        \"publication_year\",\n        \"type\"\n      ]\n    },\n    \"notes\": {\n      \"openalex_works\": \"input is a JSON array in feature_names order; output = primary_topic subfield_id; full refs/institutions/scores in works/works_part_XX.parquet\",\n      \"concept_work_links\": \"input = [concept_id, work_id, year]; output = match_evidence; concept details in concept_pool_2005_2016\"\n    }\n  },\n  \"datasets\": [\n    {\n      \"dataset\": \"concept_pool_2005_2016\",\n      \"examples\": [\n        {\n          \"input\": \"{\\\"concept_id\\\":\\\"c_9cceb3c510be\\\",\\\"phrase\\\":\\\"einstein podolsky rosen steering\\\",\\\"surface_forms\\\":[\\\"einstein podolsky rosen steering\\\",\\\"einstein podolsky rosen steerings\\\",\\\"einstein-podolsky-rosen-steering\\\"],\\\"...\",\n          \"output\": \"{\\\"oa_counts_by_year\\\":{\\\"2000\\\":0,\\\"2001\\\":0,\\\"2002\\\":0,\\\"2003\\\":0,\\\"2004\\\":0,\\\"2005\\\":0,\\\"2006\\\":0,\\\"2007\\\":0,\\\"2008\\\":0,\\\"2009\\\":0,\\\"2010\\\":0,\\\"2011\\\":5,\\\"2012\\\":5,\\\"2013\\\":16,\\\"2014\\\":18,\\\"2015\\\":36,\\\"2016\\\":29,\\\"2017\\\":30,\\\"2018\\\":38,\\\"...\",\n          \"metadata_fold\": \"screen\",\n          \"metadata_arm\": \"main\",\n          \"metadata_concept_id\": \"c_9cceb3c510be\",\n          \"metadata_phrase\": \"einstein podolsky rosen steering\",\n          \"metadata_retrieval_route\": \"A_openalex_native\",\n          \"metadata_s2_to_oa_mapping_rate\": null,\n          \"metadata_match_evidence_mix\": {\n            \"oa_title\": 0.7003,\n            \"oa_abstract\": 0.2795,\n            \"oa_index_only\": 0.0202\n          },\n          \"metadata_hydration_complete\": true,\n          \"metadata_flags\": [\n            \"dup_groups_present\"\n          ],\n          \"metadata_sense_dominant_share\": 1.0,\n          \"metadata_sample_rank_u\": 0.001095740598455186,\n          \"metadata_design_selection_prob\": 1.0,\n          \"metadata_covered_venue_share\": 0.5821,\n          \"metadata_stratum\": \"F31:Physics and Astronomy|T1|2008-11\",\n          \"metadata_F_band\": \"2008-11\",\n          \"metadata_volume_tercile\": 1,\n          \"metadata_realized_inclusion_prob\": 0.5536,\n          \"metadata_focal_years_screen\": [\n            2014\n          ],\n          \"metadata_focal_years_heldout\": [\n            2016,\n            2017,\n            2018\n          ],\n          \"metadata_vocab_arm_tag\": \"arxiv\"\n        },\n        {\n          \"input\": \"{\\\"concept_id\\\":\\\"c_8b7be83fd666\\\",\\\"phrase\\\":\\\"mirage mediation\\\",\\\"surface_forms\\\":[\\\"mirage mediation\\\",\\\"mirage mediations\\\",\\\"mirage-mediation\\\"],\\\"acronyms_stored_not_used\\\":[],\\\"vocab_arms\\\":[\\\"arxiv_mined\\\"],\\\"links...\",\n          \"output\": \"{\\\"oa_counts_by_year\\\":{\\\"2000\\\":0,\\\"2001\\\":0,\\\"2002\\\":0,\\\"2003\\\":0,\\\"2004\\\":0,\\\"2005\\\":2,\\\"2006\\\":11,\\\"2007\\\":16,\\\"2008\\\":12,\\\"2009\\\":8,\\\"2010\\\":6,\\\"2011\\\":5,\\\"2012\\\":5,\\\"2013\\\":4,\\\"2014\\\":6,\\\"2015\\\":5,\n{\n  \"metadata\": {\n    \"description\": \"Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.\",\n    \"feature_names\": {\n      \"concept_work_links\": [\n        \"concept_id\",\n        \"work_id\",\n        \"year\"\n      ],\n      \"openalex_works\": [\n        \"work_id\",\n        \"publication_year\",\n        \"type\"\n      ]\n    },\n    \"notes\": {\n      \"openalex_works\": \"input is a JSON array in feature_names order; output = primary_topic subfield_id; full refs/institutions/scores in works/works_part_XX.parquet\",\n      \"concept_work_links\": \"input = [concept_id, work_id, year]; output = match_evidence; concept details in concept_pool_2005_2016\"\n    }\n  },\n  \"datasets\": [\n    {\n      \"dataset\": \"openalex_works\",\n      \"examples\": [\n        {\n          \"input\": \"[2954104732,2019,\\\"article\\\",\\\"en\\\",true,198482871,11052,1.0,[11052,10603,12676],163634330,\\\"journal\\\",51,[2597866042,2776741657,2910849319],[5009622049,5055380996],[18653,5328,9727,2338,7255,1582,8431,1877...\",\n          \"output\": \"2208\",\n          \"metadata_field_id\": 22,\n          \"metadata_domain_id\": 3\n        },\n        {\n          \"input\": \"[2954106743,2019,\\\"article\\\",\\\"en\\\",true,195788446,10657,1.0,[10657,11682,11804],125754415,\\\"journal\\\",34,[561360952,823202098,1484947792,1510071712,1514707913,1936942997,1970188810,2001400374,2003592931,20...\",\n          \"output\": \"3107\",\n          \"metadata_field_id\": 31,\n          \"metadata_domain_id\": 3\n        },\n        {\n          \"input\": \"[2954108589,2019,\\\"preprint\\\",\\\"en\\\",true,195820351,10028,0.9998,[10028,10181,12031],4306400194,\\\"repository\\\",28,[2130942839],[5012889432,5001819765,5043599928,5005225470],[14402,5328,18031,1574,24740,1481...\",\n          \"output\": \"1702\",\n          \"metadata_field_id\": 17,\n          \"metadata_domain_id\": 3\n        }\n      ]\n    },\n    {\n      \"dataset\": \"subfield_year_totals\",\n      \"examples\": [\n        {\n          \"input\": \"{\\\"variant\\\":\\\"all_types\\\",\\\"year\\\":2000,\\\"subfield_id\\\":1100,\\\"subfield_name\\\":\\\"General Agricultural and Biological Sciences\\\",\\\"field_id\\\":11,\\\"domain_id\\\":1}\",\n          \"output\": \"11031\",\n          \"metadata_level\": \"subfield\",\n          \"metadata_task_type\": \"regression\",\n          \"metadata_year_total_with_topic\": 3657913,\n          \"metadata_year_unknown\": 0\n        },\n        {\n          \"input\": \"{\\\"variant\\\":\\\"all_types\\\",\\\"year\\\":2000,\\\"subfield_id\\\":1102,\\\"subfield_name\\\":\\\"Agronomy and Crop Science\\\",\\\"field_id\\\":11,\\\"domain_id\\\":1}\",\n          \"output\": \"10604\",\n          \"metadata_level\": \"subfield\",\n          \"metadata_task_type\": \"regression\",\n          \"metadata_year_total_with_topic\": 3657913,\n          \"metadata_year_unknown\": 0\n        },\n        {\n          \"input\": \"{\\\"variant\\\":\\\"all_types\\\",\\\"year\\\":2000,\\\"subfield_id\\\":1103,\\\"subfield_name\\\":\\\"Animal Science and Zoology\\\",\\\"field_id\\\":11,\\\"domain_id\\\":1}\",\n          \"output\": \"8355\",\n          \"metadata_level\": \"subfield\",\n          \"metadata_task_type\": \"regression\",\n          \"meta", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [11] TOOL CALL — Bash · 2026-09-30 03:19:03 UTC

```
Inspect data_out.json structure and links parquet:
cd /ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1; python3 -c "
import json
d=json.load(open('data_out.json'))
print(d.keys(), d.get('metadata',{}).keys() if isinstance(d.get('metadata'),dict) else None)
print([ (x['dataset'],len(x['examples'])) for x in d['datasets']])
e=d['datasets'][0]['examples'][0]
for k,v in e.items(): print(k, repr(v)[:600])
import collections
ex=d['datasets'][0]['examples']
print(collections.Counter(x['metadata_fold'] for x in ex))
print(collections.Counter(x['metadata_retrieval_route'] for x in ex))
print(collections.Counter(x['metadata_hydration_complete'] for x in ex))
print(sorted(len(json.dumps(x)) for x in ex)[::20])
"; ls works context; python3 -c "
import pandas as pd; cw=pd.read_parquet('concept_work.parquet'); print(cw.head()); print(cw.dtypes); print(len(cw))"
```

### [12] TOOL RESULT — Bash · 2026-09-30 03:19:03 UTC

```
{"stdout": "dict_keys(['metadata', 'datasets']) dict_keys(['description', 'sample_frame_sha256', 'retrieved_at', 'n_main', 'n_reference', 'origin_field_group_map'])\n[('concept_pool_2005_2016', 206)]\ninput '{\"concept_id\":\"c_9cceb3c510be\",\"phrase\":\"einstein podolsky rosen steering\",\"surface_forms\":[\"einstein podolsky rosen steering\",\"einstein podolsky rosen steerings\",\"einstein-podolsky-rosen-steering\"],\"acronyms_stored_not_used\":[],\"vocab_arms\":[\"arxiv_mined\"],\"links\":{},\"F\":2011,\"screen_counts_by_year\":{\"1995\":0,\"1996\":0,\"1997\":0,\"1998\":0,\"1999\":0,\"2000\":0,\"2001\":0,\"2002\":0,\"2003\":0,\"2004\":0,\"2005\":0,\"2006\":0,\"2007\":0,\"2008\":0,\"2009\":0,\"2010\":0,\"2011\":5,\"2012\":5,\"2013\":16},\"early_volume_V\":26,\"origin_field\":{\"id\":31,\"name\":\"Physics and Astronomy\",\"share\":0.5},\"origin_subfield\":{\"id\":3107,\"name\"\noutput '{\"oa_counts_by_year\":{\"2000\":0,\"2001\":0,\"2002\":0,\"2003\":0,\"2004\":0,\"2005\":0,\"2006\":0,\"2007\":0,\"2008\":0,\"2009\":0,\"2010\":0,\"2011\":5,\"2012\":5,\"2013\":16,\"2014\":18,\"2015\":36,\"2016\":29,\"2017\":30,\"2018\":38,\"2019\":36,\"2020\":23,\"2021\":31,\"2022\":27,\"2023\":21,\"2024\":32},\"s2_counts_by_year\":null,\"n_works\":347,\"work_ids\":[43964858,49474573,127562803,173155980,209643263,218609412,256424765,1000603767,1458806588,1481227016,1485281896,1502207898,1512095946,1526572687,1606822369,1614265359,1675325999,1702102493,1790331163,1792094258,1811166543,1830804825,1898651973,1960914455,1964019996,1968397786,1969112107,\nmetadata_fold 'screen'\nmetadata_arm 'main'\nmetadata_concept_id 'c_9cceb3c510be'\nmetadata_phrase 'einstein podolsky rosen steering'\nmetadata_retrieval_route 'A_openalex_native'\nmetadata_s2_to_oa_mapping_rate None\nmetadata_match_evidence_mix {'oa_title': 0.7003, 'oa_abstract': 0.2795, 'oa_index_only': 0.0202}\nmetadata_hydration_complete True\nmetadata_flags ['dup_groups_present']\nmetadata_sense_dominant_share 1.0\nmetadata_sample_rank_u 0.001095740598455186\nmetadata_design_selection_prob 1.0\nmetadata_covered_venue_share 0.5821\nmetadata_stratum 'F31:Physics and Astronomy|T1|2008-11'\nmetadata_F_band '2008-11'\nmetadata_volume_tercile 1\nmetadata_realized_inclusion_prob 0.5536\nmetadata_focal_years_screen [2014]\nmetadata_focal_years_heldout [2016, 2017, 2018]\nmetadata_vocab_arm_tag 'arxiv'\nCounter({'screen': 123, 'heldout_concept': 61, 'reference': 22})\nCounter({'B_s2_index': 180, 'A_openalex_native': 26})\nCounter({True: 206})\n[2349, 3072, 3334, 3781, 4480, 5395, 6647, 9173, 13425, 24032, 94259]\ncontext:\nquality_report.json\nquality_report.md\nrecall_audit.json\nsubfield_year_totals.json\nsubfield_year_totals_raw.json\nvenue_habitat.json\n\nworks:\nmini_works_part_00.json\nmini_works_part_01.json\nmini_works_part_02.json\nmini_works_part_03.json\npreview_works_part_00.json\npreview_works_part_01.json\npreview_works_part_02.json\npreview_works_part_03.json\nworks_part_00.parquet\nworks_part_01.parquet\nworks_part_02.parquet\nworks_part_03.parquet\n       concept_id     work_id  ...  year dup_group\n0  c_9cceb3c510be  1000603767  ...  2013       NaN\n1  c_9cceb3c510be   127562803  ...  2013       NaN\n2  c_9cceb3c510be  1458806588  ...  2015       NaN\n3  c_9cceb3c510be  1481227016  ...  2015       NaN\n4  c_9cceb3c510be  1485281896  ...  2015       NaN\n\n[5 rows x 6 columns]\nconcept_id         object\nwork_id             int64\nmatched_form       object\nmatch_evidence     object\nyear                int64\ndup_group         float64\ndtype: object\n214798", "stderr": "\nShell cwd was reset to /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [13] TOOL CALL — Bash · 2026-09-30 03:19:25 UTC

```
Create curated mini_demo_data.json subset:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; mkdir -p scripts; cat > scripts/make_mini_demo_data.py <<'EOF'
"""Build mini_demo_data.json: a diverse 100-concept subset of the concept_pool_2005_2016 dataset
(the raw data_out.json that data.py standardises). Same top-level structure as data_out.json."""
import json, collections, random
from pathlib import Path
SRC = Path("/ai-inventor/aii_data/runs/run_spUCG07dPEEP/3_invention_loop/iter_1/gen_art/gen_art_dataset_1/data_out.json")
d = json.loads(SRC.read_text())
ex = d["datasets"][0]["examples"]
quota = {"screen": 45, "heldout_concept": 33, "reference": 22}
rng = random.Random(0)
picked = []
for fold, q in quota.items():
    pool = [e for e in ex if e["metadata_fold"] == fold]
    # round-robin over (retrieval_route, F_band, volume_tercile) strata so every combination appears
    groups = collections.defaultdict(list)
    for e in pool:
        groups[(e["metadata_retrieval_route"], e["metadata_F_band"], e["metadata_volume_tercile"])].append(e)
    for g in groups.values():
        rng.shuffle(g)
        g.sort(key=lambda e: "sense_check_fail" not in e["metadata_flags"])  # flagged ones first
    keys = sorted(groups)
    sel = []
    while len(sel) < min(q, len(pool)):
        for k in keys:
            if groups[k] and len(sel) < q:
                sel.append(groups[k].pop(0))
    picked += sel
# keep original order of the frozen frame
order = {e["metadata_concept_id"]: i for i, e in enumerate(ex)}
picked.sort(key=lambda e: order[e["metadata_concept_id"]])
out = {"metadata": d["metadata"], "datasets": [{"dataset": "concept_pool_2005_2016", "examples": picked}]}
Path("mini_demo_data.json").write_text(json.dumps(out))
print(len(picked), collections.Counter(e["metadata_fold"] for e in picked),
      collections.Counter(e["metadata_retrieval_route"] for e in picked),
      collections.Counter(e["metadata_F_band"] for e in picked),
      sum("sense_check_fail" in e["metadata_flags"] for e in picked))
EOF
python3 scripts/make_mini_demo_data.py; ls -la mini_demo_data.json
python3 -c "
import json;d=json.load(open('mini_demo_data.json'));print(json.dumps(d['metadata'])[:1500]); e=d['datasets'][0]['examples'][5]; print(e['input'][:3000])"
```

### [14] TOOL RESULT — Bash [ERROR] · 2026-09-30 03:19:25 UTC

```
Error: Exit code 1
Traceback (most recent call last):
  File "/ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK/scripts/make_mini_demo_data.py", line 16, in <module>
    groups[(e["metadata_retrieval_route"], e["metadata_F_band"], e["metadata_volume_tercile"])].append(e)
                                           ~^^^^^^^^^^^^^^^^^^^
KeyError: 'metadata_F_band'
ls: cannot access 'mini_demo_data.json': No such file or directory
Traceback (most recent call last):
  File "<string>", line 2, in <module>
FileNotFoundError: [Errno 2] No such file or directory: 'mini_demo_data.json'
```

### [15] ASSISTANT · 2026-09-30 03:19:31 UTC

```
Building the curated demo subset — reference-arm concepts lack some metadata keys, fixing that now.
```

### [16] TOOL CALL — Bash · 2026-09-30 03:19:31 UTC

```
Fix and rerun subset builder, inspect:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; sed -i 's/e\["metadata_F_band"\], e\["metadata_volume_tercile"\]/e.get("metadata_F_band"), e.get("metadata_volume_tercile")/; s/e\["metadata_F_band"\] for e in picked/e.get("metadata_F_band") for e in picked/; s/keys = sorted(groups)/keys = sorted(groups, key=str)/' scripts/make_mini_demo_data.py
python3 scripts/make_mini_demo_data.py; ls -la mini_demo_data.json
python3 -c "
import json;d=json.load(open('mini_demo_data.json'));print(json.dumps(d['metadata'])[:1200]); ex=d['datasets'][0]['examples']; print(ex[5]['input'][:2500]); r=[e for e in ex if e['metadata_fold']=='reference'][0]; print(sorted(r.keys())); print(r['input'][:800])"
```

### [17] TOOL RESULT — Bash · 2026-09-30 03:19:31 UTC

```
{"stdout": "100 Counter({'screen': 45, 'heldout_concept': 33, 'reference': 22}) Counter({'B_s2_index': 74, 'A_openalex_native': 26}) Counter({'2008-11': 27, '2012-16': 26, '2005-07': 25, None: 22}) 20\n-rw-rw-rw- 1 aii-agent aii-agent 2061622 Sep 30 03:19 mini_demo_data.json\n{\"description\": \"Outcome-blind pool of scientific concepts first used 2005-2016 (main arm) plus a stationary reference arm, with complete OpenAlex work lists 2000-2024. See README.md.\", \"sample_frame_sha256\": \"80e3f244235b120be3e1201fdd8fb275ace4ba549f9a8884b96d2ea51c9a0c44\", \"retrieved_at\": \"2026-09-28\", \"n_main\": 184, \"n_reference\": 22, \"origin_field_group_map\": {\"31\": \"F31:Physics and Astronomy\", \"22\": \"D3:Physical Sciences\", \"17\": \"F17:Computer Science\", \"25\": \"D3:Physical Sciences\", \"26\": \"D3:Physical Sciences\", \"27\": \"OTHER_small\"}}\n{\"concept_id\":\"c_7eed579eaddd\",\"phrase\":\"tensor complementarity\",\"surface_forms\":[\"tensor complementarities\",\"tensor complementarity\",\"tensor-complementarity\"],\"acronyms_stored_not_used\":[],\"vocab_arms\":[\"arxiv_mined\"],\"links\":{},\"F\":2015,\"screen_counts_by_year\":{\"1995\":0,\"1996\":0,\"1997\":0,\"1998\":1,\"1999\":0,\"2000\":0,\"2001\":0,\"2002\":0,\"2003\":0,\"2004\":0,\"2005\":0,\"2006\":0,\"2007\":0,\"2008\":1,\"2009\":0,\"2010\":0,\"2011\":0,\"2012\":0,\"2013\":0,\"2014\":1,\"2015\":10,\"2016\":13,\"2017\":13},\"early_volume_V\":36,\"origin_field\":{\"id\":26,\"name\":\"Mathematics\",\"share\":0.9722},\"origin_subfield\":{\"id\":2605,\"name\":\"Computational Mathematics\",\"share\":0.9722},\"early_oa_verified_count\":36}\n['input', 'metadata_arm', 'metadata_concept_id', 'metadata_covered_venue_share', 'metadata_design_selection_prob', 'metadata_flags', 'metadata_fold', 'metadata_hydration_complete', 'metadata_match_evidence_mix', 'metadata_phrase', 'metadata_retrieval_route', 'metadata_s2_to_oa_mapping_rate', 'metadata_sample_rank_u', 'metadata_sense_dominant_share', 'output']\n{\"concept_id\":\"c_1a47828b675c\",\"phrase\":\"adenomyoma\",\"surface_forms\":[\"adenomyoma\",\"adenomyomas\"],\"acronyms_stored_not_used\":[],\"vocab_arms\":[\"legacy_concept\",\"openalex_keyword\"],\"links\":{\"openalex_keyword_id\":\"adenomyoma\",\"legacy_concept_id\":\"C2776720265\",\"legacy_concept_level\":3,\"wikidata_qid\":\"Q4682249\"},\"screen_counts_by_year_1995_2004\":{\"1995\":12,\"1996\":17,\"1997\":17,\"1998\":14,\"1999\":13,\"2000\":19,\"2001\":23,\"2002\":23,\"2003\":33,\"2004\":35}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [18] TOOL CALL — Bash · 2026-09-30 03:20:39 UTC

```
Build notebook with minimal config:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; cat > scripts/build_notebook.py <<'PYEOF'
"""Writes code_demo.ipynb (cells mirror data.py of the dataset artifact)."""
import json
from pathlib import Path

cells = []
def md(s): cells.append({"cell_type": "markdown", "metadata": {}, "source": s.strip("\n")})
def code(s): cells.append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": s.strip("\n")})

md(r'''
# New science concepts and their papers — dataset standardisation demo (`data.py`)

This notebook is a lightly annotated version of the artifact's `data.py`. The artifact is an **outcome-blind pool of emerging scientific concepts**: noun phrases first used between 2005 and 2016, found by counting OpenAlex title and abstract surface forms. The sampling frame was frozen and sha256-hashed before any post-F+2 data was looked at. A stationary **reference arm** sits alongside it, and every concept comes with its **complete OpenAlex work list for 2000-2024**.

`data.py` turns the artifact's canonical files into the pipeline's `exp_sel_data_out` schema, **one example per data row, grouped by dataset**:

| dataset | source file | row = | output |
|---|---|---|---|
| `concept_pool_2005_2016` | `data_out.json` | concept | `oa_counts_by_year` + `work_ids` (JSON) |
| `concept_work_links` | `concept_work.parquet` | concept→work link | `match_evidence` |
| `openalex_works` | `works/*.parquet` | work | primary-topic subfield id |
| `subfield_year_totals` | `context/subfield_year_totals.json` | (variant, year, subfield) | count |
| `venue_habitat` | `context/venue_habitat.json` | venue | dominant subfield |

**What this demo runs.** The full sources take about 160 MB of parquet and JSON. For the demo, `mini_demo_data.json` holds a curated **100-concept subset of `concept_pool_2005_2016`**: 45 screen, 33 held-out and 22 reference concepts. The subset covers both retrieval routes, all F bands and volume terciles, and 20 `sense_check_fail` concepts. The notebook runs the `concept_pool_2005_2016` builder and the original part-splitting writer on this subset, then plots the concepts' OpenAlex trajectories. The other four builders are shown verbatim for reference. They need the artifact's parquet and context files, which are not shipped with the demo.
''')

code(r'''
import subprocess, sys
def _pip(*a): subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-q', *a])

# orjson, loguru — NOT in Colab's pinned pre-installed list, always install
_pip('orjson==3.11.3', 'loguru==0.7.3')

# numpy, pandas, pyarrow, matplotlib — pre-installed on Colab, install locally only (at Colab's versions)
if 'google.colab' not in sys.modules:
    _pip('numpy==2.0.2', 'pandas==2.2.2', 'pyarrow==18.1.0', 'matplotlib==3.10.0')
''')

md(r'''
## Imports
This is the original `data.py` import block, unchanged. After it come the extra imports the notebook needs: `json` and `urllib` for loading the data, and `matplotlib` for the final plots.
''')

code(r'''
import sys
from pathlib import Path

import orjson
import pandas as pd
import pyarrow.parquet as pq
from loguru import logger

# --- notebook-only additions ---
import json
from collections import Counter
import matplotlib.pyplot as plt
''')

md(r'''
## Load the demo data
The demo data is fetched from the paper's GitHub repository. If that fails, the notebook falls back to a local `mini_demo_data.json`. The file has the same structure as the artifact's `data_out.json`: `{"metadata": ..., "datasets": [{"dataset": "concept_pool_2005_2016", "examples": [...]}]}`.
''')

code(r'''
GITHUB_DATA_URL = "https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json"
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
''')

code(r'''
data = load_data()
print(data["metadata"]["description"])
print("concepts in demo file:", len(data["datasets"][0]["examples"]))
''')

md(r'''
## Configuration
These are the tunable parameters. In the original script, `ROOT` is the artifact directory and `PART_LIMIT` is 90 MB. When the serialised output is larger than `PART_LIMIT`, `write_parts` splits it into `full_data_out/full_data_out_N.json`.

* `N_CONCEPTS` sets how many concepts from the demo file are standardised. The file holds 100; the original run used all 206.
* `PART_LIMIT` is lowered so that the 100-concept demo takes the multi-part splitting path. Restore `90_000_000` for the original behaviour.
* `NAMES` lists the builders to run. The original runs all of `BEST5`, but the demo only has the concept-pool data.
''')

code(r'''
N_CONCEPTS = 100          # concepts from mini_demo_data.json to standardise (demo max 100; original: all 206)
PART_LIMIT = 1_000_000    # bytes per output part (original: 90_000_000)
ROOT = Path("demo_out")   # output directory (original: Path(__file__).resolve().parent, the artifact dir)

BEST5 = ["concept_pool_2005_2016", "concept_work_links", "openalex_works", "subfield_year_totals", "venue_habitat"]
NAMES = ["concept_pool_2005_2016"]  # original: names = BEST5 (the other 4 need the artifact's parquet/context files)

ROOT.mkdir(exist_ok=True)
''')

md(r'''
## Logging and a compact JSON helper
Unchanged from the original. Loguru logs to stdout and to `ROOT/logs/data.log`. `J` serialises an object to a compact JSON string using `orjson`. Every `input` and `output` field in the schema is a string, so structured values are stored as JSON text.
''')

code(r'''
logger.remove()
logger.add(sys.stdout, level="INFO", format="{time:HH:mm:ss}|{level:<7}|{message}")
logger.add(ROOT / "logs" / "data.log", rotation="30 MB", level="DEBUG")

J = lambda o: orjson.dumps(o).decode()  # noqa: E731
''')

md(r'''
## Dataset 1: `concept_pool_2005_2016`
`data_out.json` is already one row per concept. `ds_concept_pool` passes those examples through, and `concept_meta` indexes them by concept id so the link builder can copy each concept's `fold` onto its links.

Each concept example has:
* **input** (a JSON string): the phrase, its surface forms, the first-use year `F`, screen counts up to F+2, the early volume `V`, and the origin field and subfield.
* **output** (a JSON string): `oa_counts_by_year` for 2000-2024, `n_works` and the full `work_ids` list.
* **metadata**: the fold (screen, held-out concept or reference), F band, volume tercile, focal years, retrieval route, quality flags, and so on.

*Notebook change:* both functions read the loaded `data` instead of `ROOT / "data_out.json"`, and `ds_concept_pool` keeps only the first `N_CONCEPTS` concepts.
''')

code(r'''
def concept_meta() -> dict:
    d = data  # original: orjson.loads((ROOT / "data_out.json").read_bytes())
    return {e["metadata_concept_id"]: e for e in d["datasets"][0]["examples"]}


def ds_concept_pool() -> list[dict]:
    d = data  # original: orjson.loads((ROOT / "data_out.json").read_bytes())
    return d["datasets"][0]["examples"][:N_CONCEPTS]
''')

md(r'''
## Dataset 2: `concept_work_links`, and Dataset 3: `openalex_works`
These builders are verbatim and **not executed in the demo**, because they read `concept_work.parquet` (214,798 links) and `works/works_part_*.parquet` (208,374 works). Both use the same compact encoding. The `input` is a JSON *array* whose column order is given once in the top-level metadata (`feature_names`), not repeated as keys in every row, which keeps the export small.
''')

code(r'''
LINK_FEATURES = ["concept_id", "work_id", "year"]


def ds_links(cm: dict) -> list[dict]:
    """input = JSON array ordered as LINK_FEATURES (names in top-level metadata to keep the file small)."""
    cw = pd.read_parquet(ROOT / "concept_work.parquet")
    out = []
    for i, r in enumerate(cw.itertuples(index=False)):
        c = cm[r.concept_id]
        out.append({"input": J([r.concept_id, int(r.work_id), int(r.year)]), "output": str(r.match_evidence),
                    "metadata_fold": c["metadata_fold"], "metadata_matched_form": r.matched_form,
                    "metadata_dup_group": None if pd.isna(r.dup_group) else int(r.dup_group)})
    return out


WORK_FEATURES = ["work_id", "publication_year", "type", "language", "doi_present", "s2_corpus_id", "primary_topic_id",
                 "topic_score", "topics_top3", "source_id", "source_type", "n_refs", "refs_in_corpus", "author_ids",
                 "keyword_idx", "concept_ids", "has_abstract", "abstract_n_tokens", "cited_by_count", "dup_group"]


def ds_works() -> list[dict]:
    """input = JSON array ordered as WORK_FEATURES; output = primary-topic subfield id (ASJC-style) or 'unknown'.
    Full referenced_works, institution_ids and keyword/concept scores stay in works/works_part_XX.parquet."""
    out = []
    cols = WORK_FEATURES + ["subfield_id", "field_id", "domain_id"]
    for p in sorted((ROOT / "works").glob("works_part_*.parquet")):
        for r in pq.read_table(p, columns=cols).to_pylist():
            if r["topic_score"] is not None:
                r["topic_score"] = round(float(r["topic_score"]), 4)
            sf = r["subfield_id"]
            out.append({"input": J([r[k] for k in WORK_FEATURES]), "output": str(sf) if sf is not None else "unknown",
                        "metadata_field_id": r["field_id"], "metadata_domain_id": r["domain_id"]})
    return out
''')

md(r'''
## Dataset 4: `subfield_year_totals`, and Dataset 5: `venue_habitat`
These are also verbatim and **not executed in the demo**. They need `context/subfield_year_totals.json`, `taxonomy.json` and `context/venue_habitat.json`.
* **Dataset 4** gives the denominators used for per-10^4 normalisation. It has one row per (variant, year, subfield), with 4 variants: all, typed, has_abstract and has_references.
* **Dataset 5** gives the venue habitat. It has one row per venue, with the venue's subfield shares and its dominant subfield, plus megajournal and coverage flags.
''')

code(r'''
def ds_denominators() -> list[dict]:
    d4 = orjson.loads((ROOT / "context" / "subfield_year_totals.json").read_bytes())
    tax = orjson.loads((ROOT / "taxonomy.json").read_bytes())
    out = []
    for v, years in d4["variants"].items():
        for y, t in sorted(years.items()):
            for sf, n in sorted(t["subfield"].items(), key=lambda x: int(x[0])):
                f = tax["subfield_field"].get(sf)
                out.append({"input": J({"variant": v, "year": int(y), "subfield_id": int(sf),
                                        "subfield_name": tax["subfields"].get(sf), "field_id": f,
                                        "domain_id": tax["field_domain"].get(str(f)) if f else None}),
                            "output": str(n), "metadata_level": "subfield", "metadata_task_type": "regression",
                            "metadata_year_total_with_topic": t["total_with_topic"], "metadata_year_unknown": t["unknown"]})
    return out


def ds_venues() -> list[dict]:
    d5 = orjson.loads((ROOT / "context" / "venue_habitat.json").read_bytes())
    out = []
    for v in d5["venues"]:
        inp = {k: v[k] for k in ["source_id", "issn_l", "display_name", "type", "host_org", "works_count",
                                 "max_works_per_year", "subfield_shares", "n_cpapers"]}
        out.append({"input": J(inp), "output": str(v["dominant_subfield"]) if v["dominant_subfield"] is not None else "unknown",
                    "metadata_dominant_share": v["dominant_share"], "metadata_megajournal": v["megajournal"],
                    "metadata_covered": v["covered"], "metadata_uncovered_reason": v["uncovered_reason"],
                    "metadata_task_type": "classification"})
    return out
''')

md(r'''
## Top-level metadata and the size-limited writer
This cell is verbatim. `write_parts` first deletes any old outputs, then estimates the total serialised size. Below `PART_LIMIT`, it writes a single `full_data_out.json`. Otherwise it streams the examples into parts of at most `PART_LIMIT` bytes each, `full_data_out/full_data_out_N.json`. A dataset can be split across part boundaries, so a part may hold the tail of one dataset and the head of the next.
''')

code(r'''
TOP_META = {
    "description": "Concept pool 2005-2016 artifact (see README.md). One example per data row, grouped by dataset.",
    "feature_names": {"concept_work_links": LINK_FEATURES, "openalex_works": WORK_FEATURES},
    "notes": {"openalex_works": "input is a JSON array in feature_names order; output = primary_topic subfield_id; full "
                                "refs/institutions/scores in works/works_part_XX.parquet",
              "concept_work_links": "input = [concept_id, work_id, year]; output = match_evidence; concept details in "
                                    "concept_pool_2005_2016"}}


def write_parts(datasets: list[dict]) -> None:
    for old in [ROOT / "full_data_out.json"] + sorted((ROOT / "full_data_out").glob("full_data_out_*.json")):
        old.unlink(missing_ok=True)
    total = sum(len(orjson.dumps(e)) + 1 for d in datasets for e in d["examples"])
    if total < PART_LIMIT:
        (ROOT / "full_data_out.json").write_bytes(orjson.dumps({"metadata": TOP_META, "datasets": datasets}))
        logger.info(f"wrote full_data_out.json ({total / 1e6:.1f} MB)")
        return
    (ROOT / "full_data_out").mkdir(exist_ok=True)
    parts, cur, size = [], [], 0
    for d in datasets:
        chunk = []
        for e in d["examples"]:
            b = len(orjson.dumps(e)) + 1
            if size + b > PART_LIMIT and (chunk or cur):
                if chunk:
                    cur.append({"dataset": d["dataset"], "examples": chunk})
                parts.append(cur)
                cur, chunk, size = [], [], 0
            chunk.append(e)
            size += b
        if chunk:
            cur.append({"dataset": d["dataset"], "examples": chunk})
    if cur:
        parts.append(cur)
    for k, p in enumerate(parts, 1):
        (ROOT / "full_data_out" / f"full_data_out_{k}.json").write_bytes(orjson.dumps({"metadata": TOP_META, "datasets": p}))
    logger.info(f"wrote {len(parts)} parts to full_data_out/ ({total / 1e6:.1f} MB total)")
''')

md(r'''
## Run the pipeline (`main`)
This is the original `main`. The only change is `names = NAMES` instead of `names = BEST5`, so only the builders whose inputs are present get run. Each builder's examples are wrapped as `{"dataset": name, "examples": [...]}` and handed to `write_parts`.
''')

code(r'''
@logger.catch(reraise=True)
def main() -> None:
    cm = concept_meta()
    builders = {
        "concept_pool_2005_2016": ds_concept_pool,
        "concept_work_links": lambda: ds_links(cm),
        "openalex_works": ds_works,
        "subfield_year_totals": ds_denominators,
        "venue_habitat": ds_venues,
    }
    names = NAMES  # original: names = BEST5
    datasets = []
    for n in names:
        try:
            ex = builders[n]()
        except (FileNotFoundError, KeyError, ValueError) as e:
            logger.error(f"{n}: failed ({e})")
            raise
        logger.info(f"{n}: {len(ex)} examples")
        datasets.append({"dataset": n, "examples": ex})
    write_parts(datasets)


main()
''')

md(r'''
## Results: read back the standardised output and look at the concepts
This cell reads back whatever `write_parts` produced, either one file or several parts. It then parses each example's JSON `input` and `output` and prints a per-concept table. The plots show:
1. the fold and retrieval-route composition of the exported pool;
2. OpenAlex works per year (2000-2024) for each concept, aligned at its first-use year `F`, with the main-arm median. Reference concepts have no `F`, because they are stationary controls that already existed before 2005, so they are shown in calendar time.
''')

code(r'''
files = sorted((ROOT / "full_data_out").glob("full_data_out_*.json")) if (ROOT / "full_data_out").exists() else []
if (ROOT / "full_data_out.json").exists():
    files = [ROOT / "full_data_out.json"]
rows = []
for f in files:
    for ds in orjson.loads(f.read_bytes())["datasets"]:
        for e in ds["examples"]:
            inp, out = json.loads(e["input"]), json.loads(e["output"])
            rows.append({"file": f.name, "phrase": inp["phrase"], "fold": e["metadata_fold"],
                         "route": e["metadata_retrieval_route"], "F": inp.get("F"), "V": inp.get("early_volume_V"),
                         "origin_field": (inp.get("origin_field") or {}).get("name"), "n_works": out["n_works"],
                         "sense_fail": "sense_check_fail" in e["metadata_flags"],
                         "counts": {int(y): c for y, c in out["oa_counts_by_year"].items()}})
df = pd.DataFrame(rows)
print(f"{len(files)} output file(s): {[f.name for f in files]}  |  {len(df)} concept examples")
print(df.groupby("file").size().rename("examples").to_string(), "\n")
pd.set_option("display.width", 160)
print(df.drop(columns="counts").sort_values(["fold", "F"]).head(30).to_string(index=False))
print("\nfold x route:\n", pd.crosstab(df["fold"], df["route"]).to_string())
print("\nn_works summary by fold:\n", df.groupby("fold")["n_works"].describe()[["count", "min", "50%", "max"]].to_string())
''')

code(r'''
years = list(range(2000, 2025))
fig, axes = plt.subplots(1, 3, figsize=(17, 4.6))

# (1) composition
ct = pd.crosstab(df["fold"], df["route"])
ct.plot(kind="bar", stacked=True, ax=axes[0], color=["#4C72B0", "#DD8452"], rot=0)
axes[0].set_title("Exported concepts by fold and retrieval route")
axes[0].set_ylabel("concepts"); axes[0].set_xlabel("")

# (2) main-arm trajectories aligned at first-use year F
main_df = df[df["fold"] != "reference"]
rel = range(-5, 15)
mat = []
for _, r in main_df.iterrows():
    traj = [r["counts"].get(r["F"] + k, float("nan")) if r["F"] else float("nan") for k in rel]
    mat.append(traj)
    axes[1].plot(list(rel), traj, color="#DD8452" if r["fold"] == "screen" else "#4C72B0", alpha=0.25, lw=0.8)
if mat:
    axes[1].plot(list(rel), pd.DataFrame(mat).median(axis=0, skipna=True).values, color="k", lw=2.2, label="median")
    axes[1].legend()
axes[1].set_yscale("symlog", linthresh=1)
axes[1].axvline(0, color="grey", ls="--", lw=1)
axes[1].set_title("Main arm: OpenAlex works/year vs years since F\n(orange=screen, blue=held-out)")
axes[1].set_xlabel("year - F"); axes[1].set_ylabel("works (symlog)")

# (3) reference arm in calendar time
for _, r in df[df["fold"] == "reference"].iterrows():
    axes[2].plot(years, [r["counts"].get(y, 0) for y in years], alpha=0.6, lw=1)
axes[2].set_yscale("log")
axes[2].set_title("Reference arm (stationary controls): works/year")
axes[2].set_xlabel("year"); axes[2].set_ylabel("works (log)")
plt.tight_layout(); plt.show()
''')

nb = {"cells": cells, "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python", "version": "3.12"}}, "nbformat": 4, "nbformat_minor": 5}
for i, c in enumerate(nb["cells"]):
    c["id"] = f"cell-{i:02d}"
Path("code_demo.ipynb").write_text(json.dumps(nb, indent=1))
print("wrote code_demo.ipynb with", len(cells), "cells")
PYEOF
sed -i 's/^N_CONCEPTS = 100 /N_CONCEPTS = 2   /' scripts/build_notebook.py
python3 scripts/build_notebook.py; pip index versions orjson 2>/dev/null | head -1; pip index versions loguru 2>/dev/null | head -1
```

### [19] TOOL RESULT — Bash · 2026-09-30 03:20:43 UTC

```
{"stdout": "wrote code_demo.ipynb with 24 cells\norjson (3.12.0)\nloguru (0.7.3)", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": true}
```

### [20] TOOL CALL — Bash · 2026-09-30 03:20:47 UTC

```
Test-run notebook with minimal config:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; E=/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && start=$(date +%s) && $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | tail -20; echo "runtime $(( $(date +%s)-start ))s"
```

### [21] TOOL RESULT — Bash · 2026-09-30 03:21:15 UTC

```
{"stdout": "[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[IPKernelApp] WARNING | Kernel is running over TCP without encryption. All communication (including code and outputs) is sent in plain text and is susceptible to eavesdropping. Use IPC transport or launch with kernel manager-provisioned CurveZMQ keys to enable transport encryption.\n[NbConvertApp] Writing 124344 bytes to code_demo.ipynb\nruntime 23s", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [22] TOOL CALL — Bash · 2026-09-30 03:21:17 UTC

```
Inspect notebook outputs:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; python3 -c "
import json;nb=json.load(open('code_demo.ipynb'))
for c in nb['cells']:
  if c['cell_type']=='code':
    for o in c['outputs']:
      if o.get('name')=='stdout' or o['output_type']=='error': print(''.join(o.get('text',''))[:1500] or o)
      else: print('[', o['output_type'], list(o.get('data',{}).keys()),']')
"
```

### [23] TOOL RESULT — Bash · 2026-09-30 03:21:17 UTC

```
{"stdout": "Outcome-blind pool of scientific concepts first used 2005-2016 (main arm) plus a stationary reference arm, with complete OpenAlex work lists 2000-2024. See README.md.\nconcepts in demo file: 100\n\n03:21:11|INFO   |concept_pool_2005_2016: 2 examples\n\n03:21:11|INFO   |wrote full_data_out.json (0.1 MB)\n\n1 output file(s): ['full_data_out.json']  |  2 concept examples\nfile\nfull_data_out.json    2 \n\n              file               phrase            fold             route    F   V      origin_field  n_works  sense_fail\nfull_data_out.json graphene quantum dot heldout_concept A_openalex_native 2008 122 Materials Science     8263       False\nfull_data_out.json full duplex cellular          screen A_openalex_native 2015  69       Engineering      154       False\n\nfold x route:\n route            A_openalex_native\nfold                              \nheldout_concept                  1\nscreen                           1\n\nn_works summary by fold:\n                  count     min     50%     max\nfold                                          \nheldout_concept    1.0  8263.0  8263.0  8263.0\nscreen             1.0   154.0   154.0   154.0\n\n[ display_data ['image/png', 'text/plain'] ]", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [24] ASSISTANT · 2026-09-30 03:21:23 UTC

```
Works at minimum config. Scaling to 20, then to the full 100.
```

### [25] TOOL CALL — Bash · 2026-09-30 03:21:23 UTC

```
Scale N_CONCEPTS to 20 and 100, test each:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; E=/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea
for N in 20 100; do
sed -i "s/^N_CONCEPTS = [0-9]* */N_CONCEPTS = $N /" scripts/build_notebook.py; grep -m1 "^N_CONCEPTS" scripts/build_notebook.py; python3 scripts/build_notebook.py
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel && start=$(date +%s) && $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING | tail -5; echo "N=$N runtime $(( $(date +%s)-start ))s"
done
python3 -c "
import json;nb=json.load(open('code_demo.ipynb'))
for c in nb['cells']:
  if c['cell_type']=='code':
    for o in c['outputs']:
      if o.get('name')=='stdout' or o['output_type']=='error': print(''.join(o.get('text',''))[:2500] or o)
      else: print('[', o['output_type'], list(o.get('data',{}).keys()),']')
"; ls -la demo_out demo_out/full_data_out
```

### [26] TOOL RESULT — Bash · 2026-09-30 03:22:03 UTC

```
{"stdout": "N_CONCEPTS = 20 # concepts from mini_demo_data.json to standardise (demo max 100; original: all 206)\nwrote code_demo.ipynb with 24 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 200799 bytes to code_demo.ipynb\nN=20 runtime 18s\nN_CONCEPTS = 100 # concepts from mini_demo_data.json to standardise (demo max 100; original: all 206)\nwrote code_demo.ipynb with 24 cells\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 400362 bytes to code_demo.ipynb\nN=100 runtime 18s\nOutcome-blind pool of scientific concepts first used 2005-2016 (main arm) plus a stationary reference arm, with complete OpenAlex work lists 2000-2024. See README.md.\nconcepts in demo file: 100\n\n03:21:59|INFO   |concept_pool_2005_2016: 100 examples\n\n03:22:00|INFO   |wrote 2 parts to full_data_out/ (1.4 MB total)\n\n2 output file(s): ['full_data_out_1.json', 'full_data_out_2.json']  |  100 concept examples\nfile\nfull_data_out_1.json    67\nfull_data_out_2.json    33 \n\n                file                             phrase            fold             route      F     V          origin_field  n_works  sense_fail\nfull_data_out_1.json       quark lepton complementarity heldout_concept A_openalex_native 2005.0  44.0 Physics and Astronomy      101       False\nfull_data_out_1.json                       egret excess heldout_concept        B_s2_index 2005.0  24.0 Physics and Astronomy       25       False\nfull_data_out_2.json                      gaussian mimo heldout_concept        B_s2_index 2005.0  26.0           Engineering      228       False\nfull_data_out_1.json              electrons in graphene heldout_concept        B_s2_index 2006.0  67.0     Materials Science      630       False\nfull_data_out_1.json                  quantum spin hall heldout_concept        B_s2_index 2006.0  83.0 Physics and Astronomy     2272       False\nfull_data_out_1.json                     tropical curve heldout_concept        B_s2_index 2006.0  36.0      Computer Science      325       False\nfull_data_out_2.json                exoplanet host star heldout_concept        B_s2_index 2006.0  22.0 Physics and Astronomy      391       False\nfull_data_out_1.json           body area sensor network heldout_concept A_openalex_native 2007.0  44.0           Engineering      488       False\nfull_data_out_1.json                        group lasso heldout_concept        B_s2_index 2007.0  41.0           Mathematics     1739       False\nfull_data_out_2.json  proton coupled folate transporter heldout_concept        B_s2_index 2007.0  52.0              Medicine      327       False\nfull_data_out_1.json               graphene quantum dot heldout_concept A_openalex_native 2008.0 122.0     Materials Science     8263       False\nfull_data_out_1.json superconformal chern simons theory heldout_concept        B_s2_index 2008.0  56.0 Physics and Astronomy       89       False\nfull_data_out_2.json                      iron arsenide heldout_concept        B_s2_index 2008.0 211.0     Materials Science      432       False\nfull_data_out_2.json                restricted isometry heldout_concept        B_s2_index 2008.0 154.0           Engineering     1434       False\nfull_data_out_2.json          high dimensional gaussian heldout_concept        B_s2_index 2008.0  24.0      Computer Science      352        True\nfull_data_o\n[ display_data ['image/png', 'text/plain'] ]\ndemo_out:\ntotal 5918\ndrwxrwxrwx 4 aii-agent aii-agent 2000129 Sep 30 03:21 .\ndrwxrwxrwx 5 aii-agent aii-agent 2000382 Sep 30 03:21 ..\ndrwxrwxrwx 2 aii-agent aii-agent 2000129 Sep 30 03:22 full_data_out\ndrwxrwxrwx 2 aii-agent aii-agent   58000 Sep 30 03:21 logs\n\ndemo_out/full_data_out:\ntotal 5231\ndrwxrwxrwx 2 aii-agent aii-agent 2000129 Sep 30 03:22 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000129 Sep 30 03:21 ..\n-rw-rw-rw- 1 aii-agent aii-agent  993651 Sep 30 03:21 full_data_out_1.json\n-rw-rw-rw- 1 aii-agent aii-agent  361869 Sep 30 03:22 full_data_out_2.json", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [27] TOOL CALL — Bash · 2026-09-30 03:22:07 UTC

```
Extract plot image to scratchpad:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; python3 -c "
import json,base64;nb=json.load(open('code_demo.ipynb'))
o=[o for c in nb['cells'] if c['cell_type']=='code' for o in c['outputs'] if o['output_type']=='display_data'][0]
open('/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-1-art-94GEMUsgAmgK/e7bc591c-43e1-4bfe-bf9a-92551bb5e111/scratchpad/plot.png','wb').write(base64.b64decode(o['data']['image/png']))"
```

### [28] TOOL RESULT — Bash · 2026-09-30 03:22:09 UTC

```
{"stdout": "", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [29] TOOL CALL — Read · 2026-09-30 03:22:11 UTC

```
/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-1-art-94GEMUsgAmgK/e7bc591c-43e1-4bfe-bf9a-92551bb5e111/scratchpad/plot.png
```

### [30] TOOL RESULT — Read · 2026-09-30 03:22:11 UTC

```
[event truncated: exceeded SSE frame limit]
```

### [31] TOOL CALL — Bash · 2026-09-30 03:22:19 UTC

```
Compare remote GitHub data with local file:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; curl -s https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json | python3 -c "
import json,sys,collections;d=json.load(sys.stdin);print(d.keys(), [x['dataset'] for x in d['datasets']]); ex=d['datasets'][0]['examples']; print(len(ex), collections.Counter(e['metadata_fold'] for e in ex)); print(sorted(ex[0].keys())==sorted(json.load(open('mini_demo_data.json'))['datasets'][0]['examples'][0].keys()))"
```

### [32] TOOL RESULT — Bash · 2026-09-30 03:22:19 UTC

```
{"stdout": "dict_keys(['metadata', 'datasets']) ['concept_pool_2005_2016']\n100 Counter({'screen': 49, 'heldout_concept': 39, 'reference': 12})\nTrue", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [33] ASSISTANT · 2026-09-30 03:22:31 UTC

```
Remote URL currently serves an earlier round's file (same schema). I'll also test the local-fallback path with a copy that uses a broken URL, and tidy the integer display of F/V.
```

### [34] TOOL CALL — Bash · 2026-09-30 03:22:31 UTC

```
Test local fallback path and final run:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK; python3 - <<'EOF'
p='scripts/build_notebook.py'; s=open(p).read()
s=s.replace('df = pd.DataFrame(rows)\n','df = pd.DataFrame(rows)\ndf[["F", "V"]] = df[["F", "V"]].astype("Int64")  # reference concepts have no F / V\n')
open(p,'w').write(s)
EOF
python3 scripts/build_notebook.py
S=/tmp/claude-10001/-ai-inventor-aii-data-runs-run-YczZzZ0-9kfq-4-gen-paper-repo--4-gen-demo-art-notebook-workspaces-iter-1-art-94GEMUsgAmgK/e7bc591c-43e1-4bfe-bf9a-92551bb5e111/scratchpad
sed 's#https://raw.githubusercontent.com/ai-inventor-papers#https://raw.githubusercontent.com/nonexistent-xyz#' code_demo.ipynb > $S/local_test.ipynb
E=/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel
start=$(date +%s); $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 $S/local_test.ipynb --output-dir . --output local_test_out.ipynb 2>&1 | grep -v WARNING|tail -2; echo "local runtime $(( $(date +%s)-start ))s"
python3 -c "
import json;nb=json.load(open('local_test_out.ipynb'))
for c in nb['cells']:
  if c['cell_type']=='code':
    for o in c['outputs']:
      if o.get('name')=='stdout' or o['output_type']=='error': print(''.join(o.get('text',''))[:900] or o)
" ; rm local_test_out.ipynb
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel
start=$(date +%s); $E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 code_demo.ipynb --output code_demo.ipynb 2>&1 | grep -v WARNING|tail -2; echo "final runtime $(( $(date +%s)-start ))s"
grep -c '"output_type": "error"' code_demo.ipynb
```

### [35] TOOL RESULT — Bash · 2026-09-30 03:23:11 UTC

```
{"stdout": "wrote code_demo.ipynb with 24 cells\n\u001b[31mFileNotFoundError\u001b[39m: Could not load mini_demo_data.json\n\nlocal runtime 20s\nTraceback (most recent call last):\n  File \"<string>\", line 2, in <module>\nFileNotFoundError: [Errno 2] No such file or directory: 'local_test_out.ipynb'\nrm: cannot remove 'local_test_out.ipynb': No such file or directory\n[NbConvertApp] Converting notebook code_demo.ipynb to notebook\n[NbConvertApp] Writing 400341 bytes to code_demo.ipynb\nfinal runtime 17s\n0", "stderr": "", "interrupted": false, "isImage": false, "returnCodeInterpretation": "No matches found", "noOutputExpected": false}
```

### [36] ASSISTANT · 2026-09-30 03:23:17 UTC

```
The fallback test failed only because the copy sat in the scratchpad, where there's no local data file. Rerunning the copy from inside the workspace:
```

### [37] TOOL CALL — Bash · 2026-09-30 03:23:17 UTC

```
Test local fallback from workspace dir:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK
sed 's#https://raw.githubusercontent.com/ai-inventor-papers#https://raw.githubusercontent.com/nonexistent-xyz#' code_demo.ipynb > _local_test.ipynb
E=/tmp/aii_nb_test_envs/art_94GEMUsgAmgK-05ebb1f667ea
UV_VENV_CLEAR=1 UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv venv -q --seed --python /usr/local/bin/python3.12 $E && UV_CACHE_DIR=/tmp/aii_nb_test_envs/uv-cache uv pip install -q --python $E/bin/python jupyter ipykernel
$E/bin/jupyter nbconvert --to notebook --execute --ExecutePreprocessor.timeout=600 _local_test.ipynb --output _local_test.ipynb 2>&1 | grep -v WARNING|tail -2
python3 -c "
import json;nb=json.load(open('_local_test.ipynb'))
for c in nb['cells']:
  if c['cell_type']=='code':
    for o in c['outputs']:
      if o.get('name')=='stdout' or o['output_type']=='error': print(''.join(o.get('text',''))[:700] or o)
"; rm _local_test.ipynb
```

### [38] TOOL RESULT — Bash · 2026-09-30 03:23:35 UTC

```
{"stdout": "[NbConvertApp] Converting notebook _local_test.ipynb to notebook\n[NbConvertApp] Writing 419005 bytes to _local_test.ipynb\nOutcome-blind pool of scientific concepts first used 2005-2016 (main arm) plus a stationary reference arm, with complete OpenAlex work lists 2000-2024. See README.md.\nconcepts in demo file: 100\n\n03:23:33|INFO   |concept_pool_2005_2016: 100 examples\n\n03:23:33|INFO   |wrote 3 parts to full_data_out/ (2.1 MB total)\n\n3 output file(s): ['full_data_out_1.json', 'full_data_out_2.json', 'full_data_out_3.json']  |  100 concept examples\nfile\nfull_data_out_1.json    46\nfull_data_out_2.json    48\nfull_data_out_3.json     6 \n\n                file                                 phrase            fold             route    F   V          origin_field  n_works  sense_fail\nfull_data_out_1.json           quark lepton complementarity heldout_concept A_openalex_native 2005  44 Physics and Astronomy      101       False\nfull_data_out_2.json                           egret excess heldout_concept        B_s2_index 2005  24 Physics and Astronomy       25       False\nfull_data_out_2.json                          gaussian mim", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [39] ASSISTANT · 2026-09-30 03:23:43 UTC

```
Both data paths work, and each full run takes about 18 s. Last steps: verify, clean up, and write the README, manifest and output JSON.
```

### [40] TOOL CALL — Bash · 2026-09-30 03:23:43 UTC

```
Verify URL, clean outputs, inspect workspace:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK
grep -c 'GITHUB_DATA_URL = \\"https://raw.githubusercontent.com/ai-inventor-papers/ai-invention-8892b7-occupancy-is-not-integration-for-new/fork/run_YczZzZ0_9kfq/round-1/dataset-1/demo/mini_demo_data.json\\"' code_demo.ipynb
grep -c "urllib.request.urlopen(GITHUB_DATA_URL)" code_demo.ipynb
rm -rf demo_out; ls -la .aii; du -sh .; ls -la
```

### [41] TOOL RESULT — Bash · 2026-09-30 03:23:43 UTC

```
{"stdout": "1\n1\ntotal 1954\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:17 .\ndrwxrwxrwx 4 aii-agent aii-agent 2000261 Sep 30 03:23 ..\n5.5M\t.\ntotal 7548\ndrwxrwxrwx 4 aii-agent aii-agent 2000261 Sep 30 03:23 .\ndrwxrwxrwx 5 aii-agent aii-agent 2000498 Sep 30 03:17 ..\ndrwxrwxrwx 2 aii-agent aii-agent       1 Sep 30 03:17 .aii\n-rw-rw-rw- 1 aii-agent aii-agent      54 Sep 30 03:18 .aii_claude_session.json\n-rw-rw-rw- 1 aii-agent aii-agent  264219 Sep 30 03:23 .repl_agent.ptylog\n-rw-rw-rw- 1 aii-agent aii-agent  400349 Sep 30 03:23 code_demo.ipynb\n-rw-rw-rw- 1 aii-agent aii-agent 2061622 Sep 30 03:19 mini_demo_data.json\ndrwxrwxrwx 2 aii-agent aii-agent 1002084 Sep 30 03:21 scripts", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [42] TOOL CALL — Bash · 2026-09-30 03:23:55 UTC

```
Write manifest, README, struct output:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK
cat > .aii/manifest.yaml <<'EOF'
# Nothing in this workspace is heavy (total ~5 MB, all text/JSON/notebook) — no keep/delete decisions required.
# demo_out/ is created only when code_demo.ipynb is run; it is small and regenerable.
entries:
  - path: demo_out/
    delete: regenerable
    source: "jupyter nbconvert --to notebook --execute code_demo.ipynb"
EOF
cat > README.md <<'EOF'
# Demo: New science concepts and their papers (`data.py` standardisation)

This is a Colab-ready demo notebook for the dataset artifact **"New science concepts and their papers"**. The artifact is an outcome-blind pool of emerging scientific concepts, first used between 2005 and 2016, plus a stationary reference arm. Each concept comes with its complete OpenAlex work list for 2000-2024.

The notebook is the artifact's `data.py`, split into cells with explanations between them. The code is kept as close to the original as possible. It standardises the concept pool into the `exp_sel_data_out` schema, with one example per row, and writes it with the original size-limited part writer. The last cells plot each concept's OpenAlex works-per-year trajectory, aligned at its first-use year F.

## Layout
| path | what |
|---|---|
| `code_demo.ipynb` | Demo notebook, already executed (100 concepts, ~20 s end to end) |
| `mini_demo_data.json` | Curated 100-concept subset of `concept_pool_2005_2016`: 45 screen, 33 held-out and 22 reference concepts. Covers both retrieval routes, all F bands and volume terciles, and 20 `sense_check_fail` concepts. Same structure as the artifact's `data_out.json` |
| `scripts/make_mini_demo_data.py` | Builds `mini_demo_data.json` from the artifact's `data_out.json` by stratified selection (seed 0) |
| `scripts/build_notebook.py` | Generates `code_demo.ipynb` |

## How to run
Open `code_demo.ipynb` in Colab or Jupyter and run all cells. The data is fetched from this repository's raw GitHub URL, and a local `mini_demo_data.json` is used if that fails. You can tune `N_CONCEPTS` and `PART_LIMIT` in the config cell. The originals are all 206 concepts and 90,000,000 bytes.

Only the `concept_pool_2005_2016` builder runs in the demo. The builders for `concept_work_links`, `openalex_works`, `subfield_year_totals` and `venue_habitat` are included verbatim, but they need the artifact's parquet and context files (about 160 MB), which are not shipped with the demo.

## Restoring removed files
- `demo_out/`: the notebook's output directory. It is regenerable, so re-run the notebook: `jupyter nbconvert --to notebook --execute code_demo.ipynb`.
EOF
cat > .terminal_claude_agent_struct_out.json <<'EOF'
{"out_expected_files": {"notebook": "code_demo.ipynb", "mini_data_file": "mini_demo_data.json"}}
EOF
cat .terminal_claude_agent_struct_out.json
```

### [43] TOOL RESULT — Bash · 2026-09-30 03:23:55 UTC

```
{"stdout": "{\"out_expected_files\": {\"notebook\": \"code_demo.ipynb\", \"mini_data_file\": \"mini_demo_data.json\"}}", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [44] ASSISTANT · 2026-09-30 03:24:06 UTC

```
I've converted the artifact's `data.py` into a demo notebook, `code_demo.ipynb`, and built `mini_demo_data.json` to go with it. The full notebook runs in about 18–20 seconds against the 600-second limit, with no errors.

**Demo data.** `mini_demo_data.json` is a 100-concept subset of one dataset, `concept_pool_2005_2016`, in the same structure as the artifact's `data_out.json`. It has 45 screen, 33 held-out and 22 reference concepts. The subset covers both retrieval routes, all three F bands and all volume terciles, and includes 20 concepts flagged `sense_check_fail`. I built it with a small script, `scripts/make_mini_demo_data.py` (fixed seed), without opening the full output files.

**Notebook.** The original code is kept almost unchanged, split into cells with explanations between them. The changes are:
- **Data source:** `concept_meta` and `ds_concept_pool` read the loaded data instead of `data_out.json`.
- **Builders run:** only the concept-pool builder runs (`names = NAMES` instead of `BEST5`). The other four builders are included verbatim but not run, because they need about 160 MB of parquet and context files that aren't in the demo.
- **Config cell:**
  - `N_CONCEPTS` is 100; the original used all 206.
  - `PART_LIMIT` is 1,000,000 bytes, so the demo exercises the multi-part writer; the original is 90,000,000.
  - Output goes to `demo_out/`.
- **Results cells:** these read the output back, print a per-concept table and a fold × route table, and draw three plots. The plots show the fold/route mix, main-arm works-per-year curves aligned at each concept's first-use year F with the median, and the reference arm in calendar time.

**Scaling:** I tested at 2, 20 and 100 concepts, each run in a fresh environment. Runtime stayed around 18–23 seconds, so the demo uses all 100.

**Stale file at the GitHub URL:** the URL currently serves a file from an earlier run, with a different fold mix (49/39/12). So the saved outputs in the executed notebook come from that older file, not from the new `mini_demo_data.json`. It has the same structure and the notebook runs cleanly on it. I also checked the local fallback by pointing a copy of the notebook at a broken URL; it loaded the local file and ran to completion. The URL will serve the new subset once the files are pushed.

**Checks passed:** the notebook contains the required `GITHUB_DATA_URL` line exactly, loads from that URL with a local fallback, and the data file exists.

I also wrote `README.md`, `.aii/manifest.yaml` and `.terminal_claude_agent_struct_out.json`. Nothing in the workspace is large (about 5 MB, all text). The only manifest entry is the notebook's `demo_out/` output folder, marked as regenerable.

Files are in `art_94GEMUsgAmgK/`:
- `code_demo.ipynb`
- `mini_demo_data.json`
- `README.md`
- `scripts/make_mini_demo_data.py`
- `scripts/build_notebook.py`
```

### [45] SYSTEM-USER prompt · 2026-09-30 03:24:09 UTC

```
<CRITICAL_ERROR>
The module-end file check FAILED (attempt 1/3).

PROBLEMS:
  - .aii/manifest.yaml: 'demo_out/' matches nothing that needs a decision — remove it (text, code and files under the auto-keep floor are always kept)

FIX IT:
1. Add one entry per uncovered path to `.aii/manifest.yaml` (create it if missing).
   Every path is RELATIVE TO YOUR CWD and must resolve inside it. Globs and
   whole directories are fine — a whole `hf_cache/` is ONE entry.

   entries:
     - path: results/
       keep: six GPU-hours of sweep output, not reproducible in this run
     - path: hf_cache/
       delete: redownloadable
       source: "huggingface-cli download meta-llama/Llama-3-8B"
     - path: checkpoints/
       delete: regenerable
       source: "uv run train.py --epochs 3"

   `keep:` takes a one-line reason. `delete:` takes `redownloadable` or
   `regenerable` and a `source:` that brings the files back.
2. Make sure `README.md` reads like a GitHub repository README: what you did,
   the layout (a line per important file/dir), how to run it, and a
   "Restoring removed files" section with the command for EVERY delete entry.
3. Text and code files never need a decision, and neither does anything under
   the auto-keep floor. Only large binaries and cache directories do.
</CRITICAL_ERROR>
```

### [46] TOOL CALL — Bash · 2026-09-30 03:24:13 UTC

```
Remove invalid manifest entry, update README:
cd /ai-inventor/aii_data/runs/run_YczZzZ0_9kfq/4_gen_paper_repo/_4_gen_demo_art/notebook_workspaces/iter_1/art_94GEMUsgAmgK
cat > .aii/manifest.yaml <<'EOF'
# Nothing in this workspace is heavy (~5 MB total, all text/JSON/notebook) — no keep/delete decisions required.
entries: []
EOF
python3 - <<'EOF'
p='README.md'; s=open(p).read()
s=s.replace("""## Restoring removed files
- `demo_out/`: the notebook's output directory. It is regenerable, so re-run the notebook: `jupyter nbconvert --to notebook --execute code_demo.ipynb`.
""","""## Restoring removed files
Nothing was removed, so there is nothing to restore. Everything in this repository is small text: the notebook, JSON data and scripts. Running the notebook creates a small `demo_out/` directory, which you can rebuild at any time with `jupyter nbconvert --to notebook --execute code_demo.ipynb`.
""")
open(p,'w').write(s)
EOF
cat .aii/manifest.yaml; tail -3 README.md
```

### [47] TOOL RESULT — Bash · 2026-09-30 03:24:13 UTC

```
{"stdout": "# Nothing in this workspace is heavy (~5 MB total, all text/JSON/notebook) — no keep/delete decisions required.\nentries: []\n\n## Restoring removed files\nNothing was removed, so there is nothing to restore. Everything in this repository is small text: the notebook, JSON data and scripts. Running the notebook creates a small `demo_out/` directory, which you can rebuild at any time with `jupyter nbconvert --to notebook --execute code_demo.ipynb`.", "stderr": "", "interrupted": false, "isImage": false, "noOutputExpected": false}
```

### [48] ASSISTANT · 2026-09-30 03:24:17 UTC

```
I fixed the manifest error. `.aii/manifest.yaml` now has no entries (`entries: []`), and I haven't re-run the check yet.

The `demo_out/` entry was wrong because that folder no longer exists: I deleted it after testing. Even when the notebook recreates it, it only holds small JSON and log files, which never need a decision. Everything else in the workspace is text too (about 5 MB), so nothing needs a decision.

I also rewrote the "Restoring removed files" section of `README.md` to say that nothing was removed. It notes that running the notebook recreates `demo_out/`, and gives the command. `.terminal_claude_agent_struct_out.json` is unchanged.
```
