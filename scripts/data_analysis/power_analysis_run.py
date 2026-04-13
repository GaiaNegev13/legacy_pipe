import statsmodels.formula.api as smf
import pandas as pd          
import matplotlib.pyplot as plt 
import numpy as np
from tqdm import tqdm

combined_df = pd.read_pickle("/home/gaia/Projects/legacy_data/legacy_pipe/data/processed/combined_df_with_weights_per_window.pkl")

# Configurations

# list_of_rois = list([421, 422, 448, 449])
# # all rois 1 to 454
list_of_rois = list(range(1, 455))

n_list = [25, 33, 50, 70, 100, 135, 175, 225, 300]
reps = 100  # Number of random samplings per N
simulation_results = []
age_windows = [20, 25, 30]


# 2. Run Simulation for several windows 
for age in age_windows:
    min_age = age
    max_age = age + 5

    simulation_results = []  # Reset for each age window

    volumes = combined_df[(combined_df['age_in_years'] >= min_age) & (combined_df['age_in_years'] < max_age)]
    volumes['age_in_years'] = pd.to_numeric(volumes['age_in_years'], errors='coerce')

    for roi in tqdm(list_of_rois):

        # Storage for THIS specific ROI's iterations
        roi_simulation_results = []
        
        # Filter for the specific ROI first to speed up sampling
        df_sim = volumes[volumes['region_label'] == roi].copy()
        
        # Define age range for the title
        min_age = int(df_sim['age_in_years'].min())
        max_age = int(df_sim['age_in_years'].max())

        for n in n_list:
            for r in range(reps):
                try:
                    # Sample n scans randomly
                    sample_df = df_sim.sample(n=n, replace=False)
                
                    # Fit the OLS model
                    model = smf.wls(
                        'volume_mm3 ~ birth_year + C(sex) + tiv + age_in_years',
                        data=sample_df,
                        weights=sample_df['ps_weight']
                    ).fit()
                    
                    roi_simulation_results.append({
                        'sample_size': n,
                        'iteration': r,
                        'coef': model.params['birth_year'],
                        'p_val': model.pvalues['birth_year']
                    })
                except Exception as e:
                    continue

        # Create DataFrame for current ROI
        sim_df = pd.DataFrame(roi_simulation_results)
        
        if sim_df.empty:
            print(f"No results for ROI {roi}, skipping plot.")
            continue

        # 3. Calculate Percentiles for THIS ROI
        stats = sim_df.groupby('sample_size')['coef'].agg([
            'mean',
            lambda x: np.percentile(x, 0.5),   # 99% Lower
            lambda x: np.percentile(x, 99.5),  # 99% Upper
            lambda x: np.percentile(x, 2.5),   # 95% Lower
            lambda x: np.percentile(x, 97.5)   # 95% Upper
        ]).reset_index()

        stats.columns = ['sample_size', 'mean', 'low_99', 'high_99', 'low_95', 'high_95']

        # --- STABILITY LOGIC ---
        # Find all sample sizes where the CI includes zero (the product is <= 0)
        failed_95 = stats[stats['low_95'] * stats['high_95'] <= 0]['sample_size']
        failed_99 = stats[stats['low_99'] * stats['high_99'] <= 0]['sample_size']

        # The last 'failure' defines the boundary. If no failures, use -1.
        last_fail_95 = failed_95.max() if not failed_95.empty else -1
        last_fail_99 = failed_99.max() if not failed_99.empty else -1

        # Stable N is the smallest n in our list that is GREATER than the last failure
        stable_95 = stats[stats['sample_size'] > last_fail_95]['sample_size'].min()
        stable_99 = stats[stats['sample_size'] > last_fail_99]['sample_size'].min()

        simulation_results.append({
            'roi': roi,
            'mean_coef': stats['mean'].iloc[-1], # Using the mean from the largest sample for accuracy
            'first_sample_size_95': stable_95,
            'first_sample_size_99': stable_99
        })
        
        # # 4. Create the Funnel Plot for THIS ROI
        # plt.figure(figsize=(10, 6))

        # # --- Shading Layers ---
        # plt.fill_between(stats['sample_size'], stats['low_99'], stats['high_99'], 
        #                  color='forestgreen', alpha=0.1, label='99% CI')
        # plt.fill_between(stats['sample_size'], stats['low_95'], stats['high_95'], 
        #                  color='forestgreen', alpha=0.2, label='95% CI')

        # # --- Border Lines ---
        # plt.plot(stats['sample_size'], stats['low_99'], color='gray', linestyle='--', lw=0.8, alpha=0.4)
        # plt.plot(stats['sample_size'], stats['high_99'], color='gray', linestyle='--', lw=0.8, alpha=0.4)

        # # --- Central Trend ---
        # plt.plot(stats['sample_size'], stats['mean'], color='forestgreen', lw=2, label='Mean Coef')

        # # Formatting
        # plt.xscale('log')
        # plt.xticks(n_list, labels=[str(x) for x in n_list])
        # plt.axhline(0, color='black', lw=1)
        # plt.xlabel('Sample size')
        # plt.ylabel('Birth Year Coefficient (Effect Size)')
        # plt.legend()
        # plt.title(f'Sample Size Stability For ROI {roi}, {min_age}-{max_age} years old')

        # # Show plot for this ROI
        # plt.tight_layout()
        # plt.show()

    print(f"Completed simulations for age window {min_age}-{max_age}.")

    # simulation_results to df 
    simulation_df = pd.DataFrame(simulation_results)

    # # save simulation df for the specific window
    simulation_df.to_csv(f"/home/gaia/Projects/legacy_data/legacy_pipe/data/processed/{reps}simulation_results_age_{min_age}_{max_age}.csv", index=False)