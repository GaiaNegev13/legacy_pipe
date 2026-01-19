# prioritize t1w protocols for subjects with many protocols 
from legacy_pipe.legacy_pipe.t1w_bids_conversion import process_t1w_df
from legacy_pipe.legacy_pipe.prioritize_t1w_protocols import filter_by_t1w_priority
import pandas as pd

metadata_df = pd.read_pickle('path/to/manually/cleaned/metadata.pkl')  # INSERT PATH TO CLEANED METADATA PKL HERE

full_metadata_filtered = filter_by_t1w_priority(metadata_df.copy())
full_metadata_filtered.to_csv('/path/to/interim/full_metadata_best_protocol.csv', index=False)

# convert to bids only the t1w with highest priority
# Example Usage:
OUTPUT_BIDS_DIR = '/home/gaia/Projects/legacy_data/BIDS_converted' # EDIT - Output BIDS directory
process_t1w_df(full_metadata_filtered, OUTPUT_BIDS_DIR)