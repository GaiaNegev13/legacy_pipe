import os
import subprocess
import shutil
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from LegacyPipe.dicom_utils import classify_protocol

def convert_and_organize_yaniv(row, output_dir_root):
    participant_id = str(row['unique_id'])
    session_id = str(row['scan_date'])
    input_dir = row['directory_path']
    protocol = str(row['protocol'])
    subdir = classify_protocol(protocol)

    if subdir == 'UNKNOWN':
        return ("Unknown protocol", input_dir, "")
    output_dir = os.path.join(output_dir_root, f"sub-{participant_id}/ses-{session_id}/{subdir}")
    os.makedirs(output_dir, exist_ok=True)
    temp_dicom_dir = os.path.join(output_dir, 'dicoms')
    os.makedirs(temp_dicom_dir, exist_ok=True)

    # Copy DICOM files
    for dicom_file in os.listdir(input_dir):
        if dicom_file.endswith('.dcm'):
            shutil.copy(os.path.join(input_dir, dicom_file), temp_dicom_dir)

    base_filename = f"sub-{participant_id}_ses-{session_id}_{protocol}"
    command = [
        'dcm2niix', '-z', 'y', '-b', 'y', '-f', base_filename, '-o', output_dir, temp_dicom_dir
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    shutil.rmtree(temp_dicom_dir)
    if result.returncode == 0:
        return ("Success", input_dir, "")
    else:
        err = result.stderr.decode()
        return ("Failed", input_dir, err)

def process_yaniv_format(df, output_dir):
    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="Yaniv Format Conversion"):
        results.append(convert_and_organize_yaniv(row, output_dir))
    summary_yaniv_report(results)

def summary_yaniv_report(results):
    summary = pd.DataFrame(results, columns=['Status','DicomPath','Error'])
    print("\n--- Yaniv Conversion Report ---")
    print(summary.value_counts('Status'))
    print("\nFailed conversions:")
    print(summary[summary['Status'] == 'Failed'][['DicomPath','Error']])

# Usage Example:
# df = pd.read_csv("metadata.csv")
# process_yaniv_format(df, '/path/to/Yaniv_output')
