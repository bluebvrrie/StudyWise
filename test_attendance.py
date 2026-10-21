"""
test_attendance.py - safe tests. Run with:   python -m unittest -v test_attendance
Every test works on a TEMPORARY COPY of the data, so your real CSV files are never touched.
"""
import hashlib
import itertools
import os
import shutil
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

import pandas as pd

import attendance_analysis as aa
import attendance_calculator as calc
import attendance_charts as charts
import clean_attendance
from attendance_manager import RAW_CSV, AttendanceDataError, AttendanceManager


def md5(path):
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def good_record(**changes):
    record = {"student_id": "ST9999", "semester": 4, "subject_code": "DS301", "subject_name": "Data Science",
              "faculty_id": "F101", "date": date(2025, 9, 10), "class_start_time": "09:00", "class_end_time": "10:00",
              "time_in": "09:00", "time_out": "10:00", "status": 1, "late_entry": 0, "is_exam_week": 0, "remarks": ""}
    record.update(changes)
    return record


class TempDataTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.raw = self.tmp / "raw.csv"
        shutil.copy(RAW_CSV, self.raw)
        self.cleaned = self.tmp / "cleaned.csv"
        clean_attendance.clean(self.raw, self.cleaned)
        self.manager = AttendanceManager(self.cleaned)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestCleaning(TempDataTestCase):
    def test_raw_unchanged_and_counts(self):
        before = md5(RAW_CSV)
        clean_attendance.clean(self.raw, self.cleaned)
        self.assertEqual(md5(RAW_CSV), before)
        df = self.manager.load()
        self.assertEqual(len(df), len(pd.read_csv(RAW_CSV)))
        self.assertNotIn("student_name", df.columns)
        self.assertEqual(int(df["time_in"].isna().sum()), int(pd.read_csv(RAW_CSV)["time_in"].isna().sum()))

    def test_refuses_to_overwrite_raw(self):
        with self.assertRaises(AttendanceDataError):
            clean_attendance.clean(self.raw, self.raw)

    def test_bad_rows_go_to_rejected_file(self):
        raw = pd.read_csv(self.raw, dtype=str)
        raw.loc[0, "date"] = "not-a-date"
        raw.loc[1, "status"] = "7"
        raw = pd.concat([raw, raw.iloc[[5]]])          # exact duplicate
        raw.to_csv(self.raw, index=False)
        result = clean_attendance.clean(self.raw, self.cleaned)
        self.assertEqual(result["rejected_rows"], 3)
        self.assertTrue((self.tmp / "rejected_rows.csv").exists())


class TestAnalysis(TempDataTestCase):
    def test_reference_numbers_match_independent_calculation(self):
        df = self.manager.load()
        raw = pd.read_csv(RAW_CSV)
        m = aa.overall_metrics(df)
        self.assertEqual(m["total_records"], len(raw))
        self.assertEqual(m["unique_students"], raw["student_id"].nunique())
        self.assertEqual(m["present"], int(raw["status"].sum()))
        self.assertEqual(m["overall_pct"], round(raw["status"].mean() * 100, 2))
        per_student = raw.groupby("student_id")["status"].mean() * 100
        self.assertEqual(m["below_threshold"], int((per_student < 75).sum()))

    def test_filters_work_together(self):
        df = self.manager.load()
        out = aa.apply_filters(df, "ST1", [3, 4], ["DS301"], "Present", date(2025, 3, 1), date(2025, 6, 30), "Late entries only", "Regular week only")
        self.assertTrue(len(out) > 0)
        self.assertTrue(out["student_id"].str.contains("ST1").all())
        self.assertTrue(out["semester"].isin([3, 4]).all() and (out["subject_code"] == "DS301").all())
        self.assertTrue((out["status"] == 1).all() and (out["late_entry"] == 1).all() and (out["is_exam_week"] == 0).all())
        self.assertTrue(out["date"].between("2025-03-01", "2025-06-30").all())

    def test_empty_results_are_safe(self):
        empty = aa.apply_filters(self.manager.load(), "NO_SUCH_STUDENT")
        self.assertEqual(len(empty), 0)
        m = aa.overall_metrics(empty)
        self.assertEqual((m["total_records"], m["overall_pct"], m["below_threshold"]), (0, 0.0, 0))
        self.assertEqual(aa.numeric_stats(empty), {"students_counted": 0})
        self.assertIsNone(charts.pie_present_absent(0, 0))
        self.assertIsNone(charts.bar_attendance(aa.group_summary(empty, "semester"), "semester", "t", "x"))
        self.assertIn("No records match", aa.build_report(empty, 10, {"Student": "x"}))

    def test_sorting(self):
        out = aa.sort_data(self.manager.load(), "date", ascending=False)
        self.assertTrue(out["date"].is_monotonic_decreasing)

    def test_report_contains_required_parts(self):
        df = self.manager.load()
        filtered = aa.apply_filters(df, semesters=[3])
        text = aa.build_report(filtered, len(df), {"Semester": "3"})
        for part in ["EduTrack Attendance Analysis Report", "generated at", f"Records included: {len(filtered)}",
                     "Unique students included", "Active filters", "Present records", "Absent records",
                     "Overall attendance", "Students below 75%", "Attendance by subject", "Attendance by semester"]:
            self.assertIn(part, text)

    def test_charts_render(self):
        df = self.manager.load()
        figs = [charts.bar_attendance(aa.group_summary(df, "semester"), "semester", "t", "x"),
                charts.pie_present_absent(5, 1), charts.pie_present_absent(5, 0),
                charts.line_trend(aa.trend_summary(df, "Monthly"), "Monthly"),
                charts.line_trend(aa.trend_summary(df, "Weekly"), "Weekly"),
                charts.hist_minutes_late(aa.minutes_late(df))]
        for fig in figs:
            self.assertIsNotNone(fig)
            fig.savefig(self.tmp / "chart.png")


class TestInsightsAndDisplay(TempDataTestCase):
    def test_insights_come_from_the_data(self):
        df = self.manager.load()
        texts = " ".join(t for _, t in aa.key_insights(df, 75))
        self.assertIn("students", texts)
        self.assertIn("Exam-week attendance", texts)
        self.assertEqual(aa.key_insights(aa.apply_filters(df, "NO_SUCH_STUDENT")), [])

    def test_display_table_is_readable_and_same_length(self):
        df = self.manager.load()
        table = aa.display_table(df)
        self.assertEqual(len(table), len(df))
        self.assertEqual(set(table["Status"].dropna()), {"Present", "Absent"})
        self.assertTrue((table.loc[df["status"] == 0, "Time in"] == "—").all())   # absent: blank times shown as dash
        self.assertNotIn("faculty_id", table.columns)

    def test_new_charts_and_empty_inputs(self):
        df = self.manager.load()
        students = aa.student_summary(df)
        self.assertIsNotNone(charts.hist_student_pct(students["attendance_pct"].to_numpy(), 75))
        self.assertIsNone(charts.hist_student_pct([], 75))
        self.assertIsNone(charts.hist_minutes_late([]))

    def test_custom_threshold_changes_counts(self):
        df = self.manager.load()
        self.assertGreater(aa.overall_metrics(df, 90)["below_threshold"], aa.overall_metrics(df, 75)["below_threshold"])


class TestCalculator(unittest.TestCase):
    def test_known_cases_and_boundaries(self):
        self.assertEqual(calc.calculate(75, 100)["can_miss"], 0)     # exactly 75% -> cannot miss
        self.assertEqual(calc.calculate(9, 10)["can_miss"], 2)       # 9/12 = 75% exactly
        self.assertEqual(calc.calculate(90, 100)["can_miss"], 20)
        self.assertEqual(calc.calculate(5, 10)["need_to_attend"], 10)
        self.assertEqual(calc.calculate(0, 10)["need_to_attend"], 30)
        self.assertEqual(calc.calculate(10, 10, 100)["can_miss"], 0)
        self.assertFalse(calc.calculate(9, 10, 100)["recovery_possible"])

    def test_matches_brute_force(self):
        for total, required in itertools.product(range(1, 41), [50, 60, 75, 80, 66.67, 90]):
            for attended in range(0, total + 1):
                r = calc.calculate(attended, total, required)
                if r["meets"]:
                    x = r["can_miss"]
                    self.assertGreaterEqual(attended * 100, required * (total + x) - 1e-9)
                    self.assertLess(attended * 100, required * (total + x + 1))
                elif r["recovery_possible"]:
                    y = r["need_to_attend"]
                    self.assertGreaterEqual((attended + y) * 100, required * (total + y) - 1e-9)
                    if y > 0:
                        self.assertLess((attended + y - 1) * 100, required * (total + y - 1))

    def test_invalid_inputs(self):
        for args in [(5, 0, 75), (-1, 10, 75), (11, 10, 75), (5, 10, 0), (5, 10, 101)]:
            self.assertTrue(calc.validate_inputs(*args))
            with self.assertRaises(ValueError):
                calc.calculate(*args)


class TestCrud(TempDataTestCase):
    def test_create_read_persist(self):
        before = self.manager.load()
        ok, msg, _ = self.manager.add_record(good_record())
        self.assertTrue(ok, msg)
        after = AttendanceManager(self.cleaned).load()            # fresh object = "reload the page"
        self.assertEqual(len(after), len(before) + 1)
        new = after[after["student_id"] == "ST9999"]
        self.assertEqual(len(new), 1)
        self.assertEqual(new.iloc[0]["remarks"], "On time")
        self.assertEqual(new.iloc[0]["record_id"], f"R{len(before) + 1:06d}")

    def test_duplicate_and_invalid_records_do_not_change_file(self):
        self.assertTrue(self.manager.add_record(good_record())[0])
        fingerprint = md5(self.cleaned)
        bad_cases = [good_record(),                                            # duplicate key
                     good_record(student_id=""), good_record(student_id="bad id!"),
                     good_record(semester=0), good_record(semester="abc"),
                     good_record(date="2025-13-45"), good_record(date=date(2999, 1, 1)),
                     good_record(class_end_time="08:00"), good_record(time_in="25:99"),
                     good_record(status=5), good_record(subject_code=""),
                     good_record(student_id="ST9998", status=0, time_in="09:00"),          # absent with times
                     good_record(student_id="ST9998", time_in="09:10"),                    # late but flag says no
                     good_record(student_id="ST9998", late_entry=1),                       # flag says late, but on time
                     good_record(student_id="ST9998", remarks="=cmd()")]
        for record in bad_cases:
            ok, message, _ = self.manager.add_record(record)
            self.assertFalse(ok, record)
            self.assertIn("not saved", message) if "already exists" not in message else None
        self.assertEqual(md5(self.cleaned), fingerprint)

    def test_absent_record_has_empty_times(self):
        ok, msg, _ = self.manager.add_record(good_record(student_id="ST9997", status=0, time_in=None, time_out=None))
        self.assertTrue(ok, msg)
        row = self.manager.load().query("student_id == 'ST9997'").iloc[0]
        self.assertTrue(pd.isna(row["time_in"]) and pd.isna(row["time_out"]))
        self.assertEqual(row["remarks"], "Absent")

    def test_update_changes_only_selected_record(self):
        before = self.manager.load()
        target = before.iloc[10]
        same_student = before[before["student_id"] == target["student_id"]]
        new_status = 0 if target["status"] == 1 else 1
        data = {"student_id": target["student_id"], "semester": int(target["semester"]), "subject_code": target["subject_code"],
                "subject_name": target["subject_name"], "faculty_id": target["faculty_id"], "date": target["date"],
                "class_start_time": "09:00", "class_end_time": "10:00",
                "time_in": None if new_status == 0 else "09:00", "time_out": None if new_status == 0 else "10:00",
                "status": new_status, "late_entry": 0, "is_exam_week": int(target["is_exam_week"]), "remarks": "edited"}
        ok, msg, _ = self.manager.update_record(target["record_id"], data)
        self.assertTrue(ok, msg)
        after = AttendanceManager(self.cleaned).load()
        self.assertEqual(len(after), len(before))
        changed = after[after["record_id"] == target["record_id"]].iloc[0]
        self.assertEqual((changed["status"], changed["remarks"]), (new_status, "edited"))
        others_before = before[before["record_id"] != target["record_id"]].reset_index(drop=True)
        others_after = after[after["record_id"] != target["record_id"]].reset_index(drop=True)
        pd.testing.assert_frame_equal(others_before, others_after)           # nothing else changed
        self.assertGreater(len(same_student), 1)                              # student had several records

    def test_update_cannot_create_duplicate_or_hit_missing_id(self):
        df = self.manager.load()
        a, b = df.iloc[0], df.iloc[1]
        data = {"student_id": b["student_id"], "semester": int(b["semester"]), "subject_code": b["subject_code"],
                "subject_name": b["subject_name"], "faculty_id": b["faculty_id"], "date": b["date"],
                "class_start_time": b["class_start_time"], "class_end_time": b["class_end_time"],
                "time_in": b["time_in"], "time_out": b["time_out"], "status": int(b["status"]),
                "late_entry": int(b["late_entry"]), "is_exam_week": int(b["is_exam_week"]), "remarks": "x"}
        fingerprint = md5(self.cleaned)
        self.assertFalse(self.manager.update_record(a["record_id"], data)[0])   # would duplicate record b
        self.assertFalse(self.manager.update_record("R999999", data)[0])
        self.assertEqual(md5(self.cleaned), fingerprint)

    def test_delete_removes_only_selected_record(self):
        before = self.manager.load()
        target = before.iloc[20]
        ok, msg = self.manager.delete_record(target["record_id"])
        self.assertTrue(ok, msg)
        after = AttendanceManager(self.cleaned).load()
        self.assertEqual(len(after), len(before) - 1)
        self.assertNotIn(target["record_id"], set(after["record_id"]))
        pd.testing.assert_frame_equal(before.drop(index=20).reset_index(drop=True), after)
        self.assertFalse(self.manager.delete_record(target["record_id"])[0])     # already gone

    def test_locked_file_does_not_corrupt_csv(self):
        fingerprint = md5(self.cleaned)
        with mock.patch("attendance_manager.os.replace", side_effect=PermissionError):
            ok, message, _ = self.manager.add_record(good_record())
        self.assertFalse(ok)
        self.assertIn("locked", message)
        self.assertEqual(md5(self.cleaned), fingerprint)
        self.assertEqual([p.name for p in self.tmp.glob("*.tmp")], [])            # temp file cleaned up


class TestFileProblems(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_missing_file(self):
        with self.assertRaises(AttendanceDataError):
            AttendanceManager(self.tmp / "nope.csv").load()

    def test_empty_file(self):
        (self.tmp / "e.csv").write_text("")
        with self.assertRaises(AttendanceDataError):
            AttendanceManager(self.tmp / "e.csv").load()

    def test_missing_columns(self):
        (self.tmp / "m.csv").write_text("student_id,status\nST1,1\n")
        with self.assertRaisesRegex(AttendanceDataError, "missing required column"):
            AttendanceManager(self.tmp / "m.csv").load()

    def test_header_only_file_gives_empty_dataset(self):
        from attendance_manager import COLUMNS
        (self.tmp / "h.csv").write_text(",".join(COLUMNS) + "\n")
        df = AttendanceManager(self.tmp / "h.csv").load()
        self.assertEqual(len(df), 0)
        self.assertEqual(aa.overall_metrics(df)["total_records"], 0)
        ok, msg, _ = AttendanceManager(self.tmp / "h.csv").add_record(good_record())
        self.assertTrue(ok, msg)


if __name__ == "__main__":
    unittest.main(verbosity=2)
