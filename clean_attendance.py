"""
clean_attendance.py
-------------------
Builds the cleaned working CSV from the raw CSV.

  data/sample_dataset.csv      (RAW - this script only READS it, never changes it)
        |
        v
  data/attendance_cleaned.csv  (working copy used by the app)
  data/rejected_rows.csv       (rows that failed validation, with the reason - nothing is silently lost)
  data/cleaning_report.txt     (what was checked and found)

Run:  python clean_attendance.py
"""
import re
from pathlib import Path

import pandas as pd

from attendance_manager import (AttendanceDataError, CLEAN_CSV, COLUMNS, DATE_FORMAT, KEY_COLUMNS,
                                RAW_CSV, STUDENT_ID_PATTERN, normalize_time)

REQUIRED_RAW = [c for c in COLUMNS if c != "record_id"]   # student_name is optional (we drop it)


def _safe_time(value):
    """Return (normalized_time_or_None, is_valid). Empty is valid (e.g. absent students)."""
    try:
        return normalize_time(value), True
    except ValueError:
        return None, False


def clean(raw_path=RAW_CSV, cleaned_path=CLEAN_CSV):
    raw_path, cleaned_path = Path(raw_path), Path(cleaned_path)
    if cleaned_path.resolve() == raw_path.resolve():
        raise AttendanceDataError("The cleaned file must be different from the raw file.")
    if not raw_path.exists():
        raise AttendanceDataError(f"Raw CSV not found: {raw_path}")
    try:
        raw = pd.read_csv(raw_path, dtype=str)       # read only - raw file is never written
    except pd.errors.EmptyDataError:
        raise AttendanceDataError("The raw CSV is empty.")
    missing = [c for c in REQUIRED_RAW if c not in raw.columns]
    if missing:
        raise AttendanceDataError(f"Raw CSV is missing required column(s): {', '.join(missing)}")

    df = raw.copy()
    for col in df.columns:                            # remove stray spaces
        df[col] = df[col].str.strip()
    df["student_id"] = df["student_id"].str.upper()

    # ---- Validate every row; collect the reasons instead of deleting silently ----
    reasons = pd.Series([""] * len(df), index=df.index, dtype=object)

    def flag(mask, text):
        reasons.loc[mask] = reasons.loc[mask] + text + "; "

    flag(df["student_id"].isna() | ~df["student_id"].fillna("").str.match(STUDENT_ID_PATTERN), "invalid student_id")
    parsed_date = pd.to_datetime(df["date"], format=DATE_FORMAT, errors="coerce")
    flag(parsed_date.isna(), "invalid date")
    semester = pd.to_numeric(df["semester"], errors="coerce")
    flag(semester.isna() | (semester % 1 != 0) | ~semester.between(1, 12), "invalid semester")
    for col in ["subject_code", "subject_name", "faculty_id"]:
        flag(df[col].isna() | (df[col] == ""), f"missing {col}")
    for col in ["status", "late_entry", "is_exam_week"]:
        flag(~pd.to_numeric(df[col], errors="coerce").isin([0, 1]), f"{col} is not 0/1")

    for col in ["class_start_time", "class_end_time", "time_in", "time_out"]:
        results = df[col].map(_safe_time)
        df[col] = results.map(lambda r: r[0])
        invalid = results.map(lambda r: not r[1])
        if col.startswith("class"):
            invalid = invalid | df[col].isna()       # class times are required
        flag(invalid, f"invalid {col}")

    # ---- Duplicates: same student + subject + date + class start = same record ----
    ok_so_far = reasons == ""
    dup = df.duplicated(subset=KEY_COLUMNS, keep="first") & ok_so_far
    flag(dup, "duplicate attendance record")
    exact_duplicates = int(raw.duplicated().sum())

    accepted = reasons == ""
    rejected = raw[~accepted].copy()
    rejected["rejection_reason"] = reasons[~accepted].str.rstrip("; ")

    # ---- Build the cleaned dataset ----
    cleaned = df[accepted].copy()
    cleaned["date"] = parsed_date[accepted].dt.strftime(DATE_FORMAT)
    for col in ["semester", "status", "late_entry", "is_exam_week"]:
        cleaned[col] = pd.to_numeric(cleaned[col]).astype(int)
    cleaned = cleaned.drop(columns=["student_name"], errors="ignore")   # not needed for analysis
    cleaned.insert(0, "record_id", [f"R{i:06d}" for i in range(1, len(cleaned) + 1)])
    cleaned = cleaned[COLUMNS]

    # ---- Consistency checks that are REPORTED but not changed (times stay as recorded) ----
    present = cleaned["status"] == 1
    notes = {
        "Present records with missing time_in": int((present & cleaned["time_in"].isna()).sum()),
        "Absent records that have a time_in/time_out": int((~present & (cleaned["time_in"].notna() | cleaned["time_out"].notna())).sum()),
        "Absent records marked late": int((~present & (cleaned["late_entry"] == 1)).sum()),
        "Late flag disagrees with time_in > class start": int((present & cleaned["time_in"].notna()
                                                              & ((cleaned["time_in"] > cleaned["class_start_time"]).astype(int) != cleaned["late_entry"])).sum()),
    }
    missing_in_absent = int((~present & cleaned["time_in"].isna()).sum())

    try:
        cleaned_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(cleaned_path, index=False)
        rejected_path = cleaned_path.parent / "rejected_rows.csv"
        if len(rejected) > 0:
            rejected.to_csv(rejected_path, index=False)
        elif rejected_path.exists():
            rejected_path.unlink()
    except PermissionError:
        raise AttendanceDataError(f"Cannot write to {cleaned_path.name} - close it if it is open in Excel.")

    summary = {
        "raw_rows": len(raw), "cleaned_rows": len(cleaned), "rejected_rows": len(rejected),
        "unique_students": int(cleaned["student_id"].nunique()),
        "exact_duplicate_rows_in_raw": exact_duplicates,
        "duplicate_key_rows_rejected": int(dup.sum()),
        "missing_time_in_kept_for_absent": missing_in_absent,
        "consistency_notes": notes,
    }
    report = [
        "EduTrack - attendance cleaning report",
        f"Raw file (unchanged): {raw_path.name}",
        f"Cleaned file: {cleaned_path.name}",
        f"Raw rows: {summary['raw_rows']}",
        f"Cleaned rows kept: {summary['cleaned_rows']}",
        f"Rows rejected (see rejected_rows.csv): {summary['rejected_rows']}",
        f"Unique students: {summary['unique_students']}",
        f"Exact duplicate rows in raw: {exact_duplicates}",
        f"Duplicates by key {KEY_COLUMNS}: {summary['duplicate_key_rows_rejected']}",
        f"Missing time_in/time_out kept as empty for absent students: {missing_in_absent}",
        "student_name column removed from cleaned file (not needed); student_id kept.",
        "Consistency checks (reported only, values NOT changed):",
    ] + [f"  - {k}: {v}" for k, v in notes.items()]
    (cleaned_path.parent / "cleaning_report.txt").write_text("\n".join(report), encoding="utf-8")
    summary["report"] = "\n".join(report)
    return summary


if __name__ == "__main__":
    try:
        print(clean()["report"])
    except AttendanceDataError as err:
        print("ERROR:", err)
