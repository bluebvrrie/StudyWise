"""
attendance_manager.py
---------------------
CRUD (Create, Read, Update, Delete) for the cleaned attendance CSV.

The CSV file is the ONLY storage (no database). Every operation:
  1. reads the CSV fresh from disk,
  2. validates the data,
  3. changes only the one record asked for (found by its unique record_id),
  4. writes the whole file safely (temp file + replace) so a failed save can
     never leave a half-written / corrupted CSV.
"""
import os
import re
import tempfile
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd

# ---------- Paths (relative to this file, so it works from any folder) ----------
BASE_DIR = Path(__file__).resolve().parent
RAW_CSV = BASE_DIR / "data" / "sample_dataset.csv"        # original data - never modified
CLEAN_CSV = BASE_DIR / "data" / "attendance_cleaned.csv"  # working data - CRUD happens here

# ---------- Column definitions ----------
COLUMNS = [
    "record_id", "student_id", "semester", "subject_code", "subject_name",
    "faculty_id", "date", "class_start_time", "class_end_time", "time_in",
    "time_out", "status", "late_entry", "is_exam_week", "remarks",
]
# A record is "the same attendance record" if these 4 fields match.
# (Student ID alone is NOT unique - one student has many records.)
KEY_COLUMNS = ["student_id", "subject_code", "date", "class_start_time"]
INT_COLUMNS = ["semester", "status", "late_entry", "is_exam_week"]
DATE_FORMAT = "%Y-%m-%d"
STUDENT_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{2,20}$")


class AttendanceDataError(Exception):
    """Raised for problems with the CSV file itself (missing, empty, locked...)."""


# ---------- Small helper functions (also used by clean_attendance.py) ----------
def normalize_time(value):
    """Return a time as 'HH:MM' text, or None if empty. Raises ValueError if invalid."""
    if isinstance(value, (time, datetime)):
        return value.strftime("%H:%M")
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p"):
        try:
            return datetime.strptime(text, fmt).strftime("%H:%M")
        except ValueError:
            continue
    raise ValueError(f"'{text}' is not a valid time")


def parse_date(value):
    """Return a datetime.date. Raises ValueError if invalid."""
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return datetime.strptime(str(value).strip(), DATE_FORMAT).date()


def whole_number(value):
    """Return int(value) if it is a whole number, otherwise None."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number != int(number):   # NaN or has decimals
        return None
    return int(number)


def record_label(row):
    """Readable one-line description of a record (used in select boxes)."""
    status = "Present" if row["status"] == 1 else "Absent"
    day = row["date"].strftime(DATE_FORMAT) if pd.notna(row["date"]) else "no date"
    return f"{row['record_id']} | {row['student_id']} | {row['subject_code']} | {day} | {status}"


class AttendanceManager:
    def __init__(self, csv_path=CLEAN_CSV):
        self.csv_path = Path(csv_path)

    # =====================================================================
    # READ
    # =====================================================================
    def load(self):
        """Read the CSV from disk and return a DataFrame with proper data types."""
        if not self.csv_path.exists():
            raise AttendanceDataError(
                f"The file '{self.csv_path.name}' was not found in '{self.csv_path.parent}'. "
                "Run clean_attendance.py to create it from the raw CSV.")
        try:
            raw = pd.read_csv(self.csv_path, dtype=str)
        except pd.errors.EmptyDataError:
            raise AttendanceDataError(f"'{self.csv_path.name}' is empty (it has no header or data).")
        except PermissionError:
            raise AttendanceDataError(
                f"Cannot read '{self.csv_path.name}' - it may be locked. Close it in Excel and try again.")
        except (OSError, UnicodeDecodeError, pd.errors.ParserError) as err:
            raise AttendanceDataError(f"Could not read '{self.csv_path.name}': {err}")

        missing = [c for c in COLUMNS if c not in raw.columns]
        if missing:
            raise AttendanceDataError(
                f"'{self.csv_path.name}' is missing required column(s): {', '.join(missing)}. "
                "Re-run clean_attendance.py to rebuild it.")
        return self._convert_types(raw[COLUMNS])

    @staticmethod
    def _convert_types(raw):
        df = raw.copy()
        for col in INT_COLUMNS:
            df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")
        df["date"] = pd.to_datetime(df["date"], format=DATE_FORMAT, errors="coerce")
        for col in ["record_id", "student_id", "subject_code", "subject_name", "faculty_id",
                    "class_start_time", "class_end_time", "time_in", "time_out", "remarks"]:
            df[col] = df[col].str.strip()
        return df

    @staticmethod
    def get_record(df, record_id):
        """Return the single row with this record_id (or None)."""
        found = df[df["record_id"] == record_id]
        return found.iloc[0] if len(found) == 1 else None

    # =====================================================================
    # VALIDATION (shared by Create and Update)
    # =====================================================================
    def validate(self, data, existing_df, ignore_record_id=None):
        """Check form data. Returns (clean_row_dict_or_None, errors, warnings)."""
        errors, warnings = [], []

        student_id = str(data.get("student_id") or "").strip().upper()
        if not student_id:
            errors.append("Student ID is required.")
        elif not STUDENT_ID_PATTERN.match(student_id):
            errors.append("Student ID may only contain letters, digits, '-' and '_' (2-20 characters).")

        semester = whole_number(data.get("semester"))
        if semester is None or not 1 <= semester <= 12:
            errors.append("Semester must be a whole number between 1 and 12.")

        subject_code = str(data.get("subject_code") or "").strip().upper()
        subject_name = str(data.get("subject_name") or "").strip()
        faculty_id = str(data.get("faculty_id") or "").strip().upper()
        if not subject_code:
            errors.append("Subject code is required.")
        if not subject_name:
            errors.append("Subject name is required.")
        if not faculty_id:
            errors.append("Faculty ID is required.")

        class_date = None
        try:
            class_date = parse_date(data.get("date"))
            if class_date > date.today():
                errors.append("Date cannot be in the future.")
        except (ValueError, TypeError):
            errors.append(f"Date is invalid (use {DATE_FORMAT}).")

        times = {}
        for field, label in [("class_start_time", "Class start time"), ("class_end_time", "Class end time"),
                             ("time_in", "Time in"), ("time_out", "Time out")]:
            try:
                times[field] = normalize_time(data.get(field))
            except ValueError as err:
                times[field] = None
                errors.append(f"{label}: {err}.")
        start, end = times["class_start_time"], times["class_end_time"]
        if start is None and "Class start time" not in " ".join(errors):
            errors.append("Class start time is required.")
        if end is None and "Class end time" not in " ".join(errors):
            errors.append("Class end time is required.")
        if start and end and end <= start:       # 'HH:MM' text compares correctly
            errors.append("Class end time must be after the class start time.")

        flags = {}
        for field, label in [("status", "Status"), ("late_entry", "Late entry"), ("is_exam_week", "Exam week")]:
            value = whole_number(data.get(field))
            if value not in (0, 1):
                errors.append(f"{label} must be 0 or 1.")
            flags[field] = value

        # Consistency between status, times and late entry
        time_in, time_out = times["time_in"], times["time_out"]
        if flags["status"] == 0:
            if time_in or time_out:
                errors.append("An Absent record must not have time in / time out.")
            if flags["late_entry"] == 1:
                errors.append("An Absent student cannot be marked as a late entry.")
        elif flags["status"] == 1:
            if not time_in or not time_out:
                errors.append("A Present record needs both time in and time out.")
            elif time_out < time_in:
                errors.append("Time out cannot be before time in.")
            elif start and flags["late_entry"] in (0, 1):
                is_late = time_in > start
                if is_late and flags["late_entry"] == 0:
                    errors.append(f"Time in ({time_in}) is after class start ({start}), so Late entry must be Yes.")
                if not is_late and flags["late_entry"] == 1:
                    errors.append(f"Time in ({time_in}) is not after class start ({start}), so Late entry must be No.")

        remarks = str(data.get("remarks") or "").strip()
        if len(remarks) > 200:
            errors.append("Remarks must be 200 characters or fewer.")
        if remarks[:1] in ("=", "+", "-", "@"):
            errors.append("Remarks must not start with =, +, - or @ (unsafe in spreadsheets).")
        if not remarks and not errors:
            remarks = "Absent" if flags["status"] == 0 else ("Late" if flags["late_entry"] == 1 else "On time")

        # Duplicate check using the record key (student + subject + date + start time)
        if not errors and len(existing_df) > 0:
            same = existing_df[(existing_df["student_id"] == student_id)
                               & (existing_df["subject_code"] == subject_code)
                               & (existing_df["date"] == pd.Timestamp(class_date))
                               & (existing_df["class_start_time"] == start)]
            if ignore_record_id is not None:
                same = same[same["record_id"] != ignore_record_id]
            if len(same) > 0:
                errors.append("A record for this student, subject, date and class time already exists "
                              f"(Record ID {same.iloc[0]['record_id']}).")

        # Warnings (record can still be saved)
        if not errors and len(existing_df) > 0:
            earlier = existing_df.loc[existing_df["student_id"] == student_id, "semester"].dropna()
            if len(earlier) > 0 and semester not in set(earlier.astype(int)):
                warnings.append(f"{student_id} has other records in a different semester - please double-check.")

        if errors:
            return None, errors, warnings
        row = {
            "student_id": student_id, "semester": semester, "subject_code": subject_code,
            "subject_name": subject_name, "faculty_id": faculty_id, "date": pd.Timestamp(class_date),
            "class_start_time": start, "class_end_time": end, "time_in": time_in, "time_out": time_out,
            "status": flags["status"], "late_entry": flags["late_entry"],
            "is_exam_week": flags["is_exam_week"], "remarks": remarks,
        }
        return row, [], warnings

    @staticmethod
    def _errors_text(errors):
        return "Record not saved:\n" + "\n".join(f"- {e}" for e in errors)

    # =====================================================================
    # CREATE
    # =====================================================================
    def add_record(self, data):
        """Validate and append one new record. Returns (ok, message, warnings)."""
        try:
            df = self.load()
            row, errors, warnings = self.validate(data, df)
            if errors:
                return False, self._errors_text(errors), warnings
            row["record_id"] = self._next_record_id(df)
            new_df = pd.concat([df, pd.DataFrame([row])[COLUMNS]], ignore_index=True)
            self._save(new_df)
        except AttendanceDataError as err:
            return False, str(err), []
        return True, f"Record {row['record_id']} added for {row['student_id']}.", warnings

    @staticmethod
    def _next_record_id(df):
        numbers = pd.to_numeric(df["record_id"].str.extract(r"(\d+)")[0], errors="coerce")
        next_number = int(numbers.max()) + 1 if numbers.notna().any() else 1
        return f"R{next_number:06d}"

    # =====================================================================
    # UPDATE
    # =====================================================================
    def update_record(self, record_id, data):
        """Validate and change ONLY the record with this record_id."""
        try:
            df = self.load()
            matches = df.index[df["record_id"] == record_id]
            if len(matches) != 1:
                return False, f"Record '{record_id}' was not found (it may have been deleted).", []
            row, errors, warnings = self.validate(data, df, ignore_record_id=record_id)
            if errors:
                return False, self._errors_text(errors), warnings
            for column, value in row.items():
                df.loc[matches[0], column] = value
            self._save(df)
        except AttendanceDataError as err:
            return False, str(err), []
        return True, f"Record {record_id} updated.", warnings

    # =====================================================================
    # DELETE
    # =====================================================================
    def delete_record(self, record_id):
        """Delete ONLY the record with this record_id."""
        try:
            df = self.load()
            matches = df.index[df["record_id"] == record_id]
            if len(matches) != 1:
                return False, f"Record '{record_id}' was not found (it may already be deleted)."
            self._save(df.drop(index=matches[0]))
        except AttendanceDataError as err:
            return False, str(err)
        return True, f"Record {record_id} deleted."

    # =====================================================================
    # SAVE (safe write)
    # =====================================================================
    def _save(self, df):
        """Write to a temporary file first, then replace the real CSV in one step."""
        out = df[COLUMNS].copy()
        out["date"] = out["date"].dt.strftime(DATE_FORMAT)
        temp_name = None
        try:
            handle, temp_name = tempfile.mkstemp(suffix=".tmp", dir=self.csv_path.parent)
            os.close(handle)
            out.to_csv(temp_name, index=False)
            os.replace(temp_name, self.csv_path)
            temp_name = None
        except PermissionError:
            raise AttendanceDataError(
                f"Could not save - '{self.csv_path.name}' is locked (probably open in Excel). "
                "Close it and try again. Your data was not changed.")
        except OSError as err:
            raise AttendanceDataError(f"Could not save the CSV: {err}. Your data was not changed.")
        finally:
            if temp_name and os.path.exists(temp_name):
                os.remove(temp_name)
