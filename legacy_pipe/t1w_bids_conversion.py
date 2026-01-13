
# original file: legacy_data/my_master/HardDrive_for_OHBM.ipynb
import os
import subprocess
from pathlib import Path
from datetime import datetime
import pandas as pd
from tqdm import tqdm

# CONVERSION FUNCTION (Simplified for T1w only)
def convert_t1w(row, output_dir):
    """Converts a single T1w DICOM series to BIDS format."""
    
    subject_id = str(row['unique_id'])
    scan_date = str(row['session_id_date'])  # Expected format: 'YYYYMMDD'
    dicom_path = row['folder_path'] # Path to the DICOM directory for this series

    # Fixed BIDS parameters for this task
    modality = 'anat'
    suffix = 'T1w' 

    # Determine Session ID
    try:
        scan_date_obj = datetime.strptime(scan_date, '%Y%m%d')
        session_id = scan_date_obj.strftime('%Y%m%d')
    except ValueError:
        print(f"❌ Invalid scan_date format: {scan_date}, skipping conversion for subject {subject_id}.")
        return

    # Create BIDS output directory: .../sub-XX/ses-YY/anat/
    bids_sub_dir = os.path.join(output_dir, f"sub-{subject_id}", f"ses-{session_id}", modality)
    os.makedirs(bids_sub_dir, exist_ok=True)

    # Set filename: sub-XX_ses-YY_T1w.nii.gz
    base_filename = f"sub-{subject_id}_ses-{session_id}_{suffix}"
    
    # Check if the file already exists
    flag_exists = Path(bids_sub_dir) / f"{base_filename}.nii.gz"
    if flag_exists.exists():
        # Using dcm2niix -f, it names the file based on the template
        print(f"⚠️ File already exists: {flag_exists.name}, skipping.")
        return

    # --- Run dcm2niix command ---
    command = [
        'dcm2niix',
        '-z', 'y',                 # Compress to .nii.gz
        '-b', 'y',                 # Create BIDS JSON sidecar
        '-f', base_filename,       # Output filename template (dcm2niix uses this)
        '-o', bids_sub_dir,        # Output directory
        dicom_path                 # Input DICOM directory
    ]

    print(f"🔄 Converting: {dicom_path} -> {base_filename}.nii.gz")
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode == 0:
        print(f"✅ Converted and saved to: {flag_exists.parent.name}/{flag_exists.name}\n")
    else:
        print(f"❌ Conversion failed for {dicom_path}")
        print(result.stderr.decode())


def process_t1w_df(df_filtered: pd.DataFrame, output_dir: str):
    """Processes the filtered DataFrame for conversion."""
    total_rows = len(df_filtered)
    print(f"📦 Starting T1w conversion for {total_rows} scans...")
    
    # Use tqdm to monitor the progress of the slow I/O bound conversion
    for _, row in tqdm(df_filtered.iterrows(), total=total_rows, desc="T1w BIDS Conversion"):
        convert_t1w(row, output_dir)
    print(f"🎉 Conversion run complete for {total_rows} rows.")


# Example Usage:
OUTPUT_BIDS_DIR = '/home/gaia/Projects/legacy_data/BIDS_converted' # EDIT - Output BIDS directory
info_for_conversion_filtered = pd.read_csv('/home/gaia/Projects/legacy_data/refactored_project/data/interim/full_metadata_best_protocol.csv')
process_t1w_df(info_for_conversion_filtered, OUTPUT_BIDS_DIR)