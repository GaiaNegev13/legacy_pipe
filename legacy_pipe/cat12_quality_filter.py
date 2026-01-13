import os
import re
import xml.etree.ElementTree as ET
import pandas as pd
from pathlib import Path

def extract_iqr_values(cat12_derivatives_root):
    """
    Traverse CAT12 derivatives directory, parse XML files starting with 'cat_', 
    extract IQR values from qualityratings, return DataFrame with filename and IQR.
    """
    records = []
    cat12_dir = Path(cat12_derivatives_root)
    for xml_file in cat12_dir.rglob('cat_*.xml'):
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            quality = root.find('qualityratings')
            if quality is not None:
                iqr_element = quality.find('IQR')
                if iqr_element is not None and iqr_element.text:
                    iqr_value = float(iqr_element.text)
                    records.append({'file_name': xml_file.name, 'IQR': iqr_value})
        except ET.ParseError:
            print(f"⚠️ Failed to parse XML file: {xml_file}")
        except Exception as e:
            print(f"⚠️ Error processing {xml_file}: {e}")

    return pd.DataFrame(records)


def filter_scans_by_iqr(scan_iqr_df, iqr_threshold=3.0):
    """
    Filter scans by IQR threshold, add unique_id and scan_date extracted from file names.
    """
    filtered = scan_iqr_df[scan_iqr_df['IQR'] < iqr_threshold].copy()

    # Extract unique_id (3 chars after 'ls') and scan_date (8 chars after 'ses-')
    filtered['unique_id'] = filtered['file_name'].str.extract(r'(ls\d{3})')
    filtered['scan_date'] = filtered['file_name'].str.extract(r'ses-(\d{8})')

    return filtered


def group_scans_by_subject(scan_iqr_df):
    """
    Group scans by subject based on unique_id extracted from file names.
    """
    scan_iqr_df['unique_id'] = scan_iqr_df['file_name'].str.extract(r'(ls\d{3})')
    return scan_iqr_df.groupby('unique_id')


def print_grouped_scan_iqr(grouped_scans):
    """
    Print detailed IQR info grouped by subject.
    """
    for group, data in grouped_scans:
        print(f"Subject {group}:")
        for _, row in data.iterrows():
            print(f"  File: {row['file_name']}, IQR: {row['IQR']}")


def save_filtered_scans(filtered_scans_df, output_csv):
    """
    Save filtered scans DataFrame to CSV.
    """
    filtered_scans_df.to_csv(output_csv, index=False)
    print(f"Saved filtered scans to: {output_csv}")
