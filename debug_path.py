from config import Config
import os
import sys

# Init config to get paths
Config.init_folders()

print(f"PROCESSED_FOLDER: {Config.PROCESSED_FOLDER}")

# List files in processed folder
print("\nFiles in processed folder:")
files = os.listdir(Config.PROCESSED_FOLDER)
for f in files:
    print(f" - {f}")

# Simulating the download_file logic
filename = "cleaned_Advertising_20260217_180023.csv" # One of the files I saw
filepath = os.path.join(Config.PROCESSED_FOLDER, filename)

print(f"\nTesting path: {filepath}")
if os.path.exists(filepath):
    print("✅ File EXISTS at this path")
else:
    print("❌ File NOT FOUND at this path")

# Check if maybe there is a double slash or something
print(f"Absolute path: {os.path.abspath(filepath)}")
