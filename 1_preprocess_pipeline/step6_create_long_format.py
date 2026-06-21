import os
import pandas as pd
import xml.etree.ElementTree as ET
import re
from tqdm import tqdm

# ---------- Define Functions ------------

def read_volumes(subject_id, session_id, atlas_name, bids_derivatives_dir):
    """
    Fast XML extraction. Converts 'ROI001' to '1', 'ROI454' to '454', etc.
    """
    # Standardize BIDS IDs
    sub = f"sub-{subject_id}" if not str(subject_id).startswith('sub-') else str(subject_id)
    ses = f"ses-{session_id}" if not str(session_id).startswith('ses-') else str(session_id)
    
    xml_file_name = f'catROI_{sub}_{ses}_T1w.xml'
    xml_path = os.path.join(bids_derivatives_dir, sub, ses, 'anat', xml_file_name)
    
    if not os.path.exists(xml_path):
        return pd.DataFrame()

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # Navigate to the specific atlas node
        atlas_node = root.find(atlas_name)
        if atlas_node is None:
            return pd.DataFrame()

        # 1. Extract and Clean Region Labels
        names_node = atlas_node.find('names')
        if names_node is not None:
            region_labels = []
            for item in names_node.findall('item'):
                raw_text = item.text.strip() # e.g., "ROI001"
                # Remove "ROI" and leading zeros to get "1"
                # Using regex to find only the digits
                clean_label = re.search(r'\d+', raw_text)
                if clean_label:
                    # Convert to int then str to remove leading zeros (001 -> 1)
                    region_labels.append(str(int(clean_label.group())))
                else:
                    region_labels.append(raw_text)
        else:
            return pd.DataFrame()

        # 2. Extract and Parse Volumes
        data_node = atlas_node.find('data')
        if data_node is None:
            return pd.DataFrame()

        def parse_semicolon_string(node_name):
            node = data_node.find(node_name)
            if node is None or not node.text:
                return [0.0] * len(region_labels)
            
            clean_text = node.text.replace('[', '').replace(']', '').strip()
            # Split and convert to cubic mm (multiplying by 1000)
            return [float(val) * 1000 for val in clean_text.split(';') if val.strip()]

        vgm = parse_semicolon_string('Vgm')
        vwm = parse_semicolon_string('Vwm')
        vcsf = parse_semicolon_string('Vcsf')

        # Safety check: Ensure labels and data match in length
        if len(region_labels) != len(vgm):
            print(f"Warning: Mismatch in {xml_file_name} for {atlas_name}")

        return pd.DataFrame({
            'subject_id': subject_id,
            'session_id': session_id,
            'atlas_name': atlas_name,
            'region_label': region_labels,
            'gm_volume_mm3': vgm,
            'wm_volume_mm3': vwm,
            'csf_volume_mm3': vcsf
        })

    except Exception as e:
        print(f"Error parsing {xml_file_name}: {e}")
        return pd.DataFrame()
    
def extract_tiv(subject_id, session_id, bids_derivatives_dir):
    # 1. Ensure IDs are strings and handle potential NaN
    subject_id = str(subject_id)
    session_id = str(session_id)

    # 2. Standardize BIDS IDs (add prefix if missing, avoid doubling)
    sub = f"sub-{subject_id}" if not subject_id.startswith('sub-') else subject_id
    ses = f"ses-{session_id}" if not session_id.startswith('ses-') else session_id

    # 3. Path construction using standardized 'sub' and 'ses' variables
    full_path = os.path.join(
        bids_derivatives_dir, 
        sub, 
        ses, 
        'anat', 
        f"cat_{sub}_{ses}_T1w.xml"
    )
        
    try:
        # 1. Parse the tree and get the root immediately
        tree = ET.parse(full_path)
        root = tree.getroot()
        
        # 2. Use the direct path from the root
        # CAT12 structure is usually <S><subjectmeasures><vol_TIV>
        tiv_node = root.find("subjectmeasures/vol_TIV")
        
        if tiv_node is not None and tiv_node.text:
            return float(tiv_node.text)
            
    except FileNotFoundError:
        return None # Expected for missing scans
    except Exception as e:
        print(f"Error in {subject_id}/{session_id}: {e}")
        return None
    return None

# ------------ Run --------------

if __name__ == "__main__":
    # --- Step 1: Define file paths and parameters for the batch process ---
    BIDS_DERIVATIVES_DIR = '/home/gaia/Projects/HardDriveOutput/BIDS_under_thirties/derivatives/CAT12.9_2577'
    OUTPUT_CSV_PATH = '/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_under_thirties_long_format.csv'
    ATLAS_NAME = 'schaefer2018tian2020_400_7'

    # Read the CSV file and explicitly set the data types for specific columns
    metadata = pd.read_csv(
        '/home/gaia/Projects/legacy_data/refactored_project/data/processed/HardDrive_under_thirties_full_metadata_filtered.csv',
        dtype={'unique_id': str, 'session_id_date': str})
    
    metadata['unique_id'] = metadata['unique_id'].astype(str)
    metadata['session_id_date'] = metadata['session_id_date'].astype(str)

    # List of ALL metadata columns to be added to the long format.
    # We exclude the columns already present in vol_df (like subject/session IDs) 
    # but include all others that define the subject/scan.
    # Based on your provided column index, let's select the relevant ones:
    METADATA_COLS_TO_ADD = [
        'sex', 'dob', 'scan_date', 'scan_time', 'age_at_scan', 'weight',       
        'protocol', 'institute', 'manufacturer', 'file_path', 
        'age_in_years', 'estimated_critical_info', 'birth_year'
    ]


    # DataFrames to hold regional volumes from each subject
    long_format = pd.DataFrame()
    
    # --- Step 2: Loop through each subject/session and process the data ---
    print(f"Starting batch processing for {len(metadata)} subjects...")
    print("-" * 50)
    
    for index, row in tqdm(metadata.iterrows()): 
        subj_id = row['unique_id']
        session_id = row['session_id_date']
        
        # Call the function to get the data for one subject
        vol_df = read_volumes(subj_id, session_id, ATLAS_NAME, BIDS_DERIVATIVES_DIR)

        # Process the data if the DataFrame is not empty
        if not vol_df.empty:
            
            # 1. Filter the current subject's metadata using ALL the desired columns
            # We use row[METADATA_COLS_TO_ADD].to_dict() to extract all the columns.
            subject_meta = row[METADATA_COLS_TO_ADD].to_dict()
            
            # 2. Use pandas melt to transform the DataFrame into long format
            subject_long_df = pd.melt(
                vol_df,
                id_vars=['subject_id', 'session_id', 'atlas_name', 'region_label'],
                value_vars=['gm_volume_mm3', 'wm_volume_mm3', 'csf_volume_mm3'],
                var_name='tissue_type',
                value_name='volume_mm3'
            )
            
            # 3. Add ALL extracted metadata columns to the long-format DataFrame
            # Loop through the dictionary and add each column, which is cleaner than
            # writing assignment lines for every column.
            for col_name, col_value in subject_meta.items():
                subject_long_df[col_name] = col_value

            # 4. Extract TIV and add it to the subject's long-format DataFrame
            subject_long_df['tiv'] = extract_tiv(subj_id, session_id, BIDS_DERIVATIVES_DIR)
            
            # 5. Now, concatenate the long-format data to the main DataFrame
            long_format = pd.concat([long_format, subject_long_df], ignore_index=True)

            print(f"Processed data for **{subj_id} / {session_id}** successfully.")
        
    # --- Step 3: Save the final output after the loop is complete ---
    if not long_format.empty:
        # Reorder columns for better readability (optional)
        # Construct the desired column order dynamically
        ID_COLS = ['subject_id', 'session_id']
        VOLUME_COLS = ['atlas_name', 'region_label', 'tissue_type', 'volume_mm3', 'tiv']
        
        # The final column order: IDs + All Metadata + Volume/Region info
        desired_cols = ID_COLS + METADATA_COLS_TO_ADD + VOLUME_COLS
        
        # Ensure we only try to select columns that exist in the DataFrame
        final_cols = [col for col in desired_cols if col in long_format.columns]

        long_format = long_format[final_cols]
        
        long_format.to_csv(OUTPUT_CSV_PATH, index=False)
        print("\n" + "=" * 50)
        print("✅ **Successfully created and saved the master DataFrame in long format.**")
        print("=" * 50)
        print(f"Final DataFrame shape: {long_format.shape}")
        print("\n**First 5 rows with all metadata columns:**")
        print(long_format.head())
    else:
        print("\nNo data was processed. Please check your inputs.")