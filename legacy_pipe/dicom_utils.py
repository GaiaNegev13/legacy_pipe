# /path/to/LegacyPipe/dicom_utils.py

import re
from typing import Tuple, Optional
import os
import subprocess
import shutil
import json
from pathlib import Path


# --- Configuration Mapping (Rule-Based) ---
# ORDER MATTERS: more specific rules must come first.
BIDS_CLASSIFICATION_RULES = [
    # 1. ANATOMICAL (T1w) - HIGH PRIORITY
    # Matches MPRAGE, SPGR, FSPGR, T1, 3D T1, IR-EPI (often T1 weighted)
    (r'(?i).*IR-EPI_3iso_TI(\d+)', 'anat', 'T1w', 'acq', r'IRTI\1'), 
    (r'(?i).*(MPRAGE|SPGR|BRAVO|T1W|FSPGR|T1).*', 'anat', 'T1w', 'acq', 'T1'), 

    # 2. ANATOMICAL (FLAIR) - HIGH PRIORITY
    (r'(?i).*(FLAIR|TIRM|DARK-FLUID).*', 'anat', 'FLAIR', 'acq', 'FLAIR'),

    # 3. ANATOMICAL (T2w) - HIGH PRIORITY
    # Excludes FLAIR/DWI/Func terms explicitly
    (r'(?i).*(FSE T2|TSE T2|T2W|AXIAL T2|T2\s?\*).*', 'anat', 'T2w', 'acq', 'T2'),
    
    # 4. DIFFUSION (DTI/DWI) - Non-Anatomical
    (r'(?i)DWI|DTI|DIFFUSION|CHARMED|AxCaliber', 'dwi', 'dwi', 'acq', 'DWI'),

    # 5. FUNCTIONAL (FUNC) - Non-Anatomical
    (r'(?i)EPI.*bold|fMRI', 'func', 'bold', 'task', 'fMRI'),
    
    # 6. LOCALIZER/CALIBRATION - Non-Anatomical (Often placed in anat/fmap folders if kept)
    (r'(?i)localizer|loc|scout|survey|asset cal|tfl|b1_map', 'fmap', 'phasediff', 'acq', 'Localizer'),
    
    # 7. PERFUSION (ASL) - Non-Anatomical (Often placed in perf folder)
    (r'(?i).*ASL.*|PWI', 'perf', 'asl', 'acq', 'ASL'),
]

# The remaining functions (map_protocol_to_bids_entities, format_bids_filename, convert_directory_to_bids) 
# remain the same as the last revision. 

def map_protocol_to_bids_entities(protocol_name: str) -> Tuple[str, str, str, str]:
    """
    Uses a set of regex rules to map a proprietary protocol name to BIDS entities.
    Returns: (datatype, suffix, entity_key, entity_value)
    Returns ('', '', '', '') if no match.
    """
    p = str(protocol_name).strip()
    
    for pattern, datatype, suffix, entity_key, entity_value_rule in BIDS_CLASSIFICATION_RULES:
        match = re.search(pattern, p)
        if match:
            # Handle regex group replacement for dynamic labels (like TI\1)
            if re.match(r'r\\', entity_value_rule):
                try:
                    resolved_value = re.sub(pattern, entity_value_rule.replace('r', ''), p, count=1)
                except IndexError:
                    resolved_value = 'unknown'
            else:
                resolved_value = entity_value_rule
            
            # Sanitize the label for BIDS compliance
            label = re.sub(r'[^a-zA-Z0-9]+', '', resolved_value).lower() 
            return datatype, suffix, entity_key, label
            
    return '', '', '', '' # No match


def format_bids_filename(datatype: str, suffix: str, entity_key: str, entity_value: str, sub_id: str, ses_id: Optional[str] = None) -> str:
    """Constructs the BIDS-compliant filename prefix (e.g., sub-XX_ses-YY_acq-ZZ_T1w)."""
    
    # Base subject/session part
    prefix = f'sub-{sub_id}'
    if ses_id:
        prefix += f'_ses-{ses_id}'
    
    # Entity part (task- or acq-)
    entity_str = f'_{entity_key}-{entity_value}' if entity_value else ''
    
    # Suffix part
    if datatype == 'func' and suffix == 'bold':
        return f'{prefix}{entity_str}_bold'
    elif datatype == 'dwi' and suffix == 'dwi':
        return f'{prefix}{entity_str}_dwi'
    elif datatype == 'perf' and suffix == 'asl':
        return f'{prefix}{entity_str}_asl'
    else: 
        return f'{prefix}{entity_str}_{suffix}'


def convert_directory_to_bids(dicom_dir: str, bids_root: str):
    """
    Converts all DICOM series in a directory, relying on dcm2niix to extract
    metadata and map the files into the final BIDS structure.
    
    This handles the case where one input directory contains multiple scans/subjects.
    """
    # Create a unique temporary directory name based on the input path and process ID
    temp_dir_name = f'temp_{Path(dicom_dir).name}_{os.getpid()}'
    temp_bids_root = os.path.join(bids_root, temp_dir_name)
    os.makedirs(temp_bids_root, exist_ok=True)
    
    try:
        # 1. Run dcm2niix with a simple output format that preserves critical metadata:
        # %s: series number, %p: protocol name, %d: series description
        dcm2niix_filename_format = '%s_%p_%d'
        
        print(f"  -> Running dcm2niix on {Path(dicom_dir).name}...")
        subprocess.run(
            ['dcm2niix', '-f', dcm2niix_filename_format, '-o', temp_bids_root, '-z', 'y', '-b', 'y', dicom_dir],
            check=True, # Will raise an error if dcm2niix fails
            capture_output=True,
            text=True
        )
        
        # 2. Post-processing and Final BIDS organization (by reading JSON)
        
        for temp_filename in os.listdir(temp_bids_root):
            if temp_filename.endswith('.json'):
                
                source_json_path = os.path.join(temp_bids_root, temp_filename)
                
                try:
                    with open(source_json_path, 'r') as f:
                        metadata = json.load(f)

                    # Extract crucial metadata from the DICOM header via the JSON sidecar
                    protocol_name = metadata.get('ProtocolName', metadata.get('SeriesDescription', 'UNKNOWN'))
                    sub_id = metadata.get('PatientID', 'unk')
                    study_date = metadata.get('StudyDate', 'unkdate') 
                    
                    # --- Apply Custom Protocol Mapping ---
                    datatype, suffix, entity_key, entity_value = map_protocol_to_bids_entities(protocol_name)
                    
                    if datatype:
                        # Construct the final BIDS name prefix: sub-XX_ses-YYYYMMDD_acq-label_suffix
                        bids_nifti_filename_prefix = format_bids_filename(
                            datatype=datatype, 
                            suffix=suffix, 
                            entity_key=entity_key, 
                            entity_value=entity_value, 
                            sub_id=sub_id, 
                            ses_id=study_date
                        )
                        
                        # The base name is the dcm2niix output without extension
                        base_name = temp_filename.replace('.json', '')
                        
                        # Determine final BIDS folder structure
                        sub_dir = os.path.join(bids_root, f'sub-{sub_id}')
                        modality_dir = os.path.join(sub_dir, datatype)
                        os.makedirs(modality_dir, exist_ok=True)
                        
                        # Move and rename all associated files
                        for ext in ['.nii.gz', '.json', '.bval', '.bvec']:
                            source_file = os.path.join(temp_bids_root, base_name + ext)
                            if os.path.exists(source_file):
                                dest_file = os.path.join(modality_dir, bids_nifti_filename_prefix + ext)
                                
                                # Check if the destination file already exists before moving
                                if os.path.exists(dest_file):
                                    print(f"  -> Warning: Destination {Path(dest_file).name} exists. Skipping move.")
                                    continue
                                    
                                shutil.move(source_file, dest_file)
                                
                except Exception as e:
                    print(f"  -> Warning: Failed to process series/JSON {temp_filename}. Error: {e}")
            
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"dcm2niix failed. Stderr: {e.stderr.strip()}")
    except Exception as e:
        raise RuntimeError(f"A file system/metadata operation failed. Error: {e}")
    finally:
        if os.path.exists(temp_bids_root):
            shutil.rmtree(temp_bids_root)