import os
import shutil
from PIL import Image
import numpy as np

# Define paths
source_dir = 'data/hugging_data/normal'
target_dir = 'data/hugging_data/normal_clean'

# Create target directory if it doesn't exist
os.makedirs(target_dir, exist_ok=True)

# Function to check if a normal map is plain (no features)
def is_plain_normal_map(file_path):
    # First quick check: file size
    file_size_kb = os.path.getsize(file_path) / 1024
    if file_size_kb < 10:  # Files under 10KB are likely plain
        return True
    
    # Secondary check: analyze pixel variance
    try:
        img = Image.open(file_path)
        img_array = np.array(img)
        
        # Check standard deviation of pixel values
        # Plain normal maps will have very low standard deviation
        std_dev = np.std(img_array)
        
        return std_dev < 5  # Threshold may need adjustment
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

# Process files
count_total = 0
count_kept = 0

for filename in os.listdir(source_dir):
    if filename.endswith('.png'):
        count_total += 1
        source_path = os.path.join(source_dir, filename)
        target_path = os.path.join(target_dir, filename)
        
        if not is_plain_normal_map(source_path):
            shutil.copy2(source_path, target_path)
            count_kept += 1
            print(f"Copied: {filename}")
        else:
            print(f"Skipped plain normal map: {filename}")

print(f"\nProcessing complete!")
print(f"Total normal maps: {count_total}")
print(f"Non-plain normal maps kept: {count_kept}")
print(f"Plain normal maps excluded: {count_total - count_kept}") 