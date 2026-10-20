
from pathlib import Path
import tempfile
import shutil

from classes.study_record_manager import StudyRecordManager


# Locate the existing CSV
project_dir = Path(__file__).resolve().parent
original_csv = project_dir / "data" / "study_records.csv"

# Make a temporary copy so tests cannot damage your real records
with tempfile.TemporaryDirectory() as temp_dir:
    test_csv = Path(temp_dir) / "study_records.csv"
    shutil.copy2(original_csv, test_csv)

    manager = StudyRecordManager(test_csv)

    # 1. Read records
    print("\n--- EXISTING RECORDS ---")
    print(manager.get_records())

    # 2. Calculate statistics
    print("\n--- DASHBOARD STATISTICS ---")
    print(manager.calculate_statistics())

    # 3. Calculate one subject's priority
    first_record = manager.get_records().iloc[0].to_dict()
    print("\n--- PRIORITY SCORE ---")
    print(manager.calculate_priority(first_record))

    # 4. Allocate 5 study hours
    print("\n--- STUDY TIME ALLOCATION ---")
    allocation = manager.allocate_study_time(5)
    print(allocation)
    print(
        "Total allocated hours:",
        allocation["Recommended_Hours"].sum()
    )

    # 5. Create a test record
    print("\n--- CREATE RECORD ---")
    new_record = {
        "Record_ID": "TEST001",
        "Student_ID": "S002",
        "Subject": "Chemistry",
        "Previous_Marks": 60,
        "Target_Marks": 80,
        "Difficulty": 4,
        "Study_Hours": 1,
        "Exam_Days_Left": 7,
        "Target_Grade": "A",
    }
    manager.add_record(new_record)
    print("Records after adding:", len(manager.get_records()))

    # 6. Update the test record
    print("\n--- UPDATE RECORD ---")
    manager.update_record(
        "TEST001", {"Previous_Marks": 70}
    )
    print(
        manager.get_records()
        .query("Record_ID == 'TEST001'")[["Subject", "Previous_Marks"]]
    )

    # 7. Delete the test record
    print("\n--- DELETE RECORD ---")
    manager.delete_record("TEST001")
    print("Records after deleting:", len(manager.get_records()))

    print("\nAll tests completed.")
