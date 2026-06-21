import statsmodels.formula.api as smf
import pandas as pd          
import matplotlib.pyplot as plt 
import numpy as np
from tqdm import tqdm
import os

# --- 1. Setup & Data Loading ---
combined_df = pd.read_pickle("/home/gaia/Projects/legacy_data/legacy_pipe/data/processed/combined_df_with_weights_per_window.pkl")

list_of_rois = list(range(1, 455))
n_list = [25, 33, 50, 70, 100, 135, 175, 225, 300]
reps = 1000
age_windows = [20, 25, 30]

# --- 2. Run Simulation ---
for age in age_windows:
    min_age_bin = age
    max_age_bin = age + 5
    
    # Storage for this specific age window
    simulation_summary = [] # For the final stability table
    all_plotting_stats = [] # For the funnel plots in the other notebook

    # Filter age window once
    volumes = combined_df[(combined_df['age_in_years'] >= min_age_bin) & (combined_df['age_in_years'] < max_age_bin)].copy()
    volumes['age_in_years'] = pd.to_numeric(volumes['age_in_years'], errors='coerce')

    print(f"--- Processing Age Window: {min_age_bin}-{max_age_bin} ---")

    for roi in tqdm(list_of_rois):
        roi_iterations = []
        df_sim = volumes[volumes['region_label'] == roi].copy()
        
        if len(df_sim) < max(n_list):
            continue

        for n in n_list:
            for r in range(reps):
                try:
                    sample_df = df_sim.sample(n=n, replace=False)
                    model = smf.wls(
                        'volume_mm3 ~ birth_year + C(sex) + tiv + age_in_years',
                        data=sample_df,
                        weights=sample_df['ps_weight']
                    ).fit()
                    
                    roi_iterations.append({
                        'sample_size': n,
                        'coef': model.params['birth_year']
                    })
                except:
                    continue

        sim_df = pd.DataFrame(roi_iterations)
        if sim_df.empty: continue

        # 3. Calculate Stats for plotting
        stats = sim_df.groupby('sample_size')['coef'].agg([
            'mean',
            lambda x: np.percentile(x, 0.5),   # 99% Low
            lambda x: np.percentile(x, 99.5),  # 99% High
            lambda x: np.percentile(x, 2.5),   # 95% Low
            lambda x: np.percentile(x, 97.5)   # 95% High
        ]).reset_index()
        
        stats.columns = ['sample_size', 'mean', 'low_99', 'high_99', 'low_95', 'high_95']
        
        # Add metadata for the other notebook
        stats['roi'] = roi
        stats['age_bin'] = f"{min_age_bin}_{max_age_bin}"
        all_plotting_stats.append(stats)

        # 4. Stability Logic (finding the N where it stops crossing zero)
        failed_95 = stats[stats['low_95'] * stats['high_95'] <= 0]['sample_size']
        failed_99 = stats[stats['low_99'] * stats['high_99'] <= 0]['sample_size']
        
        last_fail_95 = failed_95.max() if not failed_95.empty else -1
        last_fail_99 = failed_99.max() if not failed_99.empty else -1

        simulation_summary.append({
            'roi': roi,
            'mean_coef': stats['mean'].iloc[-1],
            'stable_n_95': stats[stats['sample_size'] > last_fail_95]['sample_size'].min(),
            'stable_n_99': stats[stats['sample_size'] > last_fail_99]['sample_size'].min()
        })

    # --- 5. Saving Data per Window ---
    
    # Save Plotting Data (The stats for the funnel)
    window_plotting_df = pd.concat(all_plotting_stats)
    plot_save_path = f"/home/gaia/Projects/legacy_data/legacy_pipe/data/processed/plotting_stats_{min_age_bin}_{max_age_bin}.csv"
    window_plotting_df.to_csv(plot_save_path, index=False)
    
    # Save Summary Data (The stable N per ROI)
    summary_df = pd.DataFrame(simulation_summary)
    summary_save_path = f"/home/gaia/Projects/legacy_data/legacy_pipe/data/processed/stability_summary_{min_age_bin}_{max_age_bin}.csv"
    summary_df.to_csv(summary_save_path, index=False)

    print(f"✅ Saved plotting data and summary for window {min_age_bin}-{max_age_bin}")