import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
import calendar
from dateutil.parser import parse
import matplotlib.patches as mpatches
import json
import os
from dateutil import parser




def calculate_critical_info(row: pd.Series, age_col: str, dob_col: str, scan_date_col: str) -> pd.Series:
    """
    Calculates missing 'age_in_years', 'dob', or 'scan_date' for a given row.
    
    This function modifies the row in-place.
    """
    age = row[age_col]
    dob = row[dob_col]
    scan_date = row[scan_date_col]
    estimated_info = "None"

    # Use a flag to track if we've already estimated a value for this row
    already_estimated = False
    
    # Check for missing age
    if pd.isna(age):
        if pd.notna(dob) and pd.notna(scan_date):
            # The 'dob' and 'scan_date' columns should be in YYYYMMDD string format
            dob_dt = datetime.strptime(str(dob), '%Y%m%d')
            scan_date_dt = datetime.strptime(str(scan_date), '%Y%m%d')
            
            age = (scan_date_dt - dob_dt).days / 365.25
            age = round(age, 2)
            estimated_info = age_col
            already_estimated = True

    # Check for missing DOB
    if not already_estimated and pd.isna(dob):
        if pd.notna(age) and pd.notna(scan_date):
            scan_date_dt = datetime.strptime(str(scan_date), '%Y%m%d')
            dob_year = scan_date_dt.year - int(age)
            dob_dt = datetime(dob_year, scan_date_dt.month, scan_date_dt.day)
            
            dob = int(dob_dt.strftime('%Y%m%d'))
            estimated_info = dob_col
            already_estimated = True
    
    # Check for missing scan date
    if not already_estimated and pd.notna(dob) and pd.notna(age) and pd.isna(scan_date):
        dob_dt = datetime.strptime(str(dob), '%Y%m%d')
        scan_date_year = dob_dt.year + int(age)
        scan_date_dt = datetime(scan_date_year, dob_dt.month, dob_dt.day)
        
        scan_date = int(scan_date_dt.strftime('%Y%m%d'))
        estimated_info = scan_date_col

    # Update the row in-place
    row[age_col] = age
    row[dob_col] = dob
    row[scan_date_col] = scan_date
    row['estimated_critical_info'] = estimated_info
    
    # Return the entire modified row
    return row


### From "Dashboard.ipynb" ###
def find_and_remove_duplicates(df : pd.DataFrame  , column : str) -> pd.DataFrame : 
    """ find and remove duplicates from a df according to a specific given column 
    
    input: 
    ------
    df - the df I want to edit
    column - the column the duplications are calculated according to 

    output: 
    -------
    df - the edited df (w/o duplications according to column)

    """
    # Count how many times each value appears
    counts = df[column].value_counts()

    # Filter for duplicates
    duplicates = counts[counts > 1]

    # Check if there are any duplicates
    if not duplicates.empty:
        print(f"Found duplicates - {list(duplicates.index)}")
    else:
        print("No duplicates")

    # Remove duplicate rows (keep first occurrence)
    df = df.drop_duplicates(subset=column, keep='first')


    return df


def time_span_histogram(column : pd.DataFrame , x_label : str, tick_jump : int = 10) : 
    """ creates a histogram from a specific column 

    input : 
    -------
    column - df, a column with numeric values from data frame
    x_label - str, the label of x axis 
    tick_jump - int, the jump in range, 10 by default
    
    
    """

    x = np.asarray(column).astype(int)
    counts, bins = np.histogram(x)
    plt.stairs(counts, bins, fill=True, color='#FFC0CB', edgecolor='blue')
    # Make the years visible on the x-axis
    plt.xticks(np.arange(x.min(), x.max() , tick_jump), rotation=90)  # Rotate labels and set ticks in jumps of 5

    # Add axis labels
    plt.xlabel(x_label)
    plt.ylabel('Amount of Legacy Participants')

    print(f'max value is {x.max()} and min value is {x.min()}')


def check_type(df , column) : 
    """print the types of values in a specific column from a df

    Parameters
    ----------
    df : dataframe
        
    column : a single column from the df
        
    """
    type_counts = df[column].map(type).value_counts()
    print(type_counts)



# Helper function to extract year and ensure int age when merging all participants ever
def preprocess(df, id_col, dob_col, sex_col, age_col):
    out = pd.DataFrame()
    out['subject_id'] = df[id_col]

    # Extract the year from DOB (safe even if DOB is missing or messy)
    out['year_of_birth'] = df[dob_col].astype(str).str.extract(r'(\d{4})')

    out['sex'] = df[sex_col]

    # Coerce non-numeric age values to NaN and drop anything truly invalid
    def safe_numeric(val):
        try:
            return int(float(val))
        except (ValueError, TypeError):
            return pd.NA

    out['age_at_scan'] = df[age_col].apply(safe_numeric).astype('Int64')

    return out

def extract_birth_year_from_dob(dob):
    """
    Extracts the birth year from a date of birth string, handling multiple formats.
    
    Parameters
    ----------
    dob : str or int
        Date of birth in various possible formats (e.g., 'YYYY-MM-DD', 'MM/DD/YYYY',
        'YYYYMMDD', etc.).
        
    Returns
    -------
    int or None
        The birth year as an integer, or None if extraction fails.
    """
    # First, convert dob to string if it's not already
    dob_str = str(dob)
    try:
        # Use dateutil.parser to parse the date string regardless of format.
        parsed_date = parser.parse(dob_str)
        
        # Now, format the parsed date as 'YYYYMMDD'
        formatted_date_str = parsed_date.strftime('%Y%m%d')
        
        # Extract the year from the formatted string and return as an integer.
        return int(formatted_date_str[:4])
    except (ValueError, TypeError, parser.ParserError):
        # Return None if parsing or conversion fails.
        return None

def sex_pie_chart(df, sex_col_name):
    """Creates a pie chart showing the distribution of sex in the DataFrame.
    """
    # Count the occurrences of each sex
    sex_counts = df[sex_col_name].value_counts()
    # 3. Create the pie chart
    plt.figure(figsize=(8, 8))
    plt.pie(
        sex_counts,
        labels=sex_counts.index,
        autopct='%1.1f%%',
        startangle=90,
        colors=sns.color_palette("pastel")
    )

    # 4. Add a title
    plt.title("Distribution of Participant Sex", fontsize=16)

    # 5. Ensure the circle is a circle
    plt.axis('equal')

    # Display the chart
    plt.show()

def age_vs_birthyear_scatterplot(df, dob_col, age_at_scan_col):
    
    # Convert DOB to datetime and extract the year
    df['birth_year'] = pd.to_datetime(df[dob_col], format='%Y%m%d').dt.year
    
    # make sure age_at_scan is integer
    df[age_at_scan_col] = pd.to_numeric(df[age_at_scan_col], errors='coerce')
    df[age_at_scan_col] = np.round(df[age_at_scan_col])

    # Count how many times each (birth_year, age_at_scan) pair appears
    df_counts = df.groupby(['birth_year', age_at_scan_col]).size().reset_index(name='count')


    plt.figure(figsize=(10, 6))
    scatter = sns.scatterplot(
        data=df_counts,
        x='birth_year',
        y=age_at_scan_col,
        hue='count',
        palette='crest',
        sizes=(20, 300),
        legend='brief'
)

    plt.title("Participant Age at Scan and Birth Year")
    plt.xlabel("Birth Year")
    plt.ylabel("Age at Scan")

    # Set x-ticks every 10 years
    ax = plt.gca()
    min_year = df_counts['birth_year'].astype(int).min()
    max_year = df_counts['birth_year'].astype(int).max()
    ax.set_xticks(np.arange(min_year, max_year + 1, 10))

    # Y-ticks: every 5 years
    min_age = int(np.floor(df_counts[age_at_scan_col].min() / 5) * 5)
    max_age = int(np.ceil(df_counts[age_at_scan_col].max() / 5) * 5)
    plt.yticks(np.arange(min_age, max_age + 1, 5))

    plt.tight_layout()
    plt.show()

def age_vs_birthyear_scatterplot_many_dfs(datasets):
    """
    Plots age vs. birth year for multiple datasets on a single figure.

    Parameters
    ----------
    datasets : list of tuples
        Each tuple should contain (DataFrame, dob_column_name, age_at_scan_column_name, style_label).
    """

    # Create the figure and axes once
    plt.figure(figsize=(10, 6))
    ax = plt.gca()

    # Define a list of markers and palettes to cycle through for each dataset
    markers = ['o', 'X', '*', 'P', 'd']
    palettes = ['crest', 'flare', 'magma', 'Reds_r', 'Greys_r']

    # Keep track of all data to set plot limits
    all_birth_years = []
    all_ages = []

    # Loop through each dataset
    for i, dataset in enumerate(datasets):
        df, dob_col, age_at_scan_col, style_label = dataset
        
        # Data preprocessing steps
        # Use a more explicit format for date conversion
        df['birth_year'] = pd.to_datetime(df[dob_col], format='%Y%m%d', errors='coerce').dt.year
        
        df[age_at_scan_col] = pd.to_numeric(df[age_at_scan_col], errors='coerce')
        df[age_at_scan_col] = np.round(df[age_at_scan_col])

        # Count how many times each (birth_year, age_at_scan) pair appears
        df_counts = df.groupby(['birth_year', age_at_scan_col]).size().reset_index(name='count')
        
        # Store all years and ages for setting plot limits later
        all_birth_years.extend(df_counts['birth_year'].tolist())
        all_ages.extend(df_counts[age_at_scan_col].tolist())

        # Plot on the same axes with a unique marker and palette
        sns.scatterplot(
            data=df_counts,
            x='birth_year',
            y=age_at_scan_col,
            hue='count',
            palette=palettes[i % len(palettes)],
            sizes=(20, 300),
            legend='brief',
            ax=ax,
            marker=markers[i % len(markers)]
        )
        
        # Add a custom legend entry for this dataset
        # This prevents the TypeError and still gives a clear label
        plt.plot([], [], 'o', marker=markers[i % len(markers)], label=style_label, color='k')

    # Set common plot properties using data from all datasets
    plt.title("Participant Age at Scan and Birth Year")
    plt.xlabel("Birth Year")
    plt.ylabel("Age at Scan")
    
    # Set x-ticks every 10 years
    if all_birth_years:
        min_year = int(min(all_birth_years))
        max_year = int(max(all_birth_years))
        ax.set_xticks(np.arange(min_year, max_year + 1, 10))
    
    # Y-ticks: every 5 years
    if all_ages:
        min_age = int(np.floor(min(all_ages) / 5) * 5)
        max_age = int(np.ceil(max(all_ages) / 5) * 5)
        plt.yticks(np.arange(min_age, max_age + 1, 5))

    # Add a legend to distinguish the datasets
    plt.legend()
    plt.tight_layout()
    plt.show()




# Function to convert the age in weeks, months, or years to years
def convert_to_years(age):
    """convert age in a specific format to a numeric value of years 
    Format to convert - 000X, X = Y(years) or M(months) or W(weeks) 
    converts to int 

    
    Parameters
    ----------
    age : str
        age in the following format:
         000X, X = Y(years) or M(months) or W(weeks) 

    Returns
    -------
    num : int 
        age in years as an int
    """
    # Check if the input is a string
    if isinstance(age, str):
        # Extract the numeric part and the unit (W, M, Y)
        # Using a try-except block to handle cases where the string might be malformed
        try:
            num = int(age[:-1])  # All characters except the last one are the number
            unit = age[-1].upper() # The last character is the unit (converted to upper case for consistency)
        except (ValueError, IndexError):
            return None # Return None for malformed strings
        
        # Convert based on the unit
        if unit == 'W':  # Weeks to years (1 week = 1/52 years)
            return num / 52
        elif unit == 'M':  # Months to years (1 month = 1/12 years)
            return num / 12
        elif unit == 'Y':  # Years (no conversion needed)
            return num
        else:
            return None  # Return None if the unit is not recognized
    elif isinstance(age, (int, float)):
        # If the input is already a number, return it as is
        return age
    else:
        # For any other data type, return None
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


def parse_and_format_date(date_str):
    """
    Parses a date string in various formats and returns a
    string in 'YYYYMMDD' format.

    Parameters
    ----------
    date_str : str
        The date string to parse. Can be in multiple formats
        (e.g., 'MM/DD/YY', 'YYYY-MM-DD', 'DD.MM.YYYY').

    Returns
    -------
    formatted_date_str : str or None
        The formatted date string 'YYYYMMDD' or None if
        parsing fails.
    """
    if pd.isna(date_str):
        return None
        
    try:
        # dateutil.parser.parse is flexible and can handle
        # most of the formats automatically
        parsed_date = parse(str(date_str), dayfirst=False)
        return parsed_date.strftime('%Y%m%d')
    except (ValueError, TypeError):
        # Return None or a specific value if the date string
        # cannot be parsed
        return None
    
def create_combined_histogram_simple(dataframes: list, column_names: list, title):
    """
    Combines data from multiple DataFrames with different column names
    and creates a single histogram.
    """
    all_data = []

    # 1. Loop through each DataFrame and its column name
    for df, col_name in zip(dataframes, column_names):
        # 2. Extract the data and add it to a single list
        if col_name in df.columns:
            all_data.extend(df[col_name].tolist())
    
    # 3. Create a pandas Series from the combined list
    combined_series = pd.Series(all_data)
    # remove NaN values
    combined_series = combined_series.dropna()
    
    # 4. Create the histogram directly from the Series
    plt.figure(figsize=(10, 6))
    
    sns.histplot(
        combined_series,
        binwidth=1,
        kde=True,
        color='hotpink'
    )
    
    plt.title(title, fontsize=16)
    plt.xlabel('Age at Scan (Years)', fontsize=12)
    # show all xticks 
    plt.xticks(range(int(combined_series.min()), int(combined_series.max()) + 1, 5))
    plt.ylabel('Amount of Subjects', fontsize=12)
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    
    plt.show()
    return combined_series


def stacked_chart_multiple_df(datasets, age_col, birth_year_col, title):
    """
    Combines data from multiple DataFrames with specified column names
    and creates a single stacked bar chart.

    Args:
        datasets (list of pd.DataFrame): A list of DataFrames to combine.
        age_col (str): The name of the age-at-scan column in all DataFrames.
        birth_year_col (str): The name of the birth-year column in all DataFrames.
        title (str): The title for the plot.
    """
    
    # 1. Combine all DataFrames into a single one
    combined_df = pd.concat(datasets, ignore_index=True)

    # 2. Clean and prepare the data
    # Drop rows with missing values in the relevant columns
    combined_df = combined_df.dropna(subset=[age_col, birth_year_col])
    
    # Ensure columns are of integer type to fix plotting errors
    combined_df[age_col] = combined_df[age_col].astype(int)
    combined_df[birth_year_col] = combined_df[birth_year_col].astype(int)

    # 3. Create the stacked bar chart
    fig, ax = plt.subplots(figsize=(30, 20))
    sns.histplot(
        data=combined_df,
        x=age_col,
        hue=birth_year_col,
        multiple='stack',
        palette='nipy_spectral',
        binwidth=1,
        discrete=True,
        shrink=1.0,
        ax=ax,
        legend=False
    )

    # 4. Manually create the legend
    birth_years = sorted(combined_df[birth_year_col].unique())
    colors = sns.color_palette('nipy_spectral', n_colors=len(birth_years))
    legend_patches = [mpatches.Patch(color=colors[i], label=str(birth_years[i])) for i in range(len(birth_years))]
    ax.legend(handles=legend_patches, title='Birth Year', loc='upper left', bbox_to_anchor=(1, 1))

    # 5. Set titles and labels
    ax.set_title(title, fontsize=20, pad=20)
    ax.set_xlabel('Age at Scan', fontsize=16)
    ax.set_ylabel('Number of Subjects', fontsize=16)
    ax.set_xticks(sorted(combined_df[age_col].unique()))
    ax.tick_params(axis='x', labelsize=16)
    ax.tick_params(axis='y', labelsize=16)

    plt.tight_layout()
    plt.show()


def load_subj_map_json(): 
    """ Load the subject mapping json file """
    # load the subject mapping
    json_file_path = "/home/gaia/Projects/legacy_data/my_master/subj_map.json"

    # Check if the file exists and is not empty/corrupted
    if os.path.exists(json_file_path):
        try:
            with open(json_file_path, 'r') as json_file:
                subj_map = json.load(json_file)
                print(f"type of subj_map 2: {type(subj_map)}")
            print(f"Successfully loaded existing subj_map from {json_file_path}:")
            print(json.dumps(subj_map, indent=4)) # Pretty print the loaded dictionary
        except json.JSONDecodeError:
            print(f"Error: Could not decode JSON from {json_file_path}. File might be empty or corrupted. Starting with an empty map.")
    else:
        print(f"Warning: {json_file_path} not found. Starting with an empty subj_map.")
        # If the file doesn't exist, it will be created on save.
    return subj_map