"""
attendance_analysis.py
Key formulas
  Overall attendance %  = Present records / Total valid records * 100
  Student attendance %  = Classes attended by the student / Classes recorded for that student * 100
"""
from datetime import datetime

import numpy as np
import pandas as pd

THRESHOLD = 75.0


def percentage(part, whole):
    """part/whole*100, returning 0.0 instead of crashing when whole is 0."""
    return round(part / whole * 100, 2) if whole else 0.0


def valid_records(df):
    """Keep only rows whose status is a real 0/1 value (so bad rows never skew percentages)."""
    return df[df["status"].isin([0, 1])]


# ---------------------------------------------------------------- filter & sort
def apply_filters(df, student_search="", semesters=None, subjects=None, status="All",
                  start_date=None, end_date=None, late="All", exam="All"):
    """Apply every active filter together. Empty/None/'All' means 'do not filter'."""
    mask = pd.Series(True, index=df.index)
    if student_search and student_search.strip():
        mask &= df["student_id"].fillna("").str.contains(student_search.strip(), case=False, regex=False)
    if semesters:
        mask &= df["semester"].isin(semesters)
    if subjects:
        mask &= df["subject_code"].isin(subjects)
    if status == "Present":
        mask &= df["status"] == 1
    elif status == "Absent":
        mask &= df["status"] == 0
    if start_date is not None:
        mask &= df["date"] >= pd.Timestamp(start_date)
    if end_date is not None:
        mask &= df["date"] <= pd.Timestamp(end_date)
    if late == "Late entries only":
        mask &= df["late_entry"] == 1
    elif late == "Not late":
        mask &= df["late_entry"] == 0
    if exam == "Exam week only":
        mask &= df["is_exam_week"] == 1
    elif exam == "Regular week only":
        mask &= df["is_exam_week"] == 0
    return df[mask.fillna(False)]


def sort_data(df, column, ascending=True):
    if column not in df.columns:
        return df
    return df.sort_values(column, ascending=ascending, kind="mergesort")   # mergesort = stable


# ---------------------------------------------------------------- summaries
def student_summary(df):
    """One row per student: classes recorded, attended, percentage."""
    v = valid_records(df)
    table = v.groupby("student_id").agg(
        semester=("semester", "first"),
        classes_recorded=("status", "size"),
        classes_attended=("status", "sum"),
    ).reset_index()
    table["classes_attended"] = table["classes_attended"].astype(int)
    table["attendance_pct"] = (table["classes_attended"] / table["classes_recorded"] * 100).round(2)
    return table.sort_values(["attendance_pct", "student_id"]).reset_index(drop=True)


def overall_metrics(df, threshold=THRESHOLD):
    v = valid_records(df)
    total = len(v)
    present = int((v["status"] == 1).sum())
    students = student_summary(v)
    below = int((students["attendance_pct"] < threshold).sum())
    return {
        "total_records": total,
        "unique_students": int(v["student_id"].nunique()),
        "present": present,
        "absent": total - present,
        "overall_pct": percentage(present, total),
        "below_threshold": below,
        "meeting_threshold": len(students) - below,
    }


def group_summary(df, columns):
    """Attendance by one or more columns (e.g. subject_code, semester)."""
    v = valid_records(df)
    table = v.groupby(columns).agg(total=("status", "size"), present=("status", "sum")).reset_index()
    table["present"] = table["present"].astype(int)
    table["absent"] = table["total"] - table["present"]
    table["attendance_pct"] = (table["present"] / table["total"] * 100).round(2)
    return table


def trend_summary(df, frequency="Monthly"):
    """Attendance % per month or per week (periods with no records are skipped)."""
    v = valid_records(df).dropna(subset=["date"])
    if v.empty:
        return pd.DataFrame(columns=["period", "total", "present", "attendance_pct"])
    code = "M" if frequency == "Monthly" else "W"
    period = v["date"].dt.to_period(code).dt.start_time
    table = v.groupby(period).agg(total=("status", "size"), present=("status", "sum")).reset_index()
    table = table.rename(columns={"date": "period"})
    table["present"] = table["present"].astype(int)
    table["attendance_pct"] = (table["present"] / table["total"] * 100).round(2)
    return table


def minutes_late(df):
    """Minutes between class start and time in, for present students who arrived late."""
    late = valid_records(df)
    late = late[(late["status"] == 1) & (late["late_entry"] == 1)]
    start = pd.to_datetime(late["class_start_time"], format="%H:%M", errors="coerce")
    arrived = pd.to_datetime(late["time_in"], format="%H:%M", errors="coerce")
    minutes = ((arrived - start).dt.total_seconds() / 60).dropna()
    return minutes[minutes > 0].to_numpy()


def late_summary(df):
    v = valid_records(df)
    present = v[v["status"] == 1]
    late_count = int((present["late_entry"] == 1).sum())
    mins = minutes_late(v)
    return {
        "present_records": len(present), "late": late_count,
        "on_time": len(present) - late_count,
        "late_pct_of_present": percentage(late_count, len(present)),
        "avg_minutes_late": round(float(np.mean(mins)), 1) if len(mins) else None,
    }


def exam_summary(df):
    table = group_summary(df, "is_exam_week")
    table["period_type"] = table["is_exam_week"].map({1: "Exam week", 0: "Regular week"})
    return table[["period_type", "total", "present", "absent", "attendance_pct"]]


def numeric_stats(df):
    """Mean/median/min/max/std of student attendance % (NumPy) and of late minutes."""
    students = student_summary(df)
    stats = {"students_counted": len(students)}
    if len(students) == 0:
        return stats
    pct = students["attendance_pct"].to_numpy(dtype=float)
    stats.update({
        "mean_pct": round(float(np.mean(pct)), 2),
        "median_pct": round(float(np.median(pct)), 2),
        "min_pct": round(float(np.min(pct)), 2),
        "max_pct": round(float(np.max(pct)), 2),
        # std needs 2+ students; ddof=1 = sample standard deviation
        "std_pct": round(float(np.std(pct, ddof=1)), 2) if len(pct) > 1 else None,
    })
    mins = minutes_late(df)
    stats["median_minutes_late"] = round(float(np.median(mins)), 1) if len(mins) else None
    stats["max_minutes_late"] = round(float(np.max(mins)), 1) if len(mins) else None
    return stats


# ---------------------------------------------------------------- report
def build_report(filtered, total_in_file, filters, threshold=THRESHOLD, generated_at=None):
    """Plain-text report built from the CURRENT filtered data."""
    generated_at = generated_at or datetime.now()
    m = overall_metrics(filtered, threshold)
    lines = [
        "EduTrack Attendance Analysis Report",
        "=" * 40,
        f"Report generated at (local time): {generated_at.strftime('%Y-%m-%d %H:%M:%S')}",
        f"Records included: {m['total_records']} (of {total_in_file} in the file)",
        f"Unique students included: {m['unique_students']}",
        "", "Active filters:",
    ] + [f"  - {name}: {value}" for name, value in filters.items()]
    if m["total_records"] == 0:
        lines += ["", "No records match the active filters, so there is nothing to summarise."]
        return "\n".join(lines)
    lines += [
        "", "Summary:",
        f"  Present records: {m['present']}",
        f"  Absent records: {m['absent']}",
        f"  Overall attendance: {m['overall_pct']}%",
        f"  Students below {threshold:.0f}%: {m['below_threshold']}",
        f"  Students at or above {threshold:.0f}%: {m['meeting_threshold']}",
        "", "Attendance by subject:",
        group_summary(filtered, ["subject_code", "subject_name"]).to_string(index=False),
        "", "Attendance by semester:",
        group_summary(filtered, "semester").to_string(index=False),
        "", "Late entries:",
    ]
    late = late_summary(filtered)
    lines += [f"  {late['late']} of {late['present_records']} present records were late ({late['late_pct_of_present']}%)."]
    lines += ["", "Exam week vs regular week:", exam_summary(filtered).to_string(index=False)]
    low = student_summary(filtered)
    low = low[low["attendance_pct"] < threshold].head(10)
    if len(low):
        lines += ["", f"Lowest-attendance students below {threshold:.0f}% (up to 10):",
                  low.to_string(index=False)]
    lines += ["", "Note: percentages use only the records that match the filters above."]
    return "\n".join(lines)


# ---------------------------------------------------------------- insights & display table
def key_insights(df, threshold=THRESHOLD):
    """Short plain-language findings computed from the CURRENT data (nothing invented).
    Returns a list of (tone, text); tone is 'good', 'warn' or 'info'."""
    out = []
    v = valid_records(df)
    if v.empty:
        return out
    subjects = group_summary(v, ["subject_code", "subject_name"])
    if len(subjects) > 1:
        top = subjects.loc[subjects["attendance_pct"].idxmax()]
        low = subjects.loc[subjects["attendance_pct"].idxmin()]
        out.append(("good", f"Highest subject attendance: {top['subject_name']} ({top['attendance_pct']}%)"))
        out.append(("warn" if low["attendance_pct"] < threshold else "info",
                    f"Lowest subject attendance: {low['subject_name']} ({low['attendance_pct']}%)"))
    exam = exam_summary(v)
    if len(exam) == 2:
        pct = dict(zip(exam["period_type"], exam["attendance_pct"]))
        gap = round(pct["Regular week"] - pct["Exam week"], 2)
        word = "lower" if gap > 0 else "higher"
        out.append(("warn" if gap > 5 else "info", f"Exam-week attendance is {abs(gap)} points {word} than regular weeks"))
    metrics = overall_metrics(v, threshold)
    if metrics["unique_students"]:
        share = round(metrics["below_threshold"] / metrics["unique_students"] * 100, 1)
        out.append(("warn" if metrics["below_threshold"] else "good",
                    f"{metrics['below_threshold']} of {metrics['unique_students']} students ({share}%) are below {threshold:g}%"))
    return out


def display_table(df):
    """Readable version of the records for the screen (friendly headings and labels)."""
    return pd.DataFrame({
        "Record": df["record_id"],
        "Student": df["student_id"],
        "Sem": df["semester"],
        "Subject": df["subject_code"].fillna("") + " · " + df["subject_name"].fillna(""),
        "Date": df["date"].dt.strftime("%Y-%m-%d"),
        "Class time": df["class_start_time"].fillna("") + "–" + df["class_end_time"].fillna(""),
        "Time in": df["time_in"].fillna("—"),
        "Time out": df["time_out"].fillna("—"),
        "Status": df["status"].map({1: "Present", 0: "Absent"}),
        "Late": df["late_entry"].map({1: "Yes", 0: "No"}),
        "Exam week": df["is_exam_week"].map({1: "Yes", 0: "No"}),
        "Remarks": df["remarks"].fillna(""),
    })
