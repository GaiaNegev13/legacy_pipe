# 1np.dividede my data to 5 year non-overlapping window in age (people 20-24, 25-29, 30-34 etc.)

# 2. Per ROI, and per age window, I want to find the slope of birth year (b1)
# the regression model is:

# for age_window:

# GMV_ROI_1 ~ b1*birth_year

import pandas as pd
import numpy as np
import statsmodels.api as sm
import matplotlib.pyplot as plt
import seaborn as sns
import statsmodels.formula.api as smf
from tqdm import tqdm

combined_df = pd.read_pickle('/home/gaia/Projects/legacy_data/combined_gm_volumes.pkl')
 
# keep only classification_label=1 and snbb
volumes = combined_df[(combined_df['classification_label'] == 1) | (combined_df['source'] == 'snbb')]

volumes['age_in_years'] = pd.to_numeric(volumes['age_in_years'], errors='coerce')

# divide volumes into age bins according to bin size
bin_size = 5
volumes['age_bin'] = pd.cut(volumes['age_in_years'], bins=np.arange(15, 85, bin_size))

print(f"amount of scans in each bin:")
print(volumes['age_bin'].value_counts().sort_index())

bin_list = volumes['age_bin'].cat.categories.tolist()

# add region name according to the atlas 
atlas_csv = pd.read_csv("/home/gaia/Projects/legacy_data/my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv")

# initiate a df with the columns bin, region_label, birth_year_coef, birth_year_t, birth_year_p
coef_df = pd.DataFrame(columns=['age_bin', 'region_label', 'variable', 'coef', 't', 'p', 'fdr_p', 'region_name'])

for bin in volumes['age_bin'].unique().dropna():
    print(f"age bin: {bin}, number of scans: {volumes[volumes['age_bin'] == bin].shape[0]}")

    min_age = bin.left
    max_age = bin.right

    # volumes df
    df_bin = volumes[(volumes['age_in_years'] >= min_age) & (volumes['age_in_years'] < max_age)]

    # metadata df
    # remove duplicates based on subject_id
    metadata = volumes.drop_duplicates(subset=['subject_id'])
    print(f"shape of {min_age} - {max_age} years old metadata after removing duplicates: {metadata.shape}")



    # create a multiple regression model for each ROI
    results = []

    # Loop over regions (ROI-level analyses)
    for roi, df_roi in tqdm(df_bin.groupby('region_label')):
        # Fit model with birth_year as a continuous predictor
        model = smf.ols(
            'volume_mm3 ~ birth_year + C(sex) + tiv + age_in_years',
            data=df_roi
        ).fit()
        
        # Collect stats for each variable
        for var in model.params.index:
            results.append({
                'region_label': roi,
                'variable': var,
                'coef': model.params[var],
                't': model.tvalues[var],
                'p': model.pvalues[var]
            })

    results_df = pd.DataFrame(results)

    results_df = results_df.merge(
        atlas_csv[['index', 'name']],     # only keep relevant columns
        how='left',                      # keep all rows from results_df
        left_on='region_label',          # column in results_df
        right_on='index'                 # matching column in atlas_csv
    )

    # rename and clean up
    results_df.rename(columns={'name': 'region_name'}, inplace=True)
    results_df.drop(columns='index', inplace=True)

    # --- Multiple comparison correction (using results_df) ---
    from statsmodels.stats.multitest import multipletests

    cov_of_interest = 'birth_year'
    mask = results_df['variable'] == cov_of_interest
    _, fdr_p, _, _ = multipletests(results_df.loc[mask, 'p'], method='fdr_bh')
    results_df.loc[mask, 'fdr_p'] = fdr_p

    # sort for inspection
    results_df = results_df.sort_values(by='fdr_p')
    print(results_df.head())


    # make sure fdr_p is float 
    results_df['fdr_p'] = results_df['fdr_p'].astype(float)

    results_df['age_bin'] = bin
    coef_df = pd.concat([coef_df, results_df], ignore_index=True)

    # save the rows from results_df where fdr_p < 0.05
    significant_results_df = results_df[results_df['fdr_p'] < 0.05].copy()

    # increase in volume (t>0)
    print(significant_results_df.loc[significant_results_df['t'] > 0, 'region_name'].tolist())

    # decrease
    print(significant_results_df.loc[significant_results_df['t'] < 0, 'region_name'].tolist())
    

birth_year_coef_df = coef_df[coef_df['variable'] == 'birth_year'].copy()

birth_year_coef_df.to_csv(f"/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/birth_year_coef_df_age_bins_size_{bin_size}.csv", index=False)
coef_df.to_csv(f"/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/coef_df_age_bins_size_{bin_size}.csv", index=False)