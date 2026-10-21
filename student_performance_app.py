"""Student Performance & Pass/Fail Analysis module.

The pass rule is an assumption for demonstration: a student passes only when
Assignment, Midterm, and Final marks are each at or above the selected cutoff.
The dataset does not provide an official pass/fail field or grading policy.
"""

from pathlib import Path
import io

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st


REQUIRED_COLUMNS = [
    "Student_ID", "Student_Name", "Gender", "Department", "Year",
    "Attendance", "Study_Hours", "Assignment_Marks", "Midterm_Marks",
    "Final_Marks", "Scholarship",
]
MARK_COLUMNS = ["Assignment_Marks", "Midterm_Marks", "Final_Marks"]
DEFAULT_FILE = Path(__file__).with_name("College_Student_Analysis_Dataset.csv")


def load_data(uploaded_file=None):
    """Load a CSV, check its required fields, and validate mark values."""
    if uploaded_file is None:
        if not DEFAULT_FILE.exists():
            raise FileNotFoundError("Place the supplied dataset beside this app.")
        data = pd.read_csv(DEFAULT_FILE)
    else:
        data = pd.read_csv(uploaded_file)
    missing = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    for column in MARK_COLUMNS:
        data[column] = pd.to_numeric(data[column], errors="coerce")
        if data[column].isna().any():
            raise ValueError(f"{column} contains blank or non-numeric marks.")
        if not data[column].between(0, 100).all():
            raise ValueError(f"{column} must contain marks from 0 to 100.")
    return data


def add_performance_results(data, cutoff):
    """Return a copy with average marks and an explainable pass/fail label."""
    result = data.copy()
    result["Average_Marks"] = result[MARK_COLUMNS].mean(axis=1)
    result["Result"] = np.where(
        result[MARK_COLUMNS].ge(cutoff).all(axis=1), "Pass", "Fail"
    )
    result["At_Risk"] = result["Result"].eq("Fail") | result["Average_Marks"].lt(cutoff + 10)
    return result


def main():
    st.set_page_config(page_title="Student Performance Analysis", page_icon="📊", layout="wide")
    st.title("Student Performance & Pass/Fail Analysis")
    st.write("Explore the supplied student marks and identify students who may need support.")
    st.info(
        "**Assumed rule:** Pass when Assignment, Midterm, and Final marks are each at "
        "least the selected cutoff. The source CSV contains no official result or grading policy."
    )

    with st.sidebar:
        st.header("Settings")
        uploaded = st.file_uploader("Upload a CSV (optional)", type=["csv"])
        cutoff = st.slider("Minimum mark for each assessment", 0, 100, 40)
        st.caption("Default 40 is an illustrative assumption. Confirm the course rule with your professor.")

    try:
        data = load_data(uploaded)
    except (OSError, ValueError, pd.errors.ParserError) as error:
        st.error(f"Could not load this dataset: {error}")
        st.stop()

    results = add_performance_results(data, cutoff)
    with st.sidebar:
        departments = ["All"] + sorted(results["Department"].dropna().unique().tolist())
        department = st.selectbox("Department", departments)
        years = sorted(results["Year"].dropna().unique().tolist())
        chosen_years = st.multiselect("Year", years, default=years)
        outcome = st.selectbox("Result", ["All", "Pass", "Fail"])

    view = results.copy()
    if department != "All":
        view = view[view["Department"] == department]
    view = view[view["Year"].isin(chosen_years)]
    if outcome != "All":
        view = view[view["Result"] == outcome]

    total = len(view)
    pass_count = int(view["Result"].eq("Pass").sum())
    fail_count = total - pass_count
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Students in view", total)
    col2.metric("Pass", pass_count)
    col3.metric("Fail", fail_count)
    col4.metric("Average of assessment marks", f"{view['Average_Marks'].mean():.1f}" if total else "N/A")

    st.subheader("Results by department")
    dept_results = results.groupby(["Department", "Result"]).size().unstack(fill_value=0)
    fig, ax = plt.subplots(figsize=(9, 4))
    dept_results.reindex(sorted(dept_results.index)).plot(
        kind="bar", ax=ax,
        color=[{"Pass": "#43a047", "Fail": "#e45756"}.get(name, "#7a7a7a") for name in dept_results.columns],
    )
    ax.set_ylabel("Number of students")
    ax.set_xlabel("Department")
    ax.set_title(f"Pass and fail counts (each assessment cutoff: {cutoff})")
    ax.tick_params(axis="x", rotation=25)
    ax.legend(title="Estimated result")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Assessment mark distribution")
    fig, ax = plt.subplots(figsize=(9, 4))
    results[MARK_COLUMNS].boxplot(ax=ax)
    ax.set_ylabel("Marks (0–100)")
    ax.set_title("Assignment, midterm, and final marks")
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    st.subheader("Student results")
    display_columns = ["Student_ID", "Student_Name", "Department", "Year"] + MARK_COLUMNS + ["Average_Marks", "Result", "At_Risk"]
    st.dataframe(view[display_columns].sort_values(["Result", "Average_Marks"]), use_container_width=True)
    st.caption("At risk means a fail or an average less than 10 marks above the selected cutoff.")

    csv_bytes = view[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button("Download filtered results (CSV)", csv_bytes, "student_performance_results.csv", "text/csv")
    report = io.StringIO()
    report.write("Student Performance & Pass/Fail Analysis\n")
    report.write(f"Assumed rule: each of the three assessment marks must be >= {cutoff}.\n")
    report.write(f"Rows in current view: {total}; Pass: {pass_count}; Fail: {fail_count}.\n")
    report.write(f"Mean assessment average in view: {view['Average_Marks'].mean():.2f}\n" if total else "No rows match the selected filters.\n")
    report.write("This is an estimated result, not an official institutional result.\n")
    st.download_button("Download short report (TXT)", report.getvalue(), "student_performance_report.txt", "text/plain")

    with st.expander("Data checks and limitations"):
        st.write(f"Rows loaded: {len(data)}. Missing attendance values: {data['Attendance'].isna().sum()}. Missing study-hours values: {data['Study_Hours'].isna().sum()}.")
        st.write(f"Repeated Student_ID values: {data['Student_ID'].duplicated().sum()}. Rows are retained because the dataset does not explain whether repeats are duplicate records or separate observations.")
        st.write("Attendance, study hours, dates, and scholarship are not used to decide pass/fail. No causal or predictive claim is made. Average marks are descriptive only; pass/fail uses all three assessment cutoffs.")
        st.write("The supplied CSV has no official pass threshold, subject-level marks, maximum-mark metadata, or semester identifier. Confirm the assessment policy before treating results as official.")


if __name__ == "__main__":
    main()
