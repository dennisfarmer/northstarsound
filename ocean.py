import os
import glob
import numpy as np

# Path to the directory to search
base_dir = "/Volumes/datascience/data/audio"

# Iterate through each folder in the base directory
for root, dirs, files in os.walk(base_dir):
    # Check for *.part and *.ytdl files
    part_files = glob.glob(os.path.join(root, "*.part"))
    ytdl_files = glob.glob(os.path.join(root, "*.ytdl"))
    
    # Print the names of the files if they exist
    for file in part_files + ytdl_files:
        print(file)

# todo: go back and redownload the files that were not downloaded properly
#/Volumes/datascience/data/audio/026/FN44GMRoBYM.mp4.part
#/Volumes/datascience/data/audio/026/FN44GMRoBYM.mp4.part-Frag1119.part
#/Volumes/datascience/data/audio/026/FN44GMRoBYM.mp4.ytdl
#https://open.spotify.com/track/5rDFPNodZAQoTYWqyjjn7E
# this one isn't even playable on spotify, so it's not worth redownloading
# todo: blacklist specific tracks that are too long or not playable
# so that we don't waste time running them through the audio feature extractor

# todo: shorten the length of id columns in the database

import matplotlib.pyplot as plt

# Collect file sizes
file_sizes = []

for root, dirs, files in os.walk(base_dir):
    for file in files:
        file_path = os.path.join(root, file)
        if os.path.isfile(file_path):
            file_sizes.append(os.path.getsize(file_path))

# Convert file sizes to MB
file_sizes_mb = [size / (1024 ** 2) for size in file_sizes]

# Calculate and print the total size of all files in gigabytes
total_size_gb = sum(file_sizes) / (1024 ** 3)
print(f"Total size of all files: {total_size_gb:.2f} GB")

# Plot the distribution of file sizes in MB
plt.figure(figsize=(10, 6))
plt.hist(file_sizes_mb, bins=50, color='blue', edgecolor='black')
plt.title('Distribution of File Sizes')
plt.xlabel('File Size (MB)')
plt.ylabel('Frequency')
plt.grid(axis='y', linestyle='--', alpha=0.7)

# Calculate the mean in MB
median_size_mb = np.median(file_sizes_mb)
print(f"Median file size: {median_size_mb:.2f} MB")

# Plot a vertical line for the median
plt.axvline(median_size_mb, color='red', linestyle='--', linewidth=1.5, label=f'Mean: {median_size_mb:.1f} MB')

# Overlay text with the median value
plt.text(median_size_mb, plt.gca().get_ylim()[1] * 0.9, f'{median_size_mb:.1f}', color='red', fontsize=10, ha='center')

plt.legend()
plt.show()
