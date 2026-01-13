from pathlib import Path
import pandas as pd
from pydicom import dcmread
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

METADATA_FIELDS = {
    'participant_id': "PatientID",
    'participant_name': "PatientName",
    'sex': "PatientSex",
    'dob': "PatientBirthDate",
    'scan_date': "AcquisitionDate",
    'scan_time': "StudyTime",
    'age_at_scan': "PatientAge",
    'weight': "PatientWeight",
    'protocol': "SeriesDescription",
    'institute': "InstitutionName",
    'manufacturer': "Manufacturer"
}

def extract_metadata(dicom_path: Path):
    try:
        ds = dcmread(str(dicom_path), stop_before_pixels=True)
        return {k: str(ds.get(v, "")) for k, v in METADATA_FIELDS.items()}
    except Exception as e:
        tqdm.write(f"Error reading {dicom_path}: {e}")
        return None

def build_metadata_dataframe(source_dir: Path, max_workers=8, batch_size=1000):
    """Efficient metadata extraction with batch submission to ThreadPoolExecutor."""
    metadata_records = []
    dicom_files = source_dir.rglob('*.dcm')  # lazy generator

    # Process in batches
    batch = []
    for f in dicom_files:
        batch.append(f)
        if len(batch) >= batch_size:
            metadata_records.extend(process_batch(batch, max_workers))
            batch = []

    # Process remaining
    if batch:
        metadata_records.extend(process_batch(batch, max_workers))

    return pd.DataFrame(metadata_records)

def process_batch(batch, max_workers):
    records = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(extract_metadata, f): f for f in batch}
        for future in tqdm(as_completed(futures), total=len(futures), desc="Extracting metadata", unit="DICOM", leave=False):
            result = future.result()
            if result:
                result['file_path'] = str(futures[future])
                records.append(result)
    return records

if __name__ == "__main__":
    source = Path("/path/to/SortedFolders") # INSERT PATH TO SORTED DICOM FOLDERS HERE
    print("Starting metadata extraction...")

    df = build_metadata_dataframe(source)

    output_csv = Path("/path/to/initial/metadata.csv") # INSERT PATH TO OUTPUT CSV HERE
    df.to_csv(output_csv, index=False)

    print(f"Metadata extraction completed! Saved {len(df)} records to {output_csv}")
