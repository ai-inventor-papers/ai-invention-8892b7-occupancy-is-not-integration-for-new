# Data and code for: Close to the cutoff: boundary proximity, score sensitivity and the year-to-year mobility of SCImago journal quartiles, 2010–2025

James Andrew C. Dorado, Stephen B. Alayon, Regin A. Cabacas, Ma. Beth S. Concepcion, Shem Durst Elijah B. Sandig
Department of Information Systems, College of Information and Communications Technology, West Visayas State University, Iloilo City, Philippines
Contact: jamesandrew.dorado@wvsu.edu.ph

Version 1.0.0

This record holds the analysis-ready data, result tables, plot data and code behind the study. The study follows every ranked journal-category pair in the SCImago Journal Rank (SJR) series across the 15 transitions from 2010→2011 to 2024→2025, and measures how often category quartiles change, how change depends on a journal's distance from the nearest quartile cutoff, and how sensitive quartile labels are to perturbations of SJR.

## Contents

| File | Content |
|---|---|
| `sjr_transition_panel.parquet` | One row per journal-category pair and adjacent-year transition t→t+1, start years 1999–2024 (1,806,415 rows, all source types, including entries and exits) |
| `sjr_category_panel.parquet` | One row per journal, subject category and year, 1999–2025 (1,736,361 rows), standardised from the raw files with parse and validation status |
| `data_dictionary.csv` | Every column of both files: type, missing count and definition |
| `raw_file_manifest.csv` | The 27 raw SCImago files used: name, size, SHA-256, retrieval date and source |
| `results.zip` | `results/tables/`: the 22 result tables produced by the pipeline (descriptive rates, transition matrices, model coefficients, predictions, sensitivity analyses, score-perturbation benchmark); `results/analysis_09/`, `analysis_10/`, `analysis_11/`: descriptive summary, model diagnostics and benchmark diagnostics |
| `manuscript.zip` | `plot_data/`: the exact values plotted in each figure; `tables/`: the manuscript tables; `figures/`: the figures (vector PDF); `manuscript_numbers.json`: every number quoted in the text; `visual_manifest.csv`: links each figure to its plot data, sources and script; `build_manuscript_assets.py`: the script that produces them from `results/` |
| `sjr-quartile-mobility-code.zip` | The full analysis pipeline (Python), configuration and tests |
| `checksums.sha256` | SHA-256 of every file in this record |

CSV files in `results/` and `manuscript/` begin with a provenance header of lines starting with `#` (source dataset and hash, filters, grouping, calculation script, timestamp). Read them with `pandas.read_csv(path, comment="#")`.

## Raw data

The raw input is the annual journal ranking export of the SCImago Journal & Country Rank portal for 1999–2025, downloaded on 30 August 2026. The raw files are not redistributed here. They can be downloaded from https://www.scimagojr.com/journalrank.php and checked against `data/raw_file_manifest.csv`; the same hashes are recorded row by row in `sjr_category_panel.parquet` (`raw_file_sha256`). The hashes are of the files with LF line endings, as analysed; normalise line endings before verifying:

```python
import hashlib
hashlib.sha256(open("scimagojr 2010.csv", "rb").read().replace(b"\r\n", b"\n")).hexdigest()
```

SCImago revises its series retrospectively, so files downloaded later may differ; the hashes identify the exact files analysed.

## Key definitions

- **Rank position** `P = (avg_rank − 0.5) / category_size`, where `avg_rank` is the SJR rank within the category-year (1 = highest SJR, ties averaged) and `category_size` is the number of ranked sources.
- **Boundary distance** `boundary_distance_t` = distance from P to the nearest cutoff 0.25, 0.50 or 0.75.
- **Quartile change** `quartile_changed` = 1 if the reported quartile in t+1 differs from that in t, 0 if equal, missing if the quartile is missing at either end. Entries and exits are never counted as change.
- Missing values are never coded as zero. Categories without a reported quartile have `parse_status = "no_quartile"`.

## Reproducing the analysis populations

```python
import pandas as pd
t = pd.read_parquet("data/sjr_transition_panel.parquet")
defined = t[(t.source_type_standardized == "journal") & t.year.between(2010, 2024) & t.quartile_changed.notna()]
model = defined[(defined.category_size >= 20) & (defined.validation_status != "far_mismatch")]
len(defined), defined.quartile_changed.mean()   # 811,438 pairs; 0.246
len(model), model.quartile_changed.sum()        # 807,805 pairs; 198,739 changes
```

## Re-running the pipeline

1. Unzip `code/sjr-quartile-mobility-code.zip` and install the dependencies in `requirements.txt` (Python 3.11 or later).
2. Download the 27 raw files into `data/raw/` with their original names (`scimagojr <year>.csv`) and verify them against `data/raw_file_manifest.csv`.
3. Run `python run_pipeline.py` (see `README.md` in the code archive for stages and options). Every stage records input and output hashes, and the pre-specified analysis parameters are in `config/analysis_parameters.yaml`.
4. To regenerate the manuscript figures and tables, place `manuscript/build_manuscript_assets.py` in a folder inside the code checkout and run it; it reads the pipeline outputs and writes `figures/`, `plot_data/` and `tables/` next to itself.

The adjusted models use a journal-cluster bootstrap with 1,000 resamples and the score-perturbation benchmark uses 200 replications; both are deterministic given the fixed seed in `config/config.yaml`.

## Licences

- Data files (`data/`, `results/`, `manuscript/` except the script): Creative Commons Attribution 4.0 International (CC BY 4.0); see `LICENSE-DATA.txt`. The SJR values and bibliometric fields originate from the SCImago Journal & Country Rank portal (data source: Scopus); please also cite SCImago when reusing them.
- Code (`code/` and `manuscript/build_manuscript_assets.py`): MIT License (`LICENSE` inside the code archive).

## Citation

Please cite the article and this record. Suggested citation for the record:

Dorado, J. A. C., Alayon, S. B., Cabacas, R. A., Concepcion, M. B. S., & Sandig, S. D. E. B. (2026). *Data and code for: Close to the cutoff: Boundary proximity, score sensitivity and the year-to-year mobility of SCImago journal quartiles, 2010–2025* (Version 1.0.0) [Data set]. Zenodo.

SCImago. (2026). *SJR – SCImago Journal & Country Rank* [Data set, annual journal ranking files 1999–2025]. Retrieved August 30, 2026, from https://www.scimagojr.com
