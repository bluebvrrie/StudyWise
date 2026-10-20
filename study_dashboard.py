
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Make the classes folder available to Python
PROJECT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_DIR))

from classes.study_record_manager import StudyRecordManager


# Configure the webpage
st.set_page_config(
    page_title="StudyWise Dashboard",
    page_icon="📚",
    layout="wide",
)

# Page heading
st.title("📚 StudyWise")
st.subheader("Your Personalized Study Dashboard")
st.write(
    "Understand your academic performance and discover "
    "which subjects need more attention."
)

st.divider()

# Load the records through our manager class
try:
    manager = StudyRecordManager()
    df = manager.get_records()
except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not load study records: {error}")
    st.stop()

# Handle an empty CSV
if df.empty:
    st.info(
        "No study records found yet. Add records to "
        "study_records.csv to populate your dashboard."
    )
    st.stop()

# Sidebar filters
st.sidebar.header("Dashboard Filters")

subjects = sorted(df["Subject"].dropna().unique().tolist())

selected_subjects = st.sidebar.multiselect(
    "Select subjects",
    options=subjects,
    default=subjects,
)

filtered_df = df[df["Subject"].isin(selected_subjects)].copy()

if filtered_df.empty:
    st.warning("No records match your selected filters.")
    st.stop()

# Calculate statistics from the filtered records
marks = filtered_df["Previous_Marks"].dropna()
hours = filtered_df["Study_Hours"].dropna()

gaps = (
    filtered_df["Target_Marks"]
    - filtered_df["Previous_Marks"]
).clip(lower=0).dropna()

mean_marks = marks.mean() if not marks.empty else None
mean_hours = hours.mean() if not hours.empty else None
mean_gap = gaps.mean() if not gaps.empty else None

below_target = int(
    (
        filtered_df["Previous_Marks"]
        < filtered_df["Target_Marks"]
    ).fillna(False).sum()
)

# Display the four KPI cards
col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Average Marks",
    f"{mean_marks:.1f}/100" if mean_marks is not None else "N/A",
)

col2.metric(
    "Average Study Hours",
    f"{mean_hours:.2f} h" if mean_hours is not None else "N/A",
)

col3.metric(
    "Average Marks Gap",
    f"{mean_gap:.1f}" if mean_gap is not None else "N/A",
)

col4.metric(
    "Subjects Needing Attention",
    below_target,
)

st.divider()

# Additional statistics
st.subheader("Performance Overview")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Highest Marks",
    f"{marks.max():.1f}" if not marks.empty else "N/A",
)

col2.metric(
    "Lowest Marks",
    f"{marks.min():.1f}" if not marks.empty else "N/A",
)

col3.metric(
    "Records Analyzed",
    len(filtered_df),
)

# Show the underlying data
st.subheader("Your Study Records")

st.dataframe(
    filtered_df,
    use_container_width=True,
    hide_index=True,
)


# Show data quality information
st.subheader("Data Quality")

missing_values = filtered_df.isna().sum()
missing_values = missing_values[missing_values > 0]

required_columns = [
    "Record_ID",
    "Student_ID",
    "Subject",
    "Previous_Marks",
    "Target_Marks",
    "Difficulty",
    "Study_Hours",
    "Exam_Days_Left",
]

# Count blank text values as missing too
blank_counts = {}

for col in ["Record_ID", "Student_ID", "Subject"]:
    blank_counts[col] = (
        filtered_df[col].isna()
        | filtered_df[col].astype(str).str.strip().eq("")
    ).sum()

# Count missing or invalid numeric values
invalid_counts = {}

for col in [
    "Previous_Marks",
    "Target_Marks",
    "Difficulty",
    "Study_Hours",
    "Exam_Days_Left",
]:
    numeric_values = pd.to_numeric(
        filtered_df[col], errors="coerce"
    )

    invalid_counts[col] = int(numeric_values.isna().sum())

quality_rows = []

for col in required_columns:
    missing_count = int(missing_values.get(col, 0))

    if col in blank_counts:
        missing_count = int(blank_counts[col])

    if col in invalid_counts:
        missing_count = invalid_counts[col]

    if missing_count > 0:
        quality_rows.append({
            "Column": col,
            "Missing or invalid values": missing_count,
        })

if quality_rows:
    st.warning("Some records need attention.")

    st.dataframe(
        pd.DataFrame(quality_rows),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.success("No missing required values found in the selected records.")

st.caption(
    "Missing marks and study hours are excluded from their respective "
    "averages. Invalid records should be corrected before use."
)


# Grade Target Calculator
st.divider()
st.header("🎯 Grade Target Calculator")

st.write(
    "Select a subject, choose your target grade, "
    "and calculate the marks gap."
)

available_subjects = sorted(
    df["Subject"].dropna().unique().tolist()
)

if available_subjects:
    selected_subject = st.selectbox(
        "Choose a subject",
        available_subjects,
        key="grade_subject",
    )

    subject_row = df[df["Subject"] == selected_subject].iloc[0]

    default_current = float(subject_row["Previous_Marks"])
    default_target = float(subject_row["Target_Marks"])

    current_marks = st.number_input(
        "Current marks",
        min_value=0.0,
        max_value=100.0,
        value=default_current,
        step=1.0,
        key="grade_current",
    )

    target_grade = st.selectbox(
        "Target grade",
        ["Pass", "B", "A", "A+"],
        index=2,
        key="grade_label",
    )

    target_marks = st.number_input(
        "Minimum marks required for this grade",
        min_value=0.0,
        max_value=100.0,
        value=default_target,
        step=1.0,
        key="grade_threshold",
        help="Enter the official threshold used by your institution.",
    )

    marks_gap = max(0, target_marks - current_marks)

    if marks_gap == 0:
        st.success(
            f"Target reached! Your score meets the "
            f"configured threshold for {target_grade}."
        )
    else:
        st.warning(
            f"You need {marks_gap:g} more marks to reach "
            f"the configured {target_grade} threshold."
        )

    col1, col2, col3 = st.columns(3)

    col1.metric("Current Marks", f"{current_marks:g}/100")
    col2.metric("Target Marks", f"{target_marks:g}/100")
    col3.metric("Marks Gap", f"{marks_gap:g}")



# Personalized Study Planner
st.divider()
st.header("📅 Personalized Study Planner")

st.write(
    "Prioritize your subjects and distribute your daily "
    "study time according to marks gap, difficulty, and exam urgency."
)

available_hours = st.number_input(
    "How many hours can you study per day?",
    min_value=0.0,
    max_value=24.0,
    value=5.0,
    step=0.5,
    key="available_daily_hours",
)

if st.button("Calculate Study Plan"):
    try:
        planner = StudyRecordManager()
        plan = planner.allocate_study_time(available_hours)

        if plan.empty:
            st.info("Add subject records to generate a study plan.")
        elif available_hours == 0:
            st.info("Enter a positive number of available study hours.")
        else:
            plan = plan.sort_values(
                "Priority", ascending=False
            ).reset_index(drop=True)

            plan.index = plan.index + 1
            plan.index.name = "Priority Rank"

            st.subheader("Your Recommended Study Plan")

            display_plan = plan.rename(
                columns={
                    "Record_ID": "Record ID",
                    "Subject": "Subject",
                    "Priority": "Priority Score",
                    "Recommended_Hours": "Recommended Hours",
                }
            )

            st.dataframe(
                display_plan.style.format({
                    "Priority Score": "{:.3f}",
                    "Recommended Hours": "{:.2f}",
                }),
                use_container_width=True,
            )

            total_hours = plan["Recommended_Hours"].sum()

            st.metric(
                "Total Recommended Hours",
                f"{total_hours:.2f} h",
            )

            st.progress(
                min(total_hours / available_hours, 1.0)
            )

            st.subheader("Why these subjects need attention")

            for _, row in plan.iterrows():
                st.write(
                    f"**{row['Subject']}** — Priority score: "
                    f"{row['Priority']:.3f}. "
                    f"Recommended study time: "
                    f"{row['Recommended_Hours']:.2f} hours."
                )

    except (ValueError, OSError) as error:
        st.error(f"Could not generate study plan: {error}")



# Analysis and Charts
st.divider()
st.header("📊 Analysis & Charts")

# Chart 1: Previous Marks vs Target Marks
st.subheader("Previous Marks vs Target Marks")

chart_data = filtered_df[
    ["Subject", "Previous_Marks", "Target_Marks"]
].copy()

chart_data = chart_data.melt(
    id_vars="Subject",
    value_vars=["Previous_Marks", "Target_Marks"],
    var_name="Mark Type",
    value_name="Marks",
)

chart_data["Mark Type"] = chart_data["Mark Type"].replace({
    "Previous_Marks": "Previous Marks",
    "Target_Marks": "Target Marks",
})

import plotly.express as px

fig_marks = px.bar(
    chart_data,
    x="Subject",
    y="Marks",
    color="Mark Type",
    barmode="group",
    title="Compare Current Scores with Target Scores",
    labels={"Marks": "Marks out of 100"},
)

fig_marks.update_layout(
    yaxis_range=[0, 100],
    legend_title_text="",
)

st.plotly_chart(fig_marks, use_container_width=True)

# Chart 2: Recommended Study Hours
st.subheader("Recommended Daily Study Hours")

try:
    chart_manager = StudyRecordManager()
    study_plan = chart_manager.allocate_study_time(
        available_hours
    )

    if not study_plan.empty:
        fig_hours = px.bar(
            study_plan,
            x="Subject",
            y="Recommended_Hours",
            color="Subject",
            title="Recommended Time per Subject",
            labels={
                "Recommended_Hours": "Hours per day",
            },
        )

        st.plotly_chart(
            fig_hours,
            use_container_width=True,
        )
    else:
        st.info("Add study records to display study-hour recommendations.")

except (ValueError, OSError) as error:
    st.error(f"Could not create study-hours chart: {error}")



# ==========================================
# STEP 7: RECORD MANAGEMENT (CRUD)
# ==========================================

st.divider()
st.header("🗂️ Study Record Management")

st.write(
    "Add new subject records, search existing records, "
    "edit information, or delete records."
)

# Always load the latest saved data for this section.
try:
    crud_manager = StudyRecordManager()
    crud_df = crud_manager.get_records()

except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not load records: {error}")
    st.stop()

create_tab, read_tab, update_tab, delete_tab = st.tabs(
    ["➕ Create", "🔍 Read", "✏️ Update", "🗑️ Delete"]
)


# ------------------------------------------
# C: CREATE A NEW RECORD
# ------------------------------------------
with create_tab:
    st.subheader("Add a Subject")

    with st.form("create_record_form", clear_on_submit=True):
        new_id = st.text_input("Record ID", placeholder="R004")
        new_student_id = st.text_input(
            "Student ID", value="S001"
        )
        new_subject = st.text_input("Subject Name")

        col1, col2 = st.columns(2)

        with col1:
            new_previous = st.number_input(
                "Previous Marks",
                min_value=0.0,
                max_value=100.0,
                value=50.0,
                step=1.0,
            )
            new_target = st.number_input(
                "Target Marks",
                min_value=0.0,
                max_value=100.0,
                value=80.0,
                step=1.0,
            )
            new_difficulty = st.selectbox(
                "Difficulty (1–4)", [1, 2, 3, 4], index=1
            )

        with col2:
            new_hours = st.number_input(
                "Actual Study Hours per Day",
                min_value=0.0,
                max_value=24.0,
                value=1.0,
                step=0.5,
            )
            new_days = st.number_input(
                "Days Until Exam",
                min_value=0,
                max_value=3650,
                value=14,
                step=1,
            )
            new_grade = st.selectbox(
                "Target Grade",
                ["Pass", "B", "A", "A+", "Not specified"],
                index=2,
            )

        create_submitted = st.form_submit_button(
            "Add Record", type="primary"
        )

    if create_submitted:
        new_record = {
            "Record_ID": new_id.strip(),
            "Student_ID": new_student_id.strip(),
            "Subject": new_subject.strip(),
            "Previous_Marks": new_previous,
            "Target_Marks": new_target,
            "Difficulty": new_difficulty,
            "Study_Hours": new_hours,
            "Exam_Days_Left": new_days,
            "Target_Grade": (
                "" if new_grade == "Not specified" else new_grade
            ),
        }

        try:
            crud_manager.add_record(new_record)
            st.success("Record added successfully!")
            st.rerun()

        except (ValueError, OSError) as error:
            st.error(f"Could not add record: {error}")


# ------------------------------------------
# R: SEARCH AND VIEW RECORDS
# ------------------------------------------
with read_tab:
    st.subheader("View Your Records")

    search_text = st.text_input(
        "Search by subject, student ID, or record ID",
        key="crud_search",
    )

    read_df = crud_df.copy()

    if search_text.strip():
        searchable = (
            read_df[["Record_ID", "Student_ID", "Subject"]]
            .fillna("")
            .astype(str)
            .agg(" ".join, axis=1)
        )
        read_df = read_df[
            searchable.str.contains(
                search_text.strip(), case=False, regex=False
            )
        ]

    difficulty_filter = st.multiselect(
        "Filter by difficulty",
        options=[1, 2, 3, 4],
        default=[1, 2, 3, 4],
        key="crud_difficulty",
    )

    read_df = read_df[
        read_df["Difficulty"].isin(difficulty_filter)
    ]

    st.dataframe(
        read_df,
        use_container_width=True,
        hide_index=True,
    )

    st.caption(f"{len(read_df)} record(s) found.")


# ------------------------------------------
# U: UPDATE AN EXISTING RECORD
# ------------------------------------------
with update_tab:
    st.subheader("Edit a Subject Record")

    if crud_df.empty:
        st.info("There are no records to update.")

    else:
        update_ids = crud_df["Record_ID"].astype(str).tolist()

        selected_update_id = st.selectbox(
            "Select the record to edit",
            update_ids,
            key="update_record_id",
        )

        selected_row = crud_df[
            crud_df["Record_ID"].astype(str) == selected_update_id
        ].iloc[0]

        with st.form("update_record_form"):
            st.text_input(
                "Record ID (cannot be changed)",
                value=selected_update_id,
                disabled=True,
            )

            edit_student = st.text_input(
                "Student ID",
                value=str(selected_row["Student_ID"]),
            )

            edit_subject = st.text_input(
                "Subject",
                value=str(selected_row["Subject"]),
            )

            col1, col2 = st.columns(2)

            with col1:
                edit_previous = st.number_input(
                    "Previous Marks",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_row["Previous_Marks"]),
                    step=1.0,
                )

                edit_target = st.number_input(
                    "Target Marks",
                    min_value=0.0,
                    max_value=100.0,
                    value=float(selected_row["Target_Marks"]),
                    step=1.0,
                )

                edit_difficulty = st.selectbox(
                    "Difficulty",
                    [1, 2, 3, 4],
                    index=int(selected_row["Difficulty"]) - 1,
                )

            with col2:
                edit_hours = st.number_input(
                    "Study Hours per Day",
                    min_value=0.0,
                    max_value=24.0,
                    value=float(selected_row["Study_Hours"]),
                    step=0.5,
                )

                edit_days = st.number_input(
                    "Days Until Exam",
                    min_value=0,
                    max_value=3650,
                    value=int(selected_row["Exam_Days_Left"]),
                    step=1,
                )

                grade_options = [
                    "Not specified", "Pass", "B", "A", "A+"
                ]
                old_grade = selected_row["Target_Grade"]
                old_grade = (
                    "Not specified"
                    if pd.isna(old_grade) or str(old_grade).strip() == ""
                    else str(old_grade)
                )
                grade_index = (
                    grade_options.index(old_grade)
                    if old_grade in grade_options else 0
                )

                edit_grade = st.selectbox(
                    "Target Grade",
                    grade_options,
                    index=grade_index,
                )

            update_submitted = st.form_submit_button(
                "Save Changes", type="primary"
            )

        if update_submitted:
            changes = {
                "Student_ID": edit_student.strip(),
                "Subject": edit_subject.strip(),
                "Previous_Marks": edit_previous,
                "Target_Marks": edit_target,
                "Difficulty": edit_difficulty,
                "Study_Hours": edit_hours,
                "Exam_Days_Left": edit_days,
                "Target_Grade": (
                    "" if edit_grade == "Not specified" else edit_grade
                ),
            }

            try:
                crud_manager.update_record(
                    selected_update_id, changes
                )
                st.success("Record updated successfully!")
                st.rerun()

            except (ValueError, OSError) as error:
                st.error(f"Could not update record: {error}")


# ------------------------------------------
# D: DELETE AN EXISTING RECORD
# ------------------------------------------
with delete_tab:
    st.subheader("Delete a Subject Record")

    if crud_df.empty:
        st.info("There are no records to delete.")

    else:
        delete_ids = crud_df["Record_ID"].astype(str).tolist()

        selected_delete_id = st.selectbox(
            "Select the record to delete",
            delete_ids,
            key="delete_record_id",
        )

        selected_delete_row = crud_df[
            crud_df["Record_ID"].astype(str) == selected_delete_id
        ].iloc[0]

        st.warning(
            f"You selected **{selected_delete_row['Subject']}** "
            f"(Record ID: {selected_delete_id}). "
            "Deleting this record cannot be undone from this page."
        )

        st.dataframe(
            selected_delete_row.to_frame().rename(
                columns={selected_delete_row.name: "Value"}
            ),
            use_container_width=True,
        )

        confirm_delete = st.checkbox(
            "I confirm that I want to delete this record.",
            key="confirm_delete_record",
        )

        if st.button(
            "Delete Selected Record",
            type="primary",
            disabled=not confirm_delete,
        ):
            try:
                crud_manager.delete_record(selected_delete_id)
                st.success("Record deleted successfully!")
                st.rerun()

            except (ValueError, OSError) as error:
                st.error(f"Could not delete record: {error}")



# ==========================================
# STEP 9: REPORT EXPORT
# ==========================================

from datetime import datetime

st.divider()
st.header("📄 Report & Export")

st.write(
    "Generate a downloadable summary of your academic "
    "performance and personalized study recommendations."
)

# Refresh the records for the report
try:
    report_manager = StudyRecordManager()
    report_df = report_manager.get_records()

except (OSError, ValueError, pd.errors.ParserError) as error:
    st.error(f"Could not prepare the report: {error}")
    report_df = pd.DataFrame(columns=report_manager.COLUMNS)

if report_df.empty:
    st.info("Add study records before generating a report.")

else:
    # Allow report-specific filtering
    report_subjects = sorted(
        report_df["Subject"].dropna().unique().tolist()
    )

    selected_report_subjects = st.multiselect(
        "Subjects to include in the report",
        options=report_subjects,
        default=report_subjects,
        key="report_subject_filter",
    )

    report_data = report_df[
        report_df["Subject"].isin(selected_report_subjects)
    ].copy()

    # Report settings
    report_hours = st.number_input(
        "Available daily study hours for this report",
        min_value=0.0,
        max_value=24.0,
        value=5.0,
        step=0.5,
        key="report_daily_hours",
    )

    if report_data.empty:
        st.warning("Select at least one subject to generate a report.")

    else:
        # Calculate summary statistics from filtered records
        report_marks = report_data["Previous_Marks"].dropna()
        report_study_hours = report_data["Study_Hours"].dropna()

        report_gaps = (
            report_data["Target_Marks"]
            - report_data["Previous_Marks"]
        ).clip(lower=0).dropna()

        avg_marks = (
            report_marks.mean() if not report_marks.empty else None
        )
        avg_hours = (
            report_study_hours.mean()
            if not report_study_hours.empty else None
        )
        avg_gap = (
            report_gaps.mean() if not report_gaps.empty else None
        )

        # Calculate priority and study-time allocation
        try:
            report_plan = report_manager.allocate_study_time(
                report_hours
            )

            report_plan = report_plan[
                report_plan["Record_ID"].astype(str).isin(
                    report_data["Record_ID"].astype(str)
                )
            ].copy()

            # Reallocate only across the selected subjects
            priority_total = report_plan["Priority"].sum()

            if len(report_plan) > 0:
                if priority_total > 0:
                    report_plan["Recommended_Hours"] = (
                        report_hours
                        * report_plan["Priority"]
                        / priority_total
                    )
                else:
                    report_plan["Recommended_Hours"] = (
                        report_hours / len(report_plan)
                    )

                report_plan["Recommended_Hours"] = (
                    report_plan["Recommended_Hours"].round(2)
                )

                rounding_difference = round(
                    report_hours
                    - report_plan["Recommended_Hours"].sum(),
                    2,
                )

                if rounding_difference:
                    highest_priority_index = (
                        report_plan["Priority"].idxmax()
                    )
                    report_plan.loc[
                        highest_priority_index, "Recommended_Hours"
                    ] += rounding_difference

            # Largest marks gaps first
            largest_gaps = report_data.copy()
            largest_gaps["Marks_Gap"] = (
                largest_gaps["Target_Marks"]
                - largest_gaps["Previous_Marks"]
            ).clip(lower=0)

            largest_gaps = largest_gaps.sort_values(
                "Marks_Gap", ascending=False
            ).head(5)

            # Identify missing values and blank required text
            missing_warnings = []

            for column in report_data.columns:
                missing_count = int(report_data[column].isna().sum())

                if column in ["Record_ID", "Student_ID", "Subject"]:
                    blank_count = int(
                        report_data[column]
                        .fillna("")
                        .astype(str)
                        .str.strip()
                        .eq("")
                        .sum()
                    )
                    missing_count = max(missing_count, blank_count)

                if missing_count > 0:
                    missing_warnings.append(
                        f"{column}: {missing_count} missing value(s)"
                    )

            # Display report preview
            st.subheader("Report Preview")

            col1, col2, col3 = st.columns(3)

            col1.metric("Records Included", len(report_data))
            col2.metric(
                "Average Marks",
                f"{avg_marks:.2f}" if avg_marks is not None else "N/A",
            )
            col3.metric(
                "Average Marks Gap",
                f"{avg_gap:.2f}" if avg_gap is not None else "N/A",
            )

            st.write("**Largest performance gaps**")
            st.dataframe(
                largest_gaps[
                    ["Subject", "Previous_Marks", "Target_Marks", "Marks_Gap"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            st.write("**Recommended study allocation**")
            st.dataframe(
                report_plan[
                    ["Subject", "Priority", "Recommended_Hours"]
                ].sort_values("Priority", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

            # Construct the text report
            generated_at = datetime.now().astimezone().isoformat(
                timespec="seconds"
            )

            report_lines = [
                "STUDYWISE ACADEMIC REPORT",
                "=" * 35,
                f"Generated at: {generated_at}",
                f"Records included: {len(report_data)}",
                "Applied subject filters: "
                + ", ".join(selected_report_subjects),
                f"Available daily study hours: {report_hours:.2f}",
                "",
                "SUMMARY STATISTICS",
                "-" * 25,
                f"Average previous marks: {avg_marks if avg_marks is not None else 'N/A'}",
                f"Average actual study hours: {avg_hours if avg_hours is not None else 'N/A'}",
                f"Average performance gap: {avg_gap if avg_gap is not None else 'N/A'}",
                f"Highest marks: {report_marks.max() if not report_marks.empty else 'N/A'}",
                f"Lowest marks: {report_marks.min() if not report_marks.empty else 'N/A'}",
                "",
                "LARGEST PERFORMANCE GAPS",
                "-" * 25,
            ]

            for _, row in largest_gaps.iterrows():
                report_lines.append(
                    f"{row['Subject']}: {row['Marks_Gap']:.2f} marks"
                )

            report_lines.extend([
                "",
                "PRIORITY SCORES AND STUDY ALLOCATION",
                "-" * 35,
            ])

            for _, row in report_plan.iterrows():
                report_lines.append(
                    f"{row['Subject']}: priority={row['Priority']:.3f}, "
                    f"recommended={row['Recommended_Hours']:.2f} hours/day"
                )

            report_lines.extend([
                "",
                "DATA QUALITY WARNINGS",
                "-" * 25,
            ])

            if missing_warnings:
                report_lines.extend(missing_warnings)
            else:
                report_lines.append("No missing values detected.")

            report_lines.extend([
                "",
                "Note: Priority scores and study-time allocations are "
                "rule-based estimates, not guaranteed predictions."
            ])

            text_report = "\n".join(report_lines)

            st.download_button(
                label="📥 Download Academic Report (.txt)",
                data=text_report,
                file_name="studywise_academic_report.txt",
                mime="text/plain",
                key="download_text_report",
            )

            # Download filtered records as CSV
            csv_data = report_data.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="📥 Download Selected Records (.csv)",
                data=csv_data,
                file_name="studywise_records.csv",
                mime="text/csv",
                key="download_records_csv",
            )

        except (ValueError, OSError, KeyError) as error:
            st.error(f"Could not generate report: {error}")


st.caption(
    "Dashboard figures are calculated from your selected "
    "study records. Recommendations are estimates, not guarantees."
)
