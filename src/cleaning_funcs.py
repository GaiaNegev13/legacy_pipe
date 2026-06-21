import pandas as pd
import json
import os
from datetime import datetime
import calendar


def remove_empty_rows(df):
    filter_cols = [c for c in df.columns if c not in ['CD_name', 'directory_name', 'path']]
    return df[~df[filter_cols].isna().all(axis=1)]

def normalize_names(df, name_col='participant_name'):
    names = df[name_col].astype(str)
    names = names.str.replace('^', ' ', regex=False).str.replace('_', ' ', regex=False).str.title()
    df[name_col] = names.apply(lambda n: ' '.join(sorted(n.strip().split())))
    return df

def replace_values(
    df,
    column_to_change,
    new_value,
    column_of_specification=None,
    value_of_specification=None
):
    '''
    Replace values in a DataFrame column based on a condition.
    '''
    condition = df[column_of_specification] == value_of_specification
    df.loc[condition, column_to_change] = new_value

    return df



def align_ids(df, id_col='participant_id'):
    '''
    Standardize participant IDs by: 
    removing dashes
    converting to string
    Pads IDs with leading zeros to length 9.
    Removes leading zero on 10-digit IDs.

    '''
    # convert to string and remove dashes
    df[id_col] = df[id_col].astype(str).str.replace('-', '', regex=False)

    # Pad IDs with leading zeros to length 9
    df[id_col] = df[id_col].apply(lambda x: x.zfill(9) if len(x) < 9 else x)

    # For 10 digit IDs starting with zero, remove leading zero
    df[id_col] = df[id_col].apply(lambda x: x[1:] if len(x) == 10 and x.startswith('0') else x)
    return df


def group_ids_by_name(df, name_col='participant_name', id_col='participant_id'):
    return df.groupby(name_col)[id_col].apply(set).reset_index()

def group_sex_by_id(df, id_col='participant_id', sex_col='sex', name_col='participant_name'):
    return df.groupby(id_col).agg(
        sex=(sex_col, lambda x: set(x)),
        participant_name=(name_col, 'first')
    ).reset_index()

import numpy as np

def handle_nan_name_value(name):
    """
    Normalize a single name value for comparison logic:
    - Convert various nan forms to None
    - Leave regular names unchanged (already normalized by normalize_names())
    """
    if name is None:
        return None
    if isinstance(name, float) and np.isnan(name):
        return None
    if isinstance(name, str):
        clean = name.strip().lower()
        if clean in ["nan", "", "none", "null"]:
            return None
    return name


def check_already_exists(
    name, id_, sex, id_index, subj_map, conflicts
):    
    """
    Return True if this subject already exists or if there is an ID conflict.
    Return False if this subject should be added.
    Rules:
    Same name + different ID → allowed
    Same name + same sex + different ID → allowed
    "nan", "Nan", "", np.nan → all treated as None, unlimited repeats
    Same ID + mismatching name/sex → blocked with warning
    Same ID + same name + same sex → treated as already existing
    
    - Check conflict using id_index
    - Store conflicts instead of printing
    """
    name_norm = handle_nan_name_value(name)

    # --- Case 1: ID already seen ---
    if id_ in id_index:
        unique_id = id_index[id_]
        subj = subj_map[unique_id]

        existing_name = handle_nan_name_value(subj["name"])
        existing_sex = subj["sex"]

        # exact match → already exists
        if (existing_name == name_norm) and (existing_sex == sex):
            return True

        # conflict → store it
        conflicts.append({
            "unique_id": unique_id,
            "existing_name": subj["name"],
            "existing_id": subj["id"],
            "existing_sex": subj["sex"],
            "new_name": name,
            "new_id": id_,
            "new_sex": sex
        })
        return True  # block addition

    # --- Case 2: ID is new → this subject does not exist ---
    return False

def add_subjects_from_df(subj_map, names, ids, sexes):
    """
    Add subjects from lists of names
    """
    conflicts = []

    # Precompute fast lookup for existing IDs
    id_index = {data["id"]: uid for uid, data in subj_map.items()}

    current_count = len(subj_map)
    added = 0

    for name, id_, sex in zip(names, ids, sexes):

        exists = check_already_exists(
            name=name,
            id_=id_,
            sex=sex,
            id_index=id_index,
            subj_map=subj_map,
            conflicts=conflicts
        )

        if not exists:
            # create new lsXXX id
            new_uid = f"ls{str(current_count + added + 1).zfill(3)}"
            subj_map[new_uid] = {"name": name, "id": id_, "sex": sex}

            # update ID index
            id_index[id_] = new_uid

            added += 1

    print(f"Added {added} new subjects. Encountered {len(conflicts)} conflicts.")

    # Return updated map + conflicts DataFrame
    import pandas as pd
    conflicts_df = pd.DataFrame(conflicts)

    return subj_map, conflicts_df


def load_subj_map(json_file):
    if os.path.exists(json_file):
        try:
            with open(json_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            print(f"Warning: Could not decode {json_file}. Starting fresh.")
    return {}

def save_subj_map(subj_map, json_file):
    with open(json_file, 'w') as f:
        json.dump(subj_map, f, indent=4)

def convert_age_to_years(age):
    """Convert age string (e.g., '0006W', '0012M', '0025Y') to years as float."""
    if pd.isna(age) or not isinstance(age, str) or len(age) < 2:
        return None
    try:
        num = int(age[:-1])
        unit = age[-1].upper()
    except Exception:
        return None
    if unit == 'W':
        return num / 52
    elif unit == 'M':
        return num / 12
    elif unit == 'Y':
        return num
    else:
        return None

def calculate_age_and_critical_info(row : pd.Series) -> pd.Series:
    """Calculate age_in_years, dob, and scan_date based on available data.
    Assuming only one of these three columns is missing at a time,
    this function will calculate the missing value based on the other two.

    Parameters
    ----------
    row : pd.Series
        A row from the DataFrame that should contain 'age_in_years', 'dob', and 'scan_date', but might not have one of them.
        

    Returns
    -------
    row : pd.Series
        The same row with calculated values for 'age_in_years', 'dob', or 'scan_date' if they were missing, 
        and an updated 'estimated_critical_info' column indicating which value was calculated.
        
    """

    # Check if 'age_in_years' is missing
    if pd.isna(row['age_in_years']):
        if pd.notna(row['scan_date']) and pd.notna(row['dob']):
            # Calculate age_in_years from scan_date - dob (based on years)
            scan_date = datetime.strptime(str(row['scan_date']), '%Y%m%d')
            dob = datetime.strptime(str(row['dob']), '%Y%m%d')
            age_in_years = scan_date.year - dob.year
            # Adjust if birthday hasn't occurred yet this year
            if (scan_date.month, scan_date.day) < (dob.month, dob.day):
                age_in_years -= 1
            # Calculate the exact age as a float (including fractional years)
            age_in_years += (scan_date.month - dob.month) / 12.0
            if scan_date.day < dob.day:
                age_in_years -= 1 / 12.0
            row['age_in_years'] = round(age_in_years, 2)  # Round to 2 decimal places
            row['estimated_critical_info'] = "age_in_years"  # Store in 'estimated_critical_info'
    
    # Check if 'dob' is missing
    elif pd.isna(row['dob']):
        if pd.notna(row['age_in_years']) and pd.notna(row['scan_date']):
            # Calculate dob from scan_date - age_in_years
            scan_date = datetime.strptime(str(row['scan_date']), '%Y%m%d')
            dob_year = scan_date.year - int(row['age_in_years'])
            
            # Fix for invalid day of the month (e.g., Feb 30, Apr 31, etc.)
            last_day_of_month = calendar.monthrange(dob_year, scan_date.month)[1]
            dob_day = min(scan_date.day, last_day_of_month)  # Ensure day is valid
            dob = datetime(dob_year, scan_date.month, dob_day)
            row['dob'] = dob.strftime('%Y%m%d')  # Store dob in YYYYMMDD format
            row['estimated_critical_info'] = "dob" # Store dob in 'estimated_critical_info'
    
    # Check if 'scan_date' is missing
    elif pd.isna(row['scan_date']):
        if pd.notna(row['dob']) and pd.notna(row['age_in_years']):
            # Calculate scan_date from dob + age_in_years
            dob = datetime.strptime(str(row['dob']), '%Y%m%d')
            scan_date_year = dob.year + int(row['age_in_years'])
            
            # Fix for invalid day of the month (e.g., Feb 30, Apr 31, etc.)
            last_day_of_month = calendar.monthrange(scan_date_year, dob.month)[1]
            scan_date_day = min(dob.day, last_day_of_month)  # Ensure day is valid
            scan_date = datetime(scan_date_year, dob.month, scan_date_day)
            row['scan_date'] = scan_date.strftime('%Y%m%d')  # Store scan_date in YYYYMMDD format
            row['estimated_critical_info'] = "scan_date"  # Store scan_date in 'estimated_critical_info'
    
    return row

def calculate_age_and_critical_info_vectorized(df: pd.DataFrame) -> pd.DataFrame:
    """
    Vectorized replacement for cf.calculate_age_and_critical_info.
    Calculates missing 'age_in_years', 'dob', or 'scan_date' based on the other two.
    Updates 'estimated_critical_info' column accordingly.
    All original columns are preserved; no new columns are added.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with columns 'age_in_years', 'dob', 'scan_date', 'estimated_critical_info'
    
    Returns
    -------
    df : pd.DataFrame
        DataFrame with calculated values filled in.
    """

    df = df.copy()

    # Ensure estimated_critical_info column exists
    if "estimated_critical_info" not in df.columns:
        df["estimated_critical_info"] = pd.NA

    # Convert dob and scan_date to datetime
    dob_ts = pd.to_datetime(df['dob'].astype(str), format='%Y%m%d', errors='coerce')
    scan_ts = pd.to_datetime(df['scan_date'].astype(str), format='%Y%m%d', errors='coerce')

    # Masks for missing values
    missing_age = df['age_in_years'].isna()
    missing_dob = df['dob'].isna()
    missing_scan = df['scan_date'].isna()

    # --------------------------
    # Calculate missing age_in_years
    # --------------------------
    mask = missing_age & dob_ts.notna() & scan_ts.notna()
    if mask.any():
        age_in_years = (scan_ts[mask] - dob_ts[mask]).dt.days / 365.25
        df.loc[mask, 'age_in_years'] = age_in_years.round(2)
        df.loc[mask, 'estimated_critical_info'] = "age_in_years"

    # --------------------------
    # Calculate missing dob
    # --------------------------
    mask = missing_dob & df['age_in_years'].notna() & scan_ts.notna()
    if mask.any():
        years = df.loc[mask, 'age_in_years'].astype(float)
        dob_est = scan_ts[mask] - pd.to_timedelta((years * 365.25).round(), unit='D')
        df.loc[mask, 'dob'] = dob_est.dt.strftime('%Y%m%d').astype('Int64')
        df.loc[mask, 'estimated_critical_info'] = "dob"

    # --------------------------
    # Calculate missing scan_date
    # --------------------------
    mask = missing_scan & df['age_in_years'].notna() & dob_ts.notna()
    if mask.any():
        years = df.loc[mask, 'age_in_years'].astype(float)
        scan_est = dob_ts[mask] + pd.to_timedelta((years * 365.25).round(), unit='D')
        df.loc[mask, 'scan_date'] = scan_est.dt.strftime('%Y%m%d').astype('Int64')
        df.loc[mask, 'estimated_critical_info'] = "scan_date"

    return df

def calculate_age_dob_scan(row):
    """Calculate missing age_in_years, dob, or scan_date based on available two.
    """

    age_val = row.get('age_in_years')
    dob_val = row.get('dob')
    scan_val = row.get('scan_date')
    
    def parse_date(d):
        try:
            return datetime.strptime(str(d), '%Y%m%d')
        except Exception:
            return None

    age_missing = pd.isna(age_val)
    dob_missing = pd.isna(dob_val)
    scan_missing = pd.isna(scan_val)

    scan_date = parse_date(scan_val)
    dob = parse_date(dob_val)

    estimated_critical_info = None  # Initialize local variable

    # Calculate age_in_years if missing
    if age_missing and scan_date and dob:
        age = scan_date.year - dob.year
        if (scan_date.month, scan_date.day) < (dob.month, dob.day):
            age -= 1
        # add fractional months
        age += (scan_date.month - dob.month) / 12.0
        if scan_date.day < dob.day:
            age -= 1 / 12.0
        row['age_in_years'] = round(age, 2)
        estimated_critical_info = 'age_in_years'

    # Calculate dob if missing
    elif dob_missing and not age_missing and scan_date:
        dob_year = scan_date.year - int(age_val)
        last_day = calendar.monthrange(dob_year, scan_date.month)[1]
        dob_day = min(scan_date.day, last_day)
        dob_date = datetime(dob_year, scan_date.month, dob_day)
        row['dob'] = dob_date.strftime('%Y%m%d')
        estimated_critical_info = 'dob'

    # Calculate scan_date if missing
    elif scan_missing and dob and not age_missing:
        scan_year = dob.year + int(age_val)
        last_day = calendar.monthrange(scan_year, dob.month)[1]
        scan_day = min(dob.day, last_day)
        scan_date_new = datetime(scan_year, dob.month, scan_day)
        row['scan_date'] = scan_date_new.strftime('%Y%m%d')
        estimated_critical_info = 'scan_date'

    # Assign the estimated info column after conditionals
    row['estimated_critical_info'] = estimated_critical_info

    return row


def calculate_mean_date(dates):
    """Calculate mean date from set of 'YYYYMMDD' strings."""
    if not dates:
        return None
    dates = {str(d) for d in dates if d is not None and len(str(d)) == 8}
    if not dates:
        return None
    try:
        dt_objs = [datetime.strptime(d, '%Y%m%d') for d in dates]
    except Exception:
        return None
    timestamps = [dt.timestamp() for dt in dt_objs]
    mean_ts = sum(timestamps) / len(timestamps)
    mean_date = datetime.fromtimestamp(mean_ts)
    return mean_date.strftime('%Y%m%d')

def unify_multiple_dobs(df, unique_id_col='unique_id', dob_col='dob'):
    """For participants with multiple DOBs, replace with the mean dob."""
    dob_group = df.groupby(unique_id_col)[dob_col].apply(set).reset_index()
    multi_dob = dob_group[dob_group[dob_col].apply(lambda x: len(x) > 1)].copy()
    multi_dob['mean_dob'] = multi_dob[dob_col].apply(calculate_mean_date)

    for _, row in multi_dob.iterrows():
        # Ensure mean_dob is an integer or pd.NA
        if row['mean_dob'] is pd.NA or row['mean_dob'] is None:
            mean_dob_int = pd.NA
        else:
            mean_dob_int = int(row['mean_dob'])
        
        df.loc[df[unique_id_col] == row[unique_id_col], dob_col] = mean_dob_int
        
    # Ensure the column dtype stays Int64
    df[dob_col] = df[dob_col].astype('Int64')
    
    return df

