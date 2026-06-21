# script to create network_component names and aggregate the rois in the atlas csv

import pandas as pd

# load atlas csv
atlas_csv = pd.read_csv("/home/gaia/Projects/legacy_data/my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv")

# replace "parietal " with "parietal"
atlas_csv['component'] = atlas_csv['component'].str.replace("parietal ", "parietal")

# save the aggregated rois in a reusable df

# Group by both network and component, then turn the 'index' column into a list
aggregated_rois = (
    atlas_csv.groupby(['network', 'component'])['index']
    .apply(list)
    .reset_index()
)

# Create the 'network_component' name column by joining the two strings
aggregated_rois['network_component'] = (
    aggregated_rois['network'] + " - " + aggregated_rois['component']
)

# Rename the index column to 'roi_list' for clarity
aggregated_rois = aggregated_rois.rename(columns={'index': 'roi_list'})

aggregated_rois.to_csv("/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/aggregated_rois.csv", index=False)