import os
import subprocess
from pathlib import Path
import pandas as pd
from tqdm import tqdm
from LegacyPipe.dicom_utils import format_scan_time, protocol_suffix

def convert_and_organize_bids(row, output_dir):
    subject_id = str(row['unique_id'])
    scan_date = str(row['scan_date'])
    dicom_path = row['directory_path']
    protocol = str(row['protocol'])
    scan_time = format_scan_time(row.get('scan_time', ''))

    try:
        session_id = pd.to_datetime(scan_date, format='%Y%m%d').strftime('%Y%m%d')
    except Exception as e:
        return ("Invalid scan_date", dicom_path, str(e))

    suffix = protocol_suffix(protocol)
    if not suffix:
        return ("Unknown protocol", dicom_path, "")

    modality = 'anat' if suffix in ['FLAIR', 'T1w'] else 'DWI'

    bids_sub_dir = os.path.join(output_dir, f"sub-{subject_id}", f"ses-{session_id}", modality)
    os.makedirs(bids_sub_dir, exist_ok=True)

    base_filename = f"sub-{subject_id}_ses-{session_id}_{suffix}"
    output_file = Path(bids_sub_dir) / f"{base_filename}.nii.gz"

    if output_file.exists():
        return ("Already converted", dicom_path, "")

    # Run dcm2niix
    command = [
        'dcm2niix',
        '-z', 'y',
        '-b', 'y',
        '-f', base_filename,
        '-o', bids_sub_dir,
        dicom_path
    ]
    result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode == 0:
        return ("Success", dicom_path, "")
    else:
        err = result.stderr.decode()
        return ("Failed", dicom_path, err)


def process_bids_format(df, output_dir):
    results = []
    for _, row in tqdm(df.iterrows(), total=len(df), desc="BIDS Conversion"):
        result = convert_and_organize_bids(row, output_dir)
        results.append(result)

    summary_bids_report(results)


def summary_bids_report(results):
    summary = pd.DataFrame(results, columns=['Status','DicomPath','Error'])
    print("\n--- BIDS Conversion Report ---")
    print(summary.value_counts('Status'))
    print("\nFailed conversions:")
    print(summary[summary['Status'] == 'Failed'][['DicomPath','Error']])
