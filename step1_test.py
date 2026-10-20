
from pathlib import Path
import pandas as pd

# Find the data folder relative to this script
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

kaggle_file = DATA_DIR / "train_input.csv"
study_file = DATA_DIR / "study_records.csv"

# Check whether both files exist
print("Kaggle dataset exists:", kaggle_file.exists())
print("Study records file exists:", study_file.exists())

# Load and inspect the Kaggle dataset
if kaggle_file.exists():
    kaggle_df = pd.read_csv(kaggle_file)
    print("\nKaggle dataset shape:", kaggle_df.shape)
    print("\nKaggle columns:")
    print(kaggle_df.columns.tolist())
    print("\nFirst five rows:")
    print(kaggle_df.head())
else:
    print("\nPlease put train_input.csv inside the data folder.")

# Load and inspect our own records
if study_file.exists():
    study_df = pd.read_csv(study_file)
    print("\nStudy records shape:", study_df.shape)
    print("\nStudy records:")
    print(study_df)
else:
    print("\nPlease create study_records.csv inside the data folder.")
