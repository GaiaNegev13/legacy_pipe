import os
import re
import json
from pathlib import Path
import pandas as pd
from tqdm import tqdm

def list_nifti_by_protocol(root_dir, protocol, output_file=None, subj_map_path='subj_map.json'):
    if output_file is None:
        output_file = f"{protocol}_list.txt"

    nii_files = []
    found_participants = set()
    processed_pairs = set()

    # Load manual labels whitelist
    whitelisted_participants = None
    try:
        with open(subj_map_path, 'r') as f:
            subj_map = json.load(f)
        whitelisted_participants = {uid for uid, d in subj_map.items() if d.get('manual_labeling') == 'y'}
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: '{subj_map_path}' not found or invalid.")

    # Collect pairs already processed by CAT12
    derivatives = os.path.join(root_dir, 'derivatives', 'CAT12.9_2577')
    if os.path.exists(derivatives):
        for dirpath, _, files in os.walk(derivatives):
            for file in files:
                m = re.match(r".*sub-(ls\d+)_ses-(\d+)_.*", file)
                if m:
                    processed_pairs.add(m.groups())

    # Search for nifti files matching filter
    for dirpath, _, files in os.walk(root_dir):
        if 'derivatives' in dirpath.split(os.sep):
            continue
        for file in files:
            if not file.endswith(f"_{protocol}.nii"):
                continue
            m = re.match(r"sub-(ls\d+)_ses-(\d+)_.*", file)
            if not m:
                continue
            subj, ses = m.groups()
            if whitelisted_participants and subj not in whitelisted_participants:
                continue
            if (subj, ses) in processed_pairs:
                continue
            full_path = os.path.join(dirpath, file)
            nii_files.append(full_path)
            found_participants.add(subj)

    # Save to output file
    with open(output_file, 'w') as f:
        for path in nii_files:
            f.write(f"'{path}'\n")

    print(f"Found {len(nii_files)} *_{protocol}.nii files (filtered).")
    print(f"Unique participants: {len(found_participants)}")
    print(f"List saved to {output_file}")
    return nii_files, found_participants

def insert_file_list_to_matlab_script(nifti_list, matlab_template_path, matlab_output_path):
    list_str = '\n'.join([f"'{path}'" for path in nifti_list])
    start_marker = 'matlabbatch{1}.spm.tools.cat.estwrite.data = {'
    end_marker = '};'

    with open(matlab_template_path, 'r') as f:
        lines = f.readlines()

    output_lines = []
    inside_data_block = False
    for line in lines:
        if start_marker in line:
            output_lines.append(start_marker + '\n')
            output_lines.append(list_str + '\n')
            inside_data_block = True
            continue
        if inside_data_block and end_marker in line:
            output_lines.append(end_marker + '\n')
            inside_data_block = False
            continue
        if not inside_data_block:
            output_lines.append(line)

    with open(matlab_output_path, 'w') as f:
        f.writelines(output_lines)

    print(f"Updated MATLAB batch script saved to {matlab_output_path}")
