# original file: legacy_data/my_master/HardDrive_for_OHBM.ipynb

from importlib import metadata
import pandas as pd
from tqdm import tqdm

# metadata_df = pd.read_pickle('path/to/manually/cleaned/metadata.pkl')  # INSERT PATH TO CLEANED METADATA PKL HERE

# Define Protocol Priority Ranking (BEST to WORST)
# Lower rank number = Higher Priority
PROTOCOL_PRIORITY = [
    # Rank 0: The Gold Standard (3D Isotropic Volumetric)
    'MPRAGE', 'SPGR', 'FSPGR', 'BRAVO', 
    # Rank 1: High-Quality 3D/IR (Inversion Recovery)
    'IRSE', 'T1IR', 'AX T1W IR', 
    # Rank 2: Standard 2D or Lower-Resolution Sequences
    'Sag T1', 'Cor T1', 'Ax T1', 'T1 SE', 'AX T1 FSE', 'CorT1 FSE' 
]

def get_protocol_rank(protocol):
    """Assigns a numerical rank based on the global PROTOCOL_PRIORITY list."""
    protocol_upper = protocol.upper()
    
    for rank, keyword in enumerate(PROTOCOL_PRIORITY):
        if keyword.upper() in protocol_upper:
            # Return the rank (0 is best, 1 is next, etc.)
            return rank
    
    # Assign a very high rank for unknown/unmatched protocols (worst priority)
    return 99 

def filter_by_t1w_priority(df: pd.DataFrame) -> pd.DataFrame:
    """
    Filters the DataFrame to keep only the highest-priority T1w scan 
    for each unique subject and session.
    """
    
    print("Starting protocol prioritization...")
    
    # 1. Extract Protocol Name
    tqdm.pandas(desc="Extracting Protocol")
        
    # 2. Assign Numerical Rank
    tqdm.pandas(desc="Assigning Rank")
    df['priority_rank'] = df['protocol'].progress_apply(get_protocol_rank)
    
    # 3. Group and Select the Best Scan (Lowest Rank)
    # Group by Subject and Session
    # Then sort by the numerical rank (lowest rank is best)
    # Then drop duplicates, keeping only the first (best) entry in each group.
    
    df_sorted = df.sort_values(
        ['unique_id', 'session_id_date', 'priority_rank'], 
        ascending=[True, True, True]
    )
    
    # Drop duplicates across the subject/session columns, keeping the first (best) rank
    df_filtered = df_sorted.drop_duplicates(
        subset=['unique_id', 'session_id_date'], 
        keep='first'
    )
    
    # Report results
    total_scans = len(df)
    selected_scans = len(df_filtered)
    removed_scans = total_scans - selected_scans
    
    print(f"Prioritization complete.")
    print(f"Total initial T1w candidates: {total_scans}")
    print(f"Total unique Subject-Sessions selected: {selected_scans}")
    print(f"Duplicate/Lower-priority scans removed: {removed_scans}")
    
    return df_filtered.reset_index(drop=True)

# # Example Usage:
# full_metadata_filtered = filter_by_t1w_priority(metadata_df.copy())
# full_metadata_filtered.to_csv('/path/to/interim/full_metadata_best_protocol.csv', index=False)