import xml.etree.ElementTree as ET
import csv
import re
import argparse
from pathlib import Path

# --- Configuration for Array Parsing ---
# Regex to find space-separated numbers inside brackets (e.g., "[0.9375 0.9375 2]")
ARRAY_PATTERN = re.compile(r'\[\s*(.+?)\s*\]')


def extract_ids_from_filepath(filepath: Path) -> tuple[str, str]:
    """
    **CUSTOMIZED FOR:** "cat_sub-ls022_ses-20050315_T1w.xml"
    
    Extracts subject_id and session_id from a file path string, 
    specifically capturing the ID *after* the 'sub-' and 'ses-' prefixes.

    Args:
        filepath: The full Path object of the XML file.

    Returns:
        A tuple of (subject_id, session_id).
    """
    filename = str(filepath)
    
    # Attempt to find subject ID (e.g., 'sub-ls022'). The parentheses capture only the ID part.
    # Extracts 'ls022'
    match_sub = re.search(r'sub-([a-zA-Z0-9]+)', filename)
    # Access group(1) for the captured content (the ID part)
    subject_id = match_sub.group(1) if match_sub else 'N/A'

    # Attempt to find session ID (e.g., 'ses-20050315'). The parentheses capture only the ID part.
    # Extracts '20050315'
    match_ses = re.search(r'ses-([a-zA-Z0-9]+)', filename)
    # Access group(1) for the captured content (the ID part)
    session_id = match_ses.group(1) if match_ses else 'N/A'
    
    return subject_id, session_id


def process_element(element: ET.Element, results: dict, prefix: str):
    """
    Recursively processes all child elements of a given XML node, 
    flattening array-like strings into multiple columns.
    
    Args:
        element: The parent XML element (e.g., <qualitymeasures>).
        results: The dictionary to store the extracted data.
        prefix: A prefix for the column names (e.g., 'qm_' for qualitymeasures).
    """
    for child in element:
        # Construct the key, using the prefix (e.g., 'qm_SurfaceEulerNumber')
        key = f"{prefix}{child.tag}"
        value = child.text.strip() if child.text else ''
        
        # Check if the value is an array-like string (e.g., "[0.9375 0.9375 2]")
        match = ARRAY_PATTERN.search(value)
        
        if match:
            # If it's an array, split the values and flatten them into numbered columns
            values_str = match.group(1).strip()
            # Replace multiple spaces with a single space and split
            components = re.split(r'\s+', values_str)
            
            for i, component in enumerate(components, 1):
                # Create keys like 'qm_res_vx_vol_1', 'qm_res_vx_vol_2', etc.
                array_key = f"{key}_{i}"
                try:
                    results[array_key] = float(component)
                except ValueError:
                    results[array_key] = component
        else:
            # If it's a single value, store it directly
            try:
                results[key] = float(value)
            except ValueError:
                results[key] = value


def parse_xml(xml_path: Path) -> dict:
    """
    Parses a single CAT12 XML file and returns a flat dictionary of measures.
    
    Args:
        xml_path: The Path object of the XML file.

    Returns:
        A dictionary containing all extracted measures, subject_id, and session_id.
    """
    subject_id, session_id = extract_ids_from_filepath(xml_path)
    
    results = {
        'subject_id': subject_id,
        'session_id': session_id,
        'filepath': str(xml_path)
    }

    try:
        # ET.parse is fast and efficient for standard XML structures like this.
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 1. Process <qualitymeasures>
        qm_element = root.find('qualitymeasures')
        if qm_element is not None:
            # Use 'qm_' prefix for measures
            process_element(qm_element, results, 'qm_')
            
        # 2. Process <qualityratings>
        qr_element = root.find('qualityratings')
        if qr_element is not None:
            # Use 'qr_' prefix for ratings
            process_element(qr_element, results, 'qr_')
            
    except ET.ParseError as e:
        print(f"ERROR: Failed to parse XML file {xml_path}: {e}")
        return {}
    except Exception as e:
        print(f"ERROR: An unexpected error occurred while processing {xml_path}: {e}")
        return {}
        
    return results


def main():
    """
    Main function to handle file input (directory or single file) and CSV output.
    Now supports recursive search for XML files matching the pattern.
    """
    parser = argparse.ArgumentParser(
        description="Extract CAT12 quality measures from XML files to a CSV file. "
                    "Processes a single file or recursively searches a directory for files "
                    "matching the 'cat_sub-*_ses-*_T1w.xml' pattern."
    )
    parser.add_argument(
        'input_path', 
        type=Path,
        help="The path to a directory (to recursively search) or a single XML file."
    )
    parser.add_argument(
        '--output', 
        '-o', 
        default='cat12_measures.csv', 
        help="The name of the output CSV file.",
        type=Path
    )
    
    args = parser.parse_args()
    
    xml_files_to_process = []
    input_path = args.input_path

    # File Discovery Logic
    if input_path.is_dir():
        print(f"Searching recursively in directory: {input_path.resolve()}")
        # Use rglob for recursive search matching the specific pattern
        search_pattern = 'cat_sub-*_ses-*_T1w.xml'
        # Convert generator to list for easier processing
        xml_files_to_process = [p for p in input_path.rglob(search_pattern) if p.is_file()]
        
        if not xml_files_to_process:
            print(f"No XML files matching the pattern '{search_pattern}' found in {input_path}. Exiting.")
            return
            
    elif input_path.is_file():
        # Check if the single file provided matches the expected pattern
        file_name_pattern = r'cat_sub-.*_ses-.*_T1w\.xml$'
        if re.match(file_name_pattern, input_path.name):
             xml_files_to_process = [input_path]
        else:
             print(f"Error: Single file {input_path} does not match the required pattern 'cat_sub-*_ses-*_T1w.xml'. Exiting.")
             return
    else:
        print(f"Error: Input path {input_path} is neither a file nor a directory. Exiting.")
        return

    all_results = []
    
    # 1. Parse all XML files
    for xml_file in xml_files_to_process:
        # Added explicit check to ensure we only try to parse actual files
        if xml_file.is_file():
            print(f"Processing: {xml_file}")
            data = parse_xml(xml_file)
            if data:
                all_results.append(data)
        else:
            print(f"Warning: Skipping {xml_file} as it is not a valid file.")
    
    if not all_results:
        print("No valid data was extracted. Exiting.")
        return

    # 2. Determine the full set of column headers
    # We find the union of all keys from all dictionaries to ensure all columns are captured
    all_keys = set()
    for row in all_results:
        all_keys.update(row.keys())
        
    # Sort the header list logically: IDs first, then sorted metrics
    header = ['subject_id', 'session_id', 'filepath']
    metric_keys = sorted([k for k in all_keys if k not in header])
    full_header = header + metric_keys
    
    # 3. Write data to CSV
    try:
        with open(args.output, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=full_header)
            
            writer.writeheader()
            
            # Write each row, handling missing values gracefully (DictWriter handles this)
            writer.writerows(all_results)
            
        print(f"\nSuccessfully processed {len(all_results)} files from {len(xml_files_to_process)} discovered XMLs.")
        print(f"Data saved to: {args.output.resolve()}")

    except Exception as e:
        print(f"ERROR: Failed to write to CSV file {args.output}: {e}")


if __name__ == '__main__':
    # To run this script: 
    # 1. Save it as cat12_xml_parser.py
    # 2. Run from your terminal (or Linux environment):
    #
    #   To search a whole directory structure recursively:
    #   python cat12_xml_parser.py /path/to/parent/folder -o all_cat12_data.csv
    #
    #   To process a single specific file (if it matches the pattern):
    #   python cat12_xml_parser.py /path/to/file/cat_sub-ls022_ses-20050315_T1w.xml -o single_scan_data.csv
    main()