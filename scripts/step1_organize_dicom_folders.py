from pathlib import Path
import os
import shutil
from tqdm import tqdm
import time

def rename_with_underscores(root: Path):
    """Rename all files/folders replacing spaces with underscores."""
    tqdm.write("➡️ Step 1: Renaming files and folders...")
    count = 0
    start_time = time.time()
    for path in tqdm(root.rglob('*'), desc="Renaming files/folders", unit="file", leave=True):
        if ' ' in path.name:
            new_path = path.parent / path.name.replace(' ', '_')
            if not new_path.exists():
                try:
                    path.rename(new_path)
                except Exception as e:
                    tqdm.write(f"Error renaming {path}: {e}")
        count += 1
    elapsed = time.time() - start_time
    tqdm.write(f"✅ Renaming completed ({count} items) in {elapsed:.1f}s.\n")

def move_dicoms_to_subfolder(root: Path):
    """Move DICOM files into 'dicom_only' subfolders if mixed with non-DICOMs."""
    tqdm.write("➡️ Step 2: Moving DICOM files...")
    folder_count = 0
    start_time = time.time()
    # Walk lazily through all directories
    for dirpath, _, filenames in tqdm(os.walk(root), desc="Scanning folders", unit="folder", leave=True):
        dirpath = Path(dirpath)
        dicoms = [f for f in filenames if f.lower().endswith('.dcm')]
        others = [f for f in filenames if not f.lower().endswith('.dcm')]
        if dicoms and others:
            subfolder = dirpath / 'dicom_only'
            subfolder.mkdir(exist_ok=True)
            # Move dicoms safely (cross-filesystem)
            for f in dicoms:
                src = dirpath / f
                dst = subfolder / f
                try:
                    shutil.move(str(src), str(dst))
                except Exception as e:
                    tqdm.write(f"Error moving {f}: {e}")
            tqdm.write(f"Dicoms moved to {subfolder}")
        folder_count += 1
    elapsed = time.time() - start_time
    tqdm.write(f"✅ DICOM moving completed ({folder_count} folders) in {elapsed:.1f}s.\n")

if __name__ == "__main__":
    root_dir = Path("") # INSERT PATH TO ROOT DIRECTORY HERE

    print("Starting full process for large folders...")

    rename_with_underscores(root_dir)
    move_dicoms_to_subfolder(root_dir)

    print("All done! Everything processed successfully.")
