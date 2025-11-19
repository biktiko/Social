"""
Debug script to check R21 data
"""
import pandas as pd
import sys

# Set UTF-8 for console output
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Load data
df = pd.read_excel("Media_Research.xlsx")

# Standardize column names
df.columns = [c.strip() for c in df.columns]

print("=" * 80)
print("R2 - TV Subscription")
print("=" * 80)
print(f"Column exists: {'R2' in df.columns}")
if 'R2' in df.columns:
    print("Unique values:")
    print(df['R2'].value_counts().to_dict())
    print()

print("=" * 80)
print("R21 - Cable Provider")
print("=" * 80)
print(f"Column exists: {'R21' in df.columns}")
if 'R21' in df.columns:
    print("All values:")
    print(df['R21'].value_counts().to_dict())
    print()
    
    # Filter for cable users only
    df_cable = df[df['R2'] == 1]
    print(f"\nFor cable users only (R2==1): {len(df_cable)} users")
    print(df_cable['R21'].value_counts().to_dict())
