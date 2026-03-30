# CLAUDE.md

## Project Overview

This is a neuroscience master's thesis project at the Sagol School of Neuroscience, Tel Aviv University (PI: Yaniv Assaf). The research investigates **generational (cohort) effects on brain structure** — how grey matter volume (GMV) differs across birth years, independent of chronological aging.

### Core Research Question
Do people born in different eras show systematically different regional brain volumes, even after controlling for age, sex, and total intracranial volume?

### Key Findings So Far
- **Increased GMV in later birth cohorts**: Salience and Limbic systems — amygdala, nucleus accumbens, insula, orbitofrontal cortex (bilateral).
- **Decreased GMV in later birth cohorts**: Subcortical motor regions — globus pallidus, putamen — and parts of the visual network.
- Initial analysis focused on the 30–35 age group (N=604, birth years 1971–1995). Future work extends to other age bins.

### Dataset
- ~3,000 T1-weighted structural MRI scans collected over 20 years (2005–2025).
- Age range: 18–87 years. Birth years: 1931–2007.
- Sources: Strauss Neuroplasticity Brain Bank (SNBB) + legacy scans from prior studies.
- Preprocessed with **CAT12** (Computational Anatomy Toolbox).
- Parcellations: 400 cortical ROIs (Schaefer atlas) + 54 subcortical ROIs (Tian atlas).

### Statistical Approach
- Multiple Linear Regression (MLR) per ROI: `GMV_ROI ~ β0 + β1*BirthYear + β2*TIV + β3*ExactAge + β4*Sex`
- Subjects divided into 5-year age bins to isolate cohort from age effects.
- FDR correction for multiple comparisons.
- Additional analyses: sliding windows, permutation testing, GAM/GAMM models, clustering, power analysis.

---

## Tech Stack

- **Primary language**: Python (notebooks + scripts)
- **Secondary**: R (for GAM/GAMM and residualizing), MATLAB (CAT12 runner scripts)
- **Key Python libraries** (likely): pandas, numpy, scipy, statsmodels, nilearn, nibabel, matplotlib, seaborn, scikit-learn
- **MRI preprocessing**: CAT12 (MATLAB-based SPM toolbox)
- **Data formats**: DICOM (raw), NIfTI (processed), CSV (extracted volumes and metadata)

---

## Project Structure

The repository contains multiple pipeline versions. **`legacy_pipe/`** is the latest stable version.

```
.
├── legacy_pipe/            # Latest stable pipeline code
│   ├── atlas_analysis.ipynb
│   ├── cat12_xml_parser.py         # Parses CAT12 output XMLs for ROI volumes
│   ├── cleaning_funcs.py           # Data cleaning utilities
│   ├── harmonization.ipynb         # Scanner/site harmonization
│   ├── prioritize_t1w_protocols.py # Selects best T1w scan per subject
│   ├── t1w_bids_conversion.py      # DICOM → BIDS conversion
│   ├── ValidateID.py               # Subject ID validation
│   ├── manual_labeling/            # Scan classification & QC
│   └── weighting_to_match_population.ipynb
│
├── scripts/
│   ├── preprocess_pipeline/        # Numbered steps (step1–step9)
│   │   ├── step1_organize_dicom_folders.py
│   │   ├── step2_extract_dicom_metadata.py
│   │   ├── step3_manual_cleaning_template.ipynb
│   │   ├── step4_prioritize_and_convert.py
│   │   ├── step5_list_for_cat12.ipynb
│   │   ├── step6_create_long_format.py
│   │   ├── step7_combine_data_sources.ipynb
│   │   ├── step7.5_handle_outliers.ipynb
│   │   ├── step8_poc_statistical_analysis.ipynb
│   │   └── step9_windowing_and_modeling.ipynb
│   │
│   └── data_analysis/              # Post-modeling analyses
│       ├── aggregate_by_function.ipynb
│       ├── clustering_trends.ipynb
│       ├── gam.ipynb / GAMM.R
│       ├── metadata_analysis.ipynb
│       ├── power_analysis.ipynb
│       ├── step10_coefficient_trend_analisys.ipynb
│       ├── step11_coef_stability_test.ipynb
│       ├── step13_permutation_testing.ipynb
│       └── sub-sampling.ipynb
│
├── data/
│   ├── raw/                # Original unprocessed data
│   ├── interim/            # Intermediate outputs (coefficient CSVs, ROI aggregations)
│   ├── processed/          # Final analysis-ready data
│   └── external/           # External reference data
│
├── reports/figures/        # Output figures
├── docs/                   # MkDocs documentation
├── models/                 # Saved models (if any)
└── references/             # Literature, notes
```

### Pipeline Flow (preprocessing → analysis)
1. **step1**: Organize raw DICOM folders from heterogeneous sources
2. **step2**: Extract DICOM metadata (scanner info, acquisition parameters, subject demographics)
3. **step3**: Manual cleaning — flag/fix problematic scans
4. **step4**: Prioritize best T1w protocol per subject, convert to NIfTI/BIDS
5. **step5**: Generate file lists for CAT12 batch processing
6. **step6**: Parse CAT12 outputs into long-format CSV (ROI volumes per subject)
7. **step7**: Combine data sources, merge metadata with volumes
8. **step7.5**: Handle outliers
9. **step8**: Initial statistical analysis (MLR per ROI)
10. **step9**: Windowed modeling (fixed age bins, sliding windows)
11. **step10+**: Coefficient trend analysis, stability testing, permutation tests

---

## Setup

### Python environment

All Python work runs inside a single virtualenv. Create and activate it once:

```bash
# 1. Create the venv (only needed once)
python -m venv .venv

# 2. Activate it (do this every session)
source .venv/bin/activate   # Linux / macOS
# .venv\Scripts\activate    # Windows

# 3. Install all dependencies
pip install -r requirements.txt
```

The `-e .` line in `requirements.txt` installs the `legacy_pipe/` package in editable mode, so imports like `import legacy_pipe.cleaning_funcs` work from any notebook or script.

### Key Python packages and what they're for

| Package | Used for |
|---------|----------|
| `pandas`, `numpy` | Data wrangling everywhere |
| `scipy`, `statsmodels` | Statistical tests, MLR, FDR correction |
| `scikit-learn` | Preprocessing (StandardScaler), clustering |
| `pygam` | Generalised Additive Models (Python-side GAM) |
| `nibabel`, `nilearn` | Loading/plotting NIfTI brain images |
| `pydicom` | Reading raw DICOM metadata (step 2) |
| `neuroCombat` | Scanner harmonisation (harmonization notebooks) |
| `balance` | Survey-style reweighting to match population distributions (step 9 / refactored_windowing_weighting) |
| `matplotlib`, `seaborn`, `Pillow` | Visualisation and image handling |
| `tqdm` | Progress bars in long-running loops |
| `python-dateutil` | Flexible date parsing in step 7 |

### R environment (GAMM / Residualizing only)

R is required only for `scripts/data_analysis/GAMM.R` and `scripts/data_analysis/Residualizing.R`.

```r
# Install required R packages (run once inside an R session)
install.packages(c("gamm4", "readr", "car"))
```

- `gamm4` — Generalised Additive Mixed Models
- `readr` — fast CSV reading
- `car` — VIF (multicollinearity) checks

The R scripts read `~/Projects/legacy_data/data_for_r_all_rois.csv` and write output CSVs to the R working directory. Set your working directory accordingly before running.

### MATLAB / CAT12 (preprocessing only)

MATLAB with the **SPM12** and **CAT12** toolboxes is required only for the actual MRI preprocessing (segmentation, parcellation). It is **not** needed to run any Python or R analysis scripts. CAT12 batch templates live in `scripts/preprocess_pipeline/`.

---

## Coding Conventions

- Preprocessing scripts are **numbered sequentially** (`step1_`, `step2_`, ...). Respect this ordering.
- Mix of `.py` scripts (reusable/batch) and `.ipynb` notebooks (exploratory/interactive).
- `legacy_pipe/` contains reusable modules imported by scripts and notebooks.
- Data files live in `data/` — never commit large data files. CSVs in `data/interim/` are intermediate results.
- R scripts (GAMM.R, Residualizing.R) are used only for specific statistical models not easily done in Python.
- MATLAB files are only for CAT12 batch processing templates.

---

## Key Domain Terms

| Term | Meaning |
|------|---------|
| **GMV** | Grey Matter Volume — the primary dependent variable |
| **TIV** | Total Intracranial Volume — used as a covariate to normalize for head size |
| **ROI** | Region of Interest — a parcellated brain area |
| **Cohort effect** | Systematic differences attributable to birth year/era, not aging |
| **CAT12** | Computational Anatomy Toolbox — SPM plugin for brain segmentation |
| **FDR** | False Discovery Rate — multiple comparison correction method |
| **Schaefer atlas** | 400-region cortical parcellation based on functional connectivity |
| **Tian atlas** | 54-region subcortical parcellation |
| **BIDS** | Brain Imaging Data Structure — standardized neuroimaging file organization |
| **DICOM** | Raw MRI file format from scanners |
| **NIfTI** | Standard neuroimaging format (.nii / .nii.gz) |
| **MPRAGE** | Magnetization-Prepared Rapid Gradient Echo — a T1w acquisition sequence |
| **Harmonization** | Statistical correction for scanner/site differences across acquisition sources |
| **Birth year coefficient (β1)** | The MLR coefficient quantifying the cohort effect on GMV per ROI |

---

## Important Context for Assistance

- When helping with statistical code, remember the MLR model structure: GMV is predicted by birth year, with TIV, exact age, and sex as covariates.
- The dataset has **heterogeneous scan sources** (different scanners, sites, years). Harmonization and QC are critical concerns.
- Birth year and age are **partially confounded** in cross-sectional data — the 5-year age binning strategy is the primary method to disentangle them.
- Intermediate CSV filenames encode parameters: e.g., `coef_df_sliding_ws100_ss50.csv` = sliding window, window size 100, step size 50.
- The project may involve generating figures for publications/conferences (OHBM, Sagol retreat).
- Prefer clear, well-commented code. This is a thesis project that needs to be reproducible and explainable.

---

## Data Paths

All paths below were found hardcoded in scripts/notebooks. Paths under `/home/gaia/Projects/HardDriveOutput/` appear to reference an external hard drive or mounted volume (not always present). Everything else is on the local filesystem.

### Root directories

| Directory | Description |
|-----------|-------------|
| `/home/gaia/Projects/legacy_data/` | Main data root — most inputs and outputs live here |
| `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/` | Intermediate results (CSVs, classification outputs) within this repo |
| `/home/gaia/Projects/legacy_data/refactored_project/data/` | Older output tree used by early pipeline steps (interim/ and processed/ subdirs) |
| `/home/gaia/Projects/legacy_data/my_master/` | Reference/master files: atlas CSVs, subject ID map |
| `/home/gaia/Projects/HardDriveOutput/` | **External hard drive** — BIDS-converted scan sets; may not be mounted |
| `/home/gaia/Projects/` | Miscellaneous loose files (SNBB pickle, GNBB CSV) |

---

### Key files by pipeline step

#### Step 3 — Manual cleaning
| File | Path | Notes |
|------|------|-------|
| Input metadata | `/home/gaia/Projects/legacy_data/refactored_project/data/interim/HardDrive_metadata.csv` | Per-batch variant (e.g. `HardDrive_metadata.csv`) |
| Subject ID map | `/home/gaia/Projects/legacy_data/my_master/subj_map.json` | Maps raw IDs to canonical subject IDs |
| Output cleaned CSV | `/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_metadata.csv` | |
| Output cleaned pickle | `/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_metadata.pkl` | |

#### Step 4 — Prioritize & convert
| File | Path | Notes |
|------|------|-------|
| Input cleaned metadata | `path/to/manually/cleaned/metadata.pkl` | Placeholder — set per batch |
| Output best-protocol CSV | `/home/gaia/Projects/legacy_data/refactored_project/data/interim/full_metadata_best_protocol.csv` | |
| Output BIDS directory | `/home/gaia/Projects/legacy_data/BIDS_converted` | NIfTI files in BIDS layout |

#### Step 5 — List for CAT12
| File | Path | Notes |
|------|------|-------|
| Input BIDS directory | `/home/gaia/Projects/HardDriveOutput/BIDS_over_thirties` | **External drive** |

#### Step 6 — Create long format
| File | Path | Notes |
|------|------|-------|
| Input CAT12 derivatives | `/home/gaia/Projects/HardDriveOutput/BIDS_under_thirties/derivatives/CAT12.9_2577` | **External drive**; version number may vary |
| Input filtered metadata | `/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_under_thirties_full_metadata_filtered.csv` | |
| Output long-format CSV | `/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_under_thirties_long_format.csv` | Per-batch variant |

#### Step 7 — Combine data sources
| File | Path | Notes |
|------|------|-------|
| Input long-format CSVs | `/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_{thirties,over_thirties,under_thirties}_long_format.csv` | Multiple batch files |
| Input SNBB data | `/home/gaia/Projects/Gaia_gm_vol_cleaned_with_unique_id.pkl` | Strauss Neuroplasticity Brain Bank volumes |
| Input GNBB volumes | `/home/gaia/Projects/gnbb.csv` | Additional source dataset |
| Output combined pickle | `/home/gaia/Projects/legacy_data/combined_gm_volumes.pkl` | All sources merged |

#### Step 9 — Windowing & modeling
| File | Path | Notes |
|------|------|-------|
| Input combined data | `/home/gaia/Projects/legacy_data/best_combined_gm_volumes.pkl` | Filtered/QC'd version of combined pickle |
| Input atlas labels | `/home/gaia/Projects/legacy_data/my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv` | Schaefer 400 + Tian atlas ROI labels |
| Output coefficients | `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/coef_df_{suffix}.csv` | `{suffix}` encodes window params, e.g. `sliding_ws100_ss50` |

#### Manual labeling / QC
| File | Path | Notes |
|------|------|-------|
| Input JPG derivatives | `/home/gaia/Projects/HardDriveOutput/BIDS_over_thirties/derivatives` | **External drive** — CAT12 QC images |
| Output classification CSV | `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/HardDrive_BIDS_over_thirties_scan_classification_results.csv` | |
| Input resolved labels | `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/manual_labels_resolved_duplicates.csv` | |
| Output review lists | `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/list_for_yaniv_pixeled.csv` | Flagged scans for PI review |
| Output review lists | `/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/list_for_yaniv_partial_scans.csv` | |

#### R scripts (GAMM / Residualizing)
| File | Path | Notes |
|------|------|-------|
| Input all-ROI data | `~/Projects/legacy_data/data_for_r_all_rois.csv` | Relative to home dir; generated before running R |
| Output fixed effects | `fixed_all_effects.csv` / `cohort_residual_effects.csv` | Written to R working directory |
| Output ROI curves | `fixed_all_roi_curves.csv` / `cohort_residual_curves.csv` | Written to R working directory |

---

### Notes on external vs. local paths

- **`/home/gaia/Projects/HardDriveOutput/`** — References an external hard drive or mounted volume. Scripts that read from here (`step5`, `step6`, `manual_labeling/classify_scans.py`) will fail if the drive is not mounted.
- **`/home/gaia/Projects/legacy_data/refactored_project/`** — An older output directory from a prior iteration of the pipeline. Some early steps still write here; later steps read from `/home/gaia/Projects/legacy_data/` directly.
- **`/home/gaia/Projects/legacy_data/my_master/`** — Treat as read-only reference data (atlas files, subject map). Do not overwrite.
- **Placeholder paths** (`/path/to/...`, `path/to/...`) — Found in template scripts (step1, step2, step3 template, step4). These must be set by the user before running.
