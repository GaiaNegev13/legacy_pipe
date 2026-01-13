import os
from pathlib import Path
import pandas as pd
import numpy as np
import matlab.engine
import logging
import re


def start_matlab_engine():
    try:
        eng = matlab.engine.start_matlab()
        logging.info("MATLAB engine started successfully.")
        return eng
    except Exception as e:
        logging.error(f"Failed to start MATLAB engine: {e}")
        raise


def stop_matlab_engine(eng):
    try:
        eng.quit()
        logging.info("MATLAB engine stopped.")
    except Exception as e:
        logging.warning(f"Error stopping MATLAB engine: {e}")


def extract_tiv_from_xml_matlab(eng, xml_path):
    """Extract TIV from CAT12 XML file using built-in MATLAB XML parsing"""
    try:
        if not xml_path.exists():
            logging.warning(f"XML file not found: {xml_path}")
            return None
        
        # Use MATLAB's built-in XML reading instead of custom function
        tiv_value = eng.eval(f"""
        try
            xml_data = xmlread('{str(xml_path)}');
            tiv_nodes = xml_data.getElementsByTagName('TIV');
            if tiv_nodes.getLength() > 0
                tiv_value = str2double(char(tiv_nodes.item(0).getTextContent()));
            else
                tiv_value = NaN;
            end
        catch
            tiv_value = NaN;
        end
        tiv_value
        """)
        return float(tiv_value) if not np.isnan(tiv_value) else None
    except Exception as e:
        logging.warning(f"TIV extraction failed for {xml_path}: {e}")
        return None


def parse_region_labels(df):
    """Parse Schaefer/Tian atlas-style region names into structural components"""
    # More flexible regex to handle various atlas formats
    pattern = re.compile(r'^(?P<atlas>\w+)_(?P<network>\w+?)_(?P<hemisphere>[LR]H)_(?P<component>[A-Za-z]+)_(?P<idx>\d+)$')
    matches = df['region_label'].str.extract(pattern)
    
    # Fallback for simpler formats
    if matches.isna().all().all():
        pattern2 = re.compile(r'^(?P<network>\w+?)_(?P<hemisphere>[LR]H)_(?P<component>[A-Za-z]+)_(?P<idx>\d+)$')
        matches = df['region_label'].str.extract(pattern2)
    
    df['network'] = matches.get('network', 'Unknown')
    df['hemisphere'] = matches.get('hemisphere', 'Unknown')
    df['component'] = matches.get('component', 'Unknown')
    df['label_name'] = df['network'].fillna('') + '_' + df['hemisphere'].fillna('') + '_' + df['component'].fillna('')
    df['base_name'] = df['label_name'].str.lower()
    df['name'] = df['region_label']
    
    # Fill NaN values with defaults
    for col in ['network', 'hemisphere', 'component', 'label_name', 'base_name', 'name']:
        df[col] = df[col].fillna('Unknown')
    
    return df


def extract_volumes_for_subject(eng, subject_id, session_id, atlas_name, derivatives_dir):
    # Handle NaN/float values by converting to string first
    subject_id = str(subject_id) if pd.notna(subject_id) else ''
    session_id = str(session_id) if pd.notna(session_id) else ''
    
    # Skip if either ID is empty/invalid
    if not subject_id or not session_id or subject_id == 'nan' or session_id == 'nan':
        logging.error(f"Invalid subject_id ({subject_id}) or session_id ({session_id})")
        return None
    
    subject_id = subject_id if subject_id.startswith('sub-') else f'sub-{subject_id}'
    session_id = session_id if session_id.startswith('ses-') else f'ses-{session_id}'

    anat_path = Path(derivatives_dir) / subject_id / session_id / 'anat'
    mat_file = anat_path / f'catROI_{subject_id}_{session_id}_T1w.mat'
    xml_file = anat_path / f'cat_{subject_id}_{session_id}_T1w.xml'

    if not mat_file.exists():
        logging.error(f"Missing MAT file: {mat_file}")
        return None

    try:
        s = eng.load(str(mat_file))
        all_data = s.get('S')
    except Exception as e:
        logging.error(f"Error loading {mat_file}: {e}")
        return None

    atlas_data = all_data.get(atlas_name)
    if not atlas_data or not atlas_data.get('data'):
        logging.warning(f"Atlas {atlas_name} not found in {mat_file}")
        return None

    data = atlas_data.get('data')
    gm_vol = np.array(data.get('Vgm')).flatten() * 1000
    wm_vol = np.array(data.get('Vwm')).flatten() * 1000
    csf_vol = np.array(data.get('Vcsf')).flatten() * 1000
    region_ids = np.array(atlas_data.get('ids')).flatten()
    
    # Create region labels based on atlas format
    atlas_prefix = atlas_name.split('_')[0] if '_' in atlas_name else atlas_name
    region_labels = [f"{atlas_prefix}_{int(r)}" for r in region_ids]

    df = pd.DataFrame({
        'subject_id': subject_id,
        'session_id': session_id,
        'atlas_name': atlas_name,
        'region_label': region_labels,
        'gm_volume_mm3': gm_vol,
        'wm_volume_mm3': wm_vol,
        'csf_volume_mm3': csf_vol
    })

    df['tiv'] = extract_tiv_from_xml_matlab(eng, xml_file)
    df['total_gm_volume'] = df['gm_volume_mm3'].sum()
    df['IQR'] = df[['gm_volume_mm3', 'wm_volume_mm3', 'csf_volume_mm3']].apply(np.nanstd, axis=1)
    
    return parse_region_labels(df)


def batch_process_volumes(metadata_df, atlas_name, derivatives_dir):
    eng = start_matlab_engine()
    all_data = []
    missing_files = []

    try:
        for idx, row in metadata_df.iterrows():
            subject_id = row['unique_id']
            session_id = row['scan_date']
            
            # Skip rows with NaN values
            if pd.isna(subject_id) or pd.isna(session_id):
                logging.warning(f"Skipping row {idx}: NaN values in unique_id or scan_date")
                continue
                
            result = extract_volumes_for_subject(eng, subject_id, session_id, atlas_name, derivatives_dir)
            if result is None:
                missing_files.append((str(subject_id), str(session_id)))
                continue
                
            melted = result.melt(
                id_vars=['subject_id', 'session_id', 'atlas_name', 'region_label', 'tiv',
                         'total_gm_volume', 'IQR', 'network', 'component', 'hemisphere',
                         'label_name', 'base_name', 'name'],
                value_vars=['gm_volume_mm3', 'wm_volume_mm3', 'csf_volume_mm3'],
                var_name='tissue',
                value_name='volume'
            )
            melted['metric'] = 'volume_mm3'  # Add metric column as shown in your example
            all_data.append(melted)
            
    finally:
        stop_matlab_engine(eng)

    # Print summary of missing files
    if missing_files:
        print("\n" + "="*50)
        print("MISSING FILES SUMMARY")
        print("="*50)
        for subj, sess in missing_files:
            print(f"  - Subject: {subj}, Session: {sess}")
        print(f"\nTotal missing: {len(missing_files)} out of {len(metadata_df)} scans")
        print(f"Successfully processed: {len(all_data)} scans")
        print("="*50 + "\n")

    if all_data:
        return pd.concat(all_data, ignore_index=True)
    return pd.DataFrame()
