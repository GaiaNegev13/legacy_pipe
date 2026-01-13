import os
import re
import json
from pathlib import Path
import pandas as pd
from tqdm import tqdm

def load_and_filter_manual_labels(label_csv_path):
    df = pd.read_csv(label_csv_path)
    df = df.dropna(subset=['Name', 'y/n'])
    return df

def update_subj_map_with_manual_labels(subj_map_path, manual_labels_df):
    with open(subj_map_path, 'r') as f:
        subj_map = json.load(f)

    name_to_label = dict(zip(manual_labels_df['Name'], manual_labels_df['y/n']))
    # Update manual label for subjects in subj_map
    for uid, data in subj_map.items():
        label = name_to_label.get(data.get('name'))
        if label:
            subj_map[uid]['manual_labeling'] = label

    with open(subj_map_path, 'w') as f:
        json.dump(subj_map, f, indent=4)
    return subj_map