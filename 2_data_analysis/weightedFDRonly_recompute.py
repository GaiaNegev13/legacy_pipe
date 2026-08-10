"""
Recompute FDR correction restricted to weighting == 'weighted' (bug fix).

Background
----------
step9_refactored_windowing_weighting.ipynb originally FDR-corrected
`birth_year` p-values within each age window across BOTH the weighted and
unweighted model rows pooled together (908 tests: 454 ROIs x 2 model
specs), even though only the 'weighted' rows are used downstream. This
script recomputes `fdr_p` correctly (weighted rows only, 454 tests per
window) from the ALREADY-COMPUTED raw p-values, which are unaffected by
the bug — no regression needs to be re-fit.

It then reproduces the data-only (non-plotting) portion of
step10_coefficient_trend_analisys.ipynb — stability merge, sig_stab,
roi_count, and the coefficient-trend FDR — against the corrected values,
restricted to the 3 age windows that have a stability analysis on disk
(20-25, 25-30, 30-35), per the project's explicit decision not to rerun
the (heavy) subsampling-based stability simulation for the other 7
windows.

Inputs read (never modified):
  legacy_pipe/data/interim/coef_df_manual_bins_wuniform.csv
  legacy_pipe/data/interim/stable_95_early_twenties.json
  legacy_pipe/data/interim/stable_95_late_twenties.json
  legacy_pipe/data/interim/stable_95_early_thirties.json
  my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv

Outputs written (new files only, "weightedFDRonly" prefix, nothing overwritten):
  legacy_pipe/data/interim/weightedFDRonly_coef_df_manual_bins_wuniform.csv
  legacy_pipe/data/processed/weightedFDRonly_weighted_birth_year_coef_df_with_stability.csv
"""
import json
from pathlib import Path

import pandas as pd
import statsmodels.formula.api as smf
from statsmodels.stats.multitest import multipletests

REPO = Path("/home/gaia/Projects/legacy_data")
INTERIM = REPO / "legacy_pipe/data/interim"
PROCESSED = REPO / "legacy_pipe/data/processed"

# ---------------------------------------------------------------------------
# 1. Recompute FDR correctly (weighted-only mask) from the existing raw p-values
# ---------------------------------------------------------------------------
coef_df = pd.read_csv(INTERIM / "coef_df_manual_bins_wuniform.csv")

old_fdr = coef_df["fdr_p"].copy()
coef_df["fdr_p"] = pd.NA

final_rows = []
for label, group in coef_df.groupby("age_bin"):
    mask = (group["variable"] == "birth_year") & (group["weighting"] == "weighted")
    if mask.any():
        _, fdr_p, _, _ = multipletests(group.loc[mask, "p"], method="fdr_bh")
        group.loc[mask, "fdr_p"] = fdr_p
    final_rows.append(group)
coef_df = pd.concat(final_rows)

out_coef_df_path = INTERIM / "weightedFDRonly_coef_df_manual_bins_wuniform.csv"
coef_df.to_csv(out_coef_df_path, index=False)
print(f"Saved -> {out_coef_df_path}")

# --- Before/after comparison, weighted birth_year rows only ---
by_weighted = coef_df[(coef_df["variable"] == "birth_year") & (coef_df["weighting"] == "weighted")].copy()
by_weighted["old_fdr_p"] = old_fdr.loc[by_weighted.index]
print("\n=== FDR family size & significant-ROI count per window (weighted birth_year rows) ===")
for age_bin, g in by_weighted.groupby("age_bin"):
    n_old_sig = (g["old_fdr_p"] < 0.05).sum()
    n_new_sig = (g["fdr_p"] < 0.05).sum()
    print(f"{age_bin}: n_ROIs={len(g)}, old family=908 (weighted+unweighted pooled), "
          f"new family={len(g)} (weighted only) | sig ROIs old={n_old_sig} -> new={n_new_sig}")

# ---------------------------------------------------------------------------
# 2. Reproduce step10's data pipeline (stability merge, sig_stab, roi_count,
#    trend FDR) against the corrected values, for the 3 windows with a
#    stability analysis on disk. Mirrors
#    legacy_pipe/2_data_analysis/step10_coefficient_trend_analisys.ipynb
#    cells b704c1f3 - 68007e45 and 3239542d.
# ---------------------------------------------------------------------------
atlas_csv = pd.read_csv(
    REPO / "my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv"
).rename(columns={"index": "region_label"})

coef_df_3win = coef_df[coef_df["age_bin"].isin(["[20, 25)", "[25, 30)", "[30, 35)"])]
birth_year_coef_df = coef_df_3win[
    (coef_df_3win["variable"] == "birth_year") & (coef_df_3win["weighting"] == "weighted")
].merge(atlas_csv[["region_label", "network", "component", "hemisphere"]], on="region_label", how="left")

birth_year_coef_df["net_comp"] = (
    birth_year_coef_df["network"].astype(str) + "_" + birth_year_coef_df["component"].astype(str)
)

# --- stability (unchanged; NOT rerun, per project decision to keep the
# heavy subsampling simulation scoped to 20-25/25-30/30-35 only) ---
def load_roi_list(filename):
    with open(INTERIM / filename) as f:
        data = json.load(f)
    print(f"Loaded {len(data)} ROIs from: {filename}")
    return data

early_twenties_roi_list_95 = load_roi_list("stable_95_early_twenties.json")
late_twenties_roi_list_95 = load_roi_list("stable_95_late_twenties.json")
early_thirties_roi_list_95 = load_roi_list("stable_95_early_thirties.json")

birth_year_coef_df["stable_95"] = False
birth_year_coef_df.loc[
    (birth_year_coef_df["age_bin"] == "[20, 25)") & birth_year_coef_df["region_label"].isin(early_twenties_roi_list_95),
    "stable_95",
] = True
birth_year_coef_df.loc[
    (birth_year_coef_df["age_bin"] == "[25, 30)") & birth_year_coef_df["region_label"].isin(late_twenties_roi_list_95),
    "stable_95",
] = True
birth_year_coef_df.loc[
    (birth_year_coef_df["age_bin"] == "[30, 35)") & birth_year_coef_df["region_label"].isin(early_thirties_roi_list_95),
    "stable_95",
] = True

birth_year_coef_df["sig_stab"] = (birth_year_coef_df["fdr_p"] < 0.05) & (birth_year_coef_df["stable_95"] == True)

out_stability_path = PROCESSED / "weightedFDRonly_weighted_birth_year_coef_df_with_stability.csv"
birth_year_coef_df.to_csv(out_stability_path, index=False)
print(f"\nSaved -> {out_stability_path}")

sig_stable_counts = (
    birth_year_coef_df[birth_year_coef_df["sig_stab"] == True].groupby("region_name")["age_bin"].nunique()
)
birth_year_coef_df["roi_count"] = birth_year_coef_df["region_name"].map(sig_stable_counts).fillna(0).astype(int)

print("\n=== Significant & stable ROI counts per window (corrected) ===")
for age_bin in sorted(birth_year_coef_df["age_bin"].unique()):
    bin_data = birth_year_coef_df[birth_year_coef_df["age_bin"] == age_bin]
    n_sig_stab = (bin_data["sig_stab"] == True).sum()
    total = bin_data["region_label"].nunique()
    print(f"{age_bin}: {n_sig_stab}/{total} ROIs significant & stable ({n_sig_stab/total*100:.2f}%)")

# ---------------------------------------------------------------------------
# 3. Reproduce the coefficient-trend analysis (step10 cell 3239542d) for
#    ROIs significant+stable in all 3 windows, on corrected data.
#    (This was never written to disk in the original pipeline either — it's
#    printed here for the report, not persisted, to match the original scope.)
# ---------------------------------------------------------------------------
birth_year_coef_df["age_bin_interval"] = birth_year_coef_df["age_bin"].apply(
    lambda s: pd.Interval(*[float(x) for x in s.strip("()[] ").split(",")], closed="left")
)
birth_year_coef_df["mid_age_bin"] = birth_year_coef_df["age_bin_interval"].apply(lambda x: x.mid)

sig_stable_df = birth_year_coef_df[(birth_year_coef_df["sig_stab"] == True) & (birth_year_coef_df["roi_count"] >= 3)].copy()
roi_list = [int(r) for r in sig_stable_df["region_label"].unique().tolist()]

trend_results = []
for region_of_interest in roi_list:
    region_data = birth_year_coef_df[birth_year_coef_df["region_label"] == region_of_interest]
    if region_data.shape[0] < 2:
        continue
    model = smf.ols("coef ~ mid_age_bin", data=region_data).fit()
    trend_results.append({
        "region_label": region_of_interest,
        "slope": model.params["mid_age_bin"],
        "t": model.tvalues["mid_age_bin"],
        "p": model.pvalues["mid_age_bin"],
    })
trend_results_df = pd.DataFrame(trend_results)
print(f"\n=== Trend analysis (ROIs sig+stable in all 3 windows): n_ROIs={len(roi_list)} ===")
if not trend_results_df.empty:
    _, fdr_p, _, _ = multipletests(trend_results_df["p"], method="fdr_bh")
    trend_results_df["fdr_p"] = fdr_p
    n_sig_trend = (trend_results_df["fdr_p"] < 0.05).sum()
    print(f"Significant trends (fdr_p < 0.05): {n_sig_trend}/{len(trend_results_df)}")
    print(trend_results_df.sort_values("fdr_p").head(10).to_string(index=False))
else:
    print("No ROIs met roi_count >= 3 — no trend regression run.")

print("\nDone.")
