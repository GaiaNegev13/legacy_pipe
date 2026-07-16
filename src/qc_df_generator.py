import os
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path
import re

def extract_cat12_metrics_wide(root_dir, source, approved_scans_set=None):
    """
    Recursively scans 'root_dir' for CAT12 XML files (cat_*.xml),
    checks if they are in the approved_scans_set, and extracts only 
    the quality metrics into a wide-format DataFrame.
    """
    root_dir = Path(root_dir)
    records = []

    for xml_file in root_dir.rglob("cat_*.xml"):
        # 1. Fast Regex Check on Filename
        filename = xml_file.name
        sub_match = re.search(r"sub-([a-zA-Z0-9]+)", filename)
        ses_match = re.search(r"ses-([0-9]+)", filename)
        
        subject_id = sub_match.group(1) if sub_match else None
        session_id = ses_match.group(1) if ses_match else None

        # Filter out unapproved scans immediately
        if approved_scans_set is not None:
            if (subject_id, session_id) not in approved_scans_set:
                continue

        try:
            tree = ET.parse(xml_file)
            xml_root = tree.getroot()

            # Minimal base record
            record = {
                'subject_id': subject_id,
                'session_id': session_id,
                'file_name': filename,
                'source': source
            }

            # 2. Extract quality metrics only (no scanner metadata parsed here)
            for section_name in ['qualitymeasures', 'qualityratings']:
                section = xml_root.find(section_name)
                if section is not None:
                    for child in section:
                        if child.text is not None:
                            val_str = child.text.strip()
                            # Handle spatial resolution/array metrics if present
                            if val_str.startswith('[') and val_str.endswith(']'):
                                clean_val = val_str.strip('[]').strip()
                                components = re.split(r'\s+', clean_val)
                                for i, comp in enumerate(components, 1):
                                    try:
                                        record[f"{child.tag}_{i}"] = float(comp)
                                    except ValueError:
                                        record[f"{child.tag}_{i}"] = comp
                            else:
                                try:
                                    record[child.tag] = float(val_str)
                                except ValueError:
                                    record[child.tag] = val_str

            records.append(record)

        except Exception as e:
            print(f"⚠️ Error parsing approved file {xml_file}: {e}")
            continue

    if not records:
        return pd.DataFrame()

    df_wide = pd.DataFrame(records)
    base_cols = ['subject_id', 'session_id', 'file_name', 'source']
    metric_cols = [c for c in df_wide.columns if c not in base_cols]
    return df_wide[base_cols + sorted(metric_cols)]