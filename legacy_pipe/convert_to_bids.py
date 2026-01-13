# /path/to/LegacyPipe/convert_to_bids.py

import os
import subprocess
from pathlib import Path
import pandas as pd
from tqdm import tqdm
# We rely on map_protocol_to_bids_entities inside convert_directory_to_bids 
# which extracts the ProtocolName from the dcm2niix JSON.
from LegacyPipe.dicom_utils import convert_directory_to_bids 


# --- Helper Function to Check for Required Columns ---
def validate_dataframe_columns(df: pd.DataFrame):
    """Checks if all required columns are present in the DataFrame."""
    # We only need these for unique directory management and logging.
    required_cols = ['file_path', 'unique_id', 'protocol']
    missing_cols = [col for col in required_cols if col not in df.columns]
    
    if missing_cols:
        raise ValueError(
            f"Input DataFrame is missing required BIDS columns: {', '.join(missing_cols)}. "
            "Ensure the filtered metadata file contains these columns."
        )


def process_bids_format(df: pd.DataFrame, output_dir: str, checkpoint_file: str = "bids_results_anat.csv"):
    """
    1. Validates input DataFrame.
    2. Iterates over unique DICOM directories in the pre-filtered anatomical subset.
    """
    
    validate_dataframe_columns(df) 

    print("Step 1: Preparation and Checkpointing...")
    
    # Load previous progress
    processed_paths = set()
    if os.path.exists(checkpoint_file):
        try:
            # Load the checkpoint file
            old = pd.read_csv(checkpoint_file, header=0)
            processed_paths = set(old["DicomPath"].unique()) 
            print(f"-> Resuming from checkpoint. Already processed: {len(processed_paths):,} directories.")
        except Exception as e:
             print(f"-> Could not load checkpoint file. Starting fresh. Error: {e}")
             
    # --- Queue Generation (Memory-Optimized) ---
    
    # 1. Identify rows that have NOT been processed yet based on 'file_path'
    unprocessed_mask = ~df['file_path'].isin(processed_paths)
    
    # 2. Get the final queue by finding unique directories within the filtered subset.
    # We only need the 'file_path' column for the conversion function.
    unique_dirs_to_process = df[unprocessed_mask].drop_duplicates(subset='file_path')[['file_path']].copy()
    
    print(f"-> Unique DICOM directories in conversion queue: {len(unique_dirs_to_process):,}.")

    # Open checkpoint file in append mode.
    write_header = not os.path.exists(checkpoint_file)
    with open(checkpoint_file, "a") as f:
        if write_header:
            f.write("Status,DicomPath,Error\n")

        # Iterate over the unique directories, using tqdm for the progression bar
        for row in tqdm(unique_dirs_to_process.itertuples(index=False), total=len(unique_dirs_to_process), desc="DICOM Directory Conversion"):
            
            try:
                # The core conversion function: reads DICOM, generates JSON, maps BIDS, moves files.
                convert_directory_to_bids(
                    dicom_dir=row.file_path,
                    bids_root=output_dir
                )
                
                status, err = "Success", ""
            except Exception as e:
                # Sanitize error message before writing to CSV
                status, err = "Failed", str(e).replace(',', ';').replace('\n', ' ')

            # Write result to checkpoint immediately
            f.write(f"{status},{row.file_path},{err}\n")
            f.flush() # Forces the write to disk for crash resistance

    print("Processing complete.")
    summary_bids_report(checkpoint_file)


# summary_bids_report remains the same
def summary_bids_report(checkpoint_file):
    """
    Loads and summarizes results from the final checkpoint file for completeness.
    """
    try:
        summary = pd.read_csv(checkpoint_file)
        print("\n--- BIDS Conversion Report ---")
        print(f"Total directories processed (from checkpoint): {len(summary):,}")
        
        status_counts = summary.value_counts('Status')
        print(status_counts)
        
        print("\nFailed directories (first 5):")
        failed = summary[summary['Status'] == 'Failed']
        if not failed.empty:
            print(failed[['DicomPath', 'Error']].head()) 
        else:
            print("None.")
    except Exception as e:
        print(f"Could not generate summary report from checkpoint file: {e}")