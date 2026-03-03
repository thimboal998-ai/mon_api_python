import pandas as pd
import os
import sys

# Add project root to path
sys.path.append('/Users/thimbo/Desktop/Traitements/mon api')

from modules.data_processor import DataProcessor

# Create dummy data
data = {
    'Unnamed: 0': [0, 1, 2], # Index column to be removed
    'id': [101, 102, 103],   # ID column (might be kept or removed depending on logic)
    'Name': ['Alice', 'Bob', 'Charlie'],
    'Age': [25, 30, 35]
}
df = pd.DataFrame(data)

print("Original Data:")
print(df)

# Initialize Processor
processor = DataProcessor(df)

# Check if index col is removed
print("\nCleaned Data (Internal):")
print(processor.df)

# Export
output_path = 'test_export.csv'
processor.export_to_csv(output_path)

# Read back
print("\nExported CSV Content:")
with open(output_path, 'r') as f:
    print(f.read())

# Check headers
df_exported = pd.read_csv(output_path)
print("\nExported Columns:")
print(list(df_exported.columns))

# Verify 'Unnamed: 0' is gone
if 'Unnamed: 0' not in df_exported.columns:
    print("\n✅ Index column successfully removed.")
else:
    print("\n❌ Index column STIll present.")

# Verify no extra lines
with open(output_path, 'r') as f:
    lines = f.readlines()
    if len(lines) == 4: # Header + 3 rows
        print("✅ Correct number of lines (Header + Data only).")
    else:
        print(f"❌ Incorrect line count: {len(lines)}")
