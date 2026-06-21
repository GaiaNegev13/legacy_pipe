import os
import pandas as pd
import yabplot as yab

# ── Setup Paths ──────────────────────────────────────────────────────────────
atlas_nii_path = '/media/storage/MATLAB_atlases-20250612T134418Z-1-001/MATLAB_atlases/schaefer2018tian2020_400_7.nii'
atlas_csv_path = '/home/gaia/Projects/legacy_data/my_master/space-MNI152_atlas-schaefer2018tian2020_res-1mm_den-400_div-7networks_dseg.csv'

# Permanent location for your meshes
OUT_DIR = '/home/gaia/Projects/legacy_data/legacy_pipe/models/atlases/subcortical/tian2020_s7'

# ── Logic ────────────────────────────────────────────────────────────────────
if not os.path.exists(OUT_DIR):
    os.makedirs(OUT_DIR, exist_ok=True)
    
    print("Reading labels...")
    atlas_csv = pd.read_csv(atlas_csv_path)
    atlas_labels = dict(zip(atlas_csv['index'], atlas_csv['name']))

    # Extract subcortical only
    sub_labels = {idx: name for idx, name in atlas_labels.items() if not name.startswith('7Networks_')}

    print(f"Building {len(sub_labels)} meshes. This might take a minute...")
    yab.build_subcortical_atlas(
        nii_path=atlas_nii_path,
        labels_dict=sub_labels,
        out_dir=OUT_DIR,
        smooth_i=20,
        smooth_f=0.5
    )
    print(f"✅ Atlas successfully built and saved to {OUT_DIR}")
else:
    print(f"Checking: Atlas already exists at {OUT_DIR}")