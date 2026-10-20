
from pathlib import Path
import tempfile
import shutil

from classes.study_record_manager import StudyRecordManager

project_dir = Path(__file__).resolve().parent
original_csv = project_dir / "data" / "study_records.csv"

with tempfile.TemporaryDirectory() as temp_dir:
    test_csv = Path(temp_dir) / "study_records.csv"
    shutil.copy2(original_csv, test_csv)

    manager = StudyRecordManager(test_csv)

    valid_record = {
        "Record_ID": "TEST008",
        "Student_ID": "S002",
        "Subject": "Chemistry",
        "Previous_Marks": 60,
        "Target_Marks": 80,
        "Difficulty": 3,
        "Study_Hours": 2,
        "Exam_Days_Left": 7,
        "Target_Grade": "A",
    }

    # Test 1: valid record
    print("\nTEST 1: Valid record")
    try:
        manager.add_record(valid_record)
        print("PASS: Valid record added.")
    except ValueError as error:
        print("FAIL:", error)

    # Test 2: duplicate ID
    print("\nTEST 2: Duplicate ID")
    try:
        manager.add_record(valid_record)
        print("FAIL: Duplicate was accepted.")
    except ValueError as error:
        print("PASS: Duplicate rejected:", error)

    # Test 3: marks above 100
    print("\nTEST 3: Invalid marks")
    bad_marks = valid_record.copy()
    bad_marks["Record_ID"] = "TEST009"
    bad_marks["Previous_Marks"] = 150

    try:
        manager.add_record(bad_marks)
        print("FAIL: Invalid marks were accepted.")
    except ValueError as error:
        print("PASS: Invalid marks rejected:", error)

    # Test 4: negative study hours
    print("\nTEST 4: Negative study hours")
    bad_hours = valid_record.copy()
    bad_hours["Record_ID"] = "TEST010"
    bad_hours["Study_Hours"] = -2

    try:
        manager.add_record(bad_hours)
        print("FAIL: Negative hours were accepted.")
    except ValueError as error:
        print("PASS: Negative hours rejected:", error)

    # Test 5: empty subject
    print("\nTEST 5: Empty subject")
    bad_subject = valid_record.copy()
    bad_subject["Record_ID"] = "TEST011"
    bad_subject["Subject"] = ""

    try:
        manager.add_record(bad_subject)
        print("FAIL: Empty subject was accepted.")
    except ValueError as error:
        print("PASS: Empty subject rejected:", error)

    # Test 6: unknown record
    print("\nTEST 6: Unknown record")
    try:
        manager.delete_record("DOES_NOT_EXIST")
        print("FAIL: Unknown record was deleted.")
    except ValueError as error:
        print("PASS: Unknown record rejected:", error)

    print("\nValidation tests completed.")
