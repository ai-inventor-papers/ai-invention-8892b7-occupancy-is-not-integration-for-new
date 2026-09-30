# Prompts

Complete, auto-generated record of **every prompt the AI Inventor system gave each agent** across this run — generated at repository-upload time so it captures all steps. For the full conversation (assistant turns, thinking, tool calls and results) see the sibling `../messages/` folder.

- Run: `iter5_6136aaed9367` — Host vocabulary predicts whether new scientific concepts take root across disciplinary boundaries

Each prompt is labelled by type and timestamped, with its full untruncated body:

- **SYSTEM-USER** — the pipeline-generated role/instruction prompt placed in the user slot.
- **HUMAN-USER** — the task / human-typed message into the agent stream.
- **SKILL-INPUT** — a skill the agent loaded; its `SKILL.md` instructions, verbatim.

Layout mirrors the run's module tree: one folder per high-level phase, a `round_N/` per iteration where the phase iterates, then each module — a single-task module is one `.md` file, a parallel module (gen_plan / gen_art / gen_viz / gen_demo_art) is a folder with one `.md` per task.

## Index

- **1. test_idea** — `invention_loop`
  - round_5
    - `chat/prompts/1_test_idea/round_5/1_gen_report_text.md` — 4 prompts
    - `chat/prompts/1_test_idea/round_5/2_review_report.md` — 1 prompt
    - `chat/prompts/1_test_idea/round_5/3_upd_hypo.md` — 1 prompt
- **2. report_results** — `gen_paper_repo`
  - `chat/prompts/2_report_results/1_gen_paper_draft.md` — 11 prompts
  - `2_gen_viz/` — 12 task(s)
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_1.md` — 6 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_2.md` — 3 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_3.md` — 2 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_4.md` — 1 prompt
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_5.md` — 2 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_6.md` — 2 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_1.md` — 2 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_2.md` — 2 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_3.md` — 3 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_4.md` — 3 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_5.md` — 3 prompts
    - `chat/prompts/2_report_results/2_gen_viz/gen_viz_report_6.md` — 2 prompts
  - `3_gen_demo_art/` — 22 task(s)
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_dataset_1.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_dataset_2.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_dataset_3.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_dataset_4.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_1.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_2.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_3.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_4.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_5.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_6.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_7.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_8.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_evaluation_9.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_1.md` — 5 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_2.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_3.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_4.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_5.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_6.md` — 4 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_7.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_8.md` — 3 prompts
    - `chat/prompts/2_report_results/3_gen_demo_art/gen_demo_art_experiment_9.md` — 3 prompts
  - `4_gen_full_paper/` — 3 task(s)
    - `chat/prompts/2_report_results/4_gen_full_paper/gen_full_paper.md` — 7 prompts
    - `chat/prompts/2_report_results/4_gen_full_paper/gen_paper_site.md` — 11 prompts
    - `chat/prompts/2_report_results/4_gen_full_paper/gen_report_doc.md` — 10 prompts
  - `chat/prompts/2_report_results/5_gen_html_demo.md` — 2 prompts
