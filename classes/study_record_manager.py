
from pathlib import Path
import os
import tempfile

import numpy as np
import pandas as pd


class StudyRecordManager:
    """Manage StudyWise subject records stored in a CSV file."""

    COLUMNS = [
        "Record_ID",
        "Student_ID",
        "Subject",
        "Previous_Marks",
        "Target_Marks",
        "Difficulty",
        "Study_Hours",
        "Exam_Days_Left",
        "Target_Grade",
    ]

    NUMERIC_COLUMNS = [
        "Previous_Marks",
        "Target_Marks",
        "Difficulty",
        "Study_Hours",
        "Exam_Days_Left",
    ]

    def __init__(self, csv_path=None):
        """Set up the manager and load the records."""

        project_dir = Path(__file__).resolve().parent.parent

        if csv_path is None:
            csv_path = project_dir / "data" / "study_records.csv"

        self.csv_path = Path(csv_path)
        self.df = pd.DataFrame(columns=self.COLUMNS)

        self.load_data()

    def load_data(self):
        """Load records from the CSV file."""

        try:
            if not self.csv_path.exists():
                self.csv_path.parent.mkdir(
                    parents=True, exist_ok=True
                )
                self.df = pd.DataFrame(columns=self.COLUMNS)
                self.save_data()
                print("Created an empty study records CSV.")
                return self.df

            data = pd.read_csv(self.csv_path)

            if data.empty and len(data.columns) == 0:
                self.df = pd.DataFrame(columns=self.COLUMNS)
                print("The CSV is empty and has no headers.")
                return self.df

            missing_columns = [
                col for col in self.COLUMNS
                if col not in data.columns
            ]

            if missing_columns:
                raise ValueError(
                    f"CSV is missing columns: {missing_columns}"
                )

            self.df = data[self.COLUMNS].copy()

            for col in self.NUMERIC_COLUMNS:
                self.df[col] = pd.to_numeric(
                    self.df[col], errors="coerce"
                )

            if self.df["Record_ID"].duplicated().any():
                raise ValueError("Duplicate Record_ID values found.")

            print(f"Loaded {len(self.df)} records.")
            return self.df

        except (OSError, pd.errors.ParserError, ValueError) as error:
            print(f"Could not load records: {error}")
            raise
        else:
            print("CSV loading completed.")
        finally:
            print("Load operation finished.")

    
    def validate_record(self, record):
        """Validate one record before it is added or updated."""

        # Check required text fields
        required_text = ["Record_ID", "Student_ID", "Subject"]

        for col in required_text:
            value = record.get(col)

            if value is None or pd.isna(value) or not str(value).strip():
                raise ValueError(f"{col} cannot be empty.")

        # Check required numeric fields
        for col in self.NUMERIC_COLUMNS:
            value = record.get(col)

            if value is None or pd.isna(value):
                raise ValueError(f"{col} is required.")

            try:
                value = float(value)
            except (TypeError, ValueError):
                raise ValueError(f"{col} must be a number.")

            if not np.isfinite(value):
                raise ValueError(f"{col} must be a finite number.")

        # Marks must be between 0 and 100
        for col in ["Previous_Marks", "Target_Marks"]:
            value = float(record[col])

            if not 0 <= value <= 100:
                raise ValueError(f"{col} must be between 0 and 100.")

        # Difficulty must be an integer from 1 to 4
        difficulty = float(record["Difficulty"])

        if difficulty not in [1, 2, 3, 4]:
            raise ValueError("Difficulty must be 1, 2, 3, or 4.")

        # Study hours cannot be negative
        if float(record["Study_Hours"]) < 0:
            raise ValueError("Study_Hours cannot be negative.")

        # Days remaining must be a non-negative whole number
        days = float(record["Exam_Days_Left"])

        if days < 0 or not days.is_integer():
            raise ValueError(
                "Exam_Days_Left must be a non-negative whole number."
            )

        # Target grade is optional, but must be text if supplied
        grade = record.get("Target_Grade", "")

        if grade is None or pd.isna(grade):
            grade = ""

        if not isinstance(grade, str):
            raise ValueError("Target_Grade must be text.")

        return True


    def get_records(self):
        """Return a copy of all records."""

        return self.df.copy()

    def add_record(self, record):
        """Validate and add a new record."""

        self.validate_record(record)

        record_id = str(record["Record_ID"]).strip()

        if record_id in self.df["Record_ID"].astype(str).values:
            raise ValueError(f"Record_ID {record_id} already exists.")

        new_record = {
            col: record.get(col, "")
            for col in self.COLUMNS
        }
        new_record["Record_ID"] = record_id

        updated_df = pd.concat(
            [self.df, pd.DataFrame([new_record])],
            ignore_index=True,
        )

        self._save_dataframe(updated_df)
        self.df = updated_df
        return True

    def update_record(self, record_id, changes):
        """Update an existing record by its unique ID."""

        matches = self.df["Record_ID"].astype(str) == str(record_id)

        if not matches.any():
            raise ValueError(f"Record {record_id} was not found.")

        updated_df = self.df.copy()
        index = updated_df.index[matches][0]

        updated_record = updated_df.loc[index].to_dict()
        updated_record.update(changes)

        if str(updated_record["Record_ID"]) != str(record_id):
            raise ValueError("Record_ID cannot be changed.")

        self.validate_record(updated_record)

        for col in self.COLUMNS:
            updated_df.loc[index, col] = updated_record[col]

        self._save_dataframe(updated_df)
        self.df = updated_df
        return True

    def delete_record(self, record_id):
        """Delete a record by its unique ID."""

        matches = self.df["Record_ID"].astype(str) == str(record_id)

        if not matches.any():
            raise ValueError(f"Record {record_id} was not found.")

        updated_df = self.df.loc[~matches].copy()

        self._save_dataframe(updated_df)
        self.df = updated_df
        return True

    def calculate_statistics(self):
        """Calculate the main dashboard statistics."""

        marks = self.df["Previous_Marks"].dropna()
        hours = self.df["Study_Hours"].dropna()

        gaps = (
            self.df["Target_Marks"] - self.df["Previous_Marks"]
        ).clip(lower=0).dropna()

        return {
            "mean_previous_marks": (
                marks.mean() if not marks.empty else None
            ),
            "mean_study_hours": (
                hours.mean() if not hours.empty else None
            ),
            "mean_performance_gap": (
                gaps.mean() if not gaps.empty else None
            ),
            "highest_marks": (
                marks.max() if not marks.empty else None
            ),
            "lowest_marks": (
                marks.min() if not marks.empty else None
            ),
            "subjects_below_target": int(
                (
                    self.df["Previous_Marks"]
                    < self.df["Target_Marks"]
                ).fillna(False).sum()
            ),
            "record_count": len(self.df),
        }

    def calculate_priority(self, record):
        """Calculate a transparent rule-based priority score."""

        self.validate_record(record)

        gap_normalized = max(
            0,
            float(record["Target_Marks"])
            - float(record["Previous_Marks"]),
        ) / 100

        difficulty_normalized = (
            float(record["Difficulty"]) - 1
        ) / 3

        urgency = 1 - min(
            float(record["Exam_Days_Left"]), 30
        ) / 30

        return (
            0.5 * gap_normalized
            + 0.3 * difficulty_normalized
            + 0.2 * urgency
        )

    def allocate_study_time(self, available_hours):
        """Allocate daily study hours according to priority."""

        available_hours = float(available_hours)

        if not np.isfinite(available_hours) or available_hours < 0:
            raise ValueError(
                "Available hours must be a finite, non-negative number."
            )

        if self.df.empty:
            return pd.DataFrame(
                columns=["Record_ID", "Subject", "Priority",
                         "Recommended_Hours"]
            )

        results = self.df.copy()
        results["Priority"] = results.apply(
            lambda row: self.calculate_priority(row.to_dict()),
            axis=1,
        )

        priority_sum = results["Priority"].sum()

        if priority_sum == 0:
            results["Recommended_Hours"] = (
                available_hours / len(results)
            )
        else:
            results["Recommended_Hours"] = (
                available_hours
                * results["Priority"]
                / priority_sum
            )

        # Round to two decimal places, then correct rounding drift.
        results["Recommended_Hours"] = (
            results["Recommended_Hours"].round(2)
        )

        if len(results) > 0:
            difference = round(
                available_hours
                - results["Recommended_Hours"].sum(),
                2,
            )
            results.loc[
                results["Priority"].idxmax(),
                "Recommended_Hours",
            ] += difference

        return results[
            ["Record_ID", "Subject", "Priority", "Recommended_Hours"]
        ]

    def _save_dataframe(self, dataframe):
        """Save safely without replacing the old file on failure."""

        temp_path = None

        try:
            self.csv_path.parent.mkdir(
                parents=True, exist_ok=True
            )

            with tempfile.NamedTemporaryFile(
                mode="w",
                newline="",
                suffix=".csv",
                prefix="study_records_",
                dir=self.csv_path.parent,
                delete=False,
                encoding="utf-8",
            ) as temp_file:
                temp_path = Path(temp_file.name)
                dataframe.to_csv(temp_file, index=False)

            os.replace(temp_path, self.csv_path)
            temp_path = None

        except (OSError, ValueError) as error:
            print(f"Could not save records: {error}")
            raise
        else:
            print("Records saved successfully.")
        finally:
            if temp_path is not None and temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass

    def save_data(self):
        """Save the manager's current records."""

        self._save_dataframe(self.df)
