import os
import re
import csv
from tkinter import Tk, Label, PhotoImage, Button
from PIL import Image, ImageTk

# --- Configuration ---
# Set the root directory containing your CAT12 derivative JPG files.
# The script will search this directory and all subdirectories recursively.
ROOT_DIR = "/path/to/cat12/derivatives"  # **CHANGE THIS PATH**, last segment should be "derivatives".

# The name of the output CSV file where results will be saved.
OUTPUT_CSV = "/home/gaia/Projects/legacy_data/legacy_pipe/data/interim/SourceName_scan_classification_results.csv" # **CHANGE THIS PATH**

# Allowed classification keys (1 to 9). You can expand this as needed.
# 1 = Good, 
# 2 = pixeled (cubes in the scan), 
# 3 = striped (slices too big), 
# 4 = black jpg, 
# 5 = not usable scan (partial brain)
ALLOWED_KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9']

# Regex pattern to extract Subject ID and Session ID from the BIDS-like path.
# This assumes a structure like: /.../sub-01/ses-M00/sub-01_ses-M00_cat12_image.jpg
BIDS_PATTERN = re.compile(r'(sub-[a-zA-Z0-9]+)/(ses-[a-zA-Z0-9]+)/')

# --- Global State ---
jpg_files = []
current_index = 0
result_data = []

# --- Helper Functions ---

def find_jpg_files(root_path):
    """Recursively finds all JPG files in the root directory."""
    print(f"Searching for JPG files in: {root_path}...")
    files = []
    for dirpath, _, filenames in os.walk(root_path):
        for f in filenames:
            if f.endswith('.jpg') or f.endswith('.jpeg'):
                files.append(os.path.join(dirpath, f))
    print(f"Found {len(files)} image files.")
    return sorted(files)

def extract_bids_info(file_path):
    """Extracts Subject and Session IDs from the file path using BIDS pattern."""
    match = BIDS_PATTERN.search(file_path)
    if match:
        # Group 1 is 'sub-XXX', Group 2 is 'ses-YYY'
        subject_id = match.group(1)
        session_id = match.group(2)
        return subject_id, session_id
    # Fallback if the pattern doesn't match the required part of the path
    print(f"Warning: Could not extract BIDS info from path: {file_path}")
    return "UNKNOWN_SUB", "UNKNOWN_SES"

def save_results():
    """Saves all collected classification results to the CSV file."""
    print(f"\nSaving {len(result_data)} results to {OUTPUT_CSV}...")
    with open(OUTPUT_CSV, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['subject_id', 'session_id', 'classification_label', 'file_path'])
        writer.writerows(result_data)
    print("Save complete.")

# --- GUI and Logic ---

def next_image(label_value):
    """
    Records the classification and advances to the next image.
    Called when a valid classification key is pressed.
    """
    global current_index

    if not label_value:
        print("Please press a valid classification key (1-9).")
        return

    # 1. Record the result
    current_file = jpg_files[current_index]
    sub_id, ses_id = extract_bids_info(current_file)
    
    result_data.append([sub_id, ses_id, label_value, current_file])
    print(f"Recorded: Sub={sub_id}, Ses={ses_id}, Label={label_value}. Total recorded: {len(result_data)}")

    # 2. Advance to the next image
    current_index += 1
    
    # 3. Check if all files are processed
    if current_index >= len(jpg_files):
        save_results()
        status_label.config(text=f"*** FINISHED! All {len(jpg_files)} files processed. Results saved to {OUTPUT_CSV} ***", fg="green")
        root.unbind('<Key>') # Stop listening for keypresses
        return

    # 4. Update the display for the next image
    display_image(jpg_files[current_index])
    
    # Reset focus or clear previous keypress if necessary, though keypress
    # binding handles the input directly.

def key_press(event):
    """
    Handles keypresses for classification. 
    It mimics the 'press a number then press ENTER' logic by using the number keypress itself.
    """
    key = event.keysym
    if key in ALLOWED_KEYS:
        # Instead of waiting for Enter, we classify immediately upon a number press.
        next_image(key)
    # The 'Enter' requirement is simplified here: a number keypress *is* the classification.
    # If you *must* have the number-then-enter sequence, the logic would be more complex
    # (e.g., storing the number in a global variable and checking for 'Return'/'Enter' key).
    
    # For simplicity and speed, we use the number keypress as the final action.

def display_image(file_path):
    """Loads and displays the image in the Tkinter window."""
    global tk_image

    # Update status label with the current file being viewed
    status_label.config(text=f"Viewing {current_index + 1}/{len(jpg_files)}: {os.path.basename(file_path)}")
    
    # Load the image using PIL
    try:
        pil_image = Image.open(file_path)
        # Resize to fit on screen if needed (adjust as per your screen/image size)
        # For example, to max 1000px height while maintaining aspect ratio:
        if pil_image.height > 1000:
             ratio = 1000 / pil_image.height
             new_width = int(pil_image.width * ratio)
             pil_image = pil_image.resize((new_width, 1000), Image.Resampling.LANCZOS)
             
        # Convert PIL Image to Tkinter PhotoImage
        tk_image = ImageTk.PhotoImage(pil_image)
        
        # Update the image label
        image_label.config(image=tk_image)
        image_label.image = tk_image # Keep a reference!
        
        # Update window title to show current path for context
        root.title(f"Scan Classifier - {file_path}")
        
    except Exception as e:
        # In case of a corrupt or unreadable file
        print(f"Error loading image {file_path}: {e}")
        next_image("ERROR") # Classify as error and move on

def main():
    """Main function to initialize the script and GUI."""
    global root, image_label, status_label, jpg_files, current_index

    # 1. Find all JPG files
    jpg_files = find_jpg_files(ROOT_DIR)
    if not jpg_files:
        print("No JPG files found. Check your ROOT_DIR path and file extensions.")
        return

    # If the script crashed previously, you can load the results and resume:
    # (Advanced feature, not implemented here for simplicity, but you can check
    # if OUTPUT_CSV exists and remove already classified files from jpg_files).

    # 2. Setup the GUI
    root = Tk()
    root.title("Scan Classifier")
    
    # Label to show the image
    image_label = Label(root)
    image_label.pack(padx=10, pady=10)

    # Label to show status and instructions
    status_label = Label(root, 
                         text=f"Instructions: Press a number key (1-{ALLOWED_KEYS[-1]}) to classify and advance.",
                         font=('Arial', 12), fg="blue")
    status_label.pack(pady=5)
    
    # Bind keypress events to the handler function
    # '<Key>' captures all keypresses
    root.bind('<Key>', key_press)
    
    # 3. Start the process
    display_image(jpg_files[current_index])
    
    # 4. Start the Tkinter event loop
    root.mainloop()

if __name__ == "__main__":
    main()