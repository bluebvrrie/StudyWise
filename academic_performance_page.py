import streamlit as st
import pandas as pd
from pathlib import Path

# This page focuses on grades and CGPA ranges.
st.set_page_config(page_title="Academic Performance", page_icon="🎓", layout="wide")

st.title("🎓 Academic Performance & CGPA Analysis")
st.write("A closer look at grade patterns and student-reported CGPA ranges.")
st.caption(
    "This dataset contains CGPA bands, not exact CGPA values, semester marks, or credits. "
    "Expected CGPA is the student's reported range, not a prediction."
)

# Read the CSV beside this app, or let the presenter upload another one.
uploaded_file = st.sidebar.file_uploader("Upload an academic CSV", type=["csv"])
local_file = Path(__file__).with_name("academic_performance_cleaned.csv")

try:
    if uploaded_file is not None:
        data = pd.read_csv(uploaded_file)
        st.sidebar.success("Using uploaded CSV")
    elif local_file.exists():
        data = pd.read_csv(local_file)
        st.sidebar.info("Using the CSV saved beside this app")
    else:
        st.info("Upload the academic CSV from the sidebar to get started.")
        st.stop()
except Exception as error:
    st.error(f"I could not read that CSV: {error}")
    st.stop()

# Check that this file has the columns needed by the page.
needed_columns = [
    "Student_ID", "Course_ID", "Grade_Label",
    "Last_Semester_CGPA_Range", "Expected_Graduation_CGPA_Range"
]
missing_columns = [column for column in needed_columns if column not in data.columns]
if missing_columns:
    st.error("Missing columns: " + ", ".join(missing_columns))
    st.stop()

# Some copies of the CSV contain a damaged dash in the CGPA labels.
range_columns = ["Last_Semester_CGPA_Range", "Expected_Graduation_CGPA_Range"]
for column in range_columns:
    data[column] = (
        data[column]
        .astype("string")
        .str.replace("�", "-", regex=False)
        .str.replace("–", "-", regex=False)
    )

# This order also gives each CGPA band a simple position for comparison.
cgpa_order = [
    "Below 2.00", "2.00-2.49", "2.50-2.99", "3.00-3.49", "Above 3.49"
]

st.sidebar.header("Explore the records")
courses = sorted(data["Course_ID"].dropna().unique().tolist())
selected_courses = st.sidebar.multiselect("Course ID", courses, default=courses)

cgpa_bands = [band for band in cgpa_order if band in data["Last_Semester_CGPA_Range"].dropna().unique()]
selected_bands = st.sidebar.multiselect(
    "Last-semester CGPA band", cgpa_bands, default=cgpa_bands
)

filtered_data = data[
    data["Course_ID"].isin(selected_courses)
    & data["Last_Semester_CGPA_Range"].isin(selected_bands)
].copy()

if filtered_data.empty:
    st.warning("No records match these filters. Try selecting more courses or CGPA bands.")
    st.stop()

# Quick overview
st.subheader("Class at a glance")
first, second, third = st.columns(3)
first.metric("Student records", len(filtered_data))
second.metric("Different courses", filtered_data["Course_ID"].nunique())
third.metric("Grade labels", filtered_data["Grade_Label"].nunique())

# How many records report a higher expected CGPA band than their last-semester band?
band_position = {band: number for number, band in enumerate(cgpa_order)}
last_position = filtered_data["Last_Semester_CGPA_Range"].map(band_position)
expected_position = filtered_data["Expected_Graduation_CGPA_Range"].map(band_position)
known_ranges = last_position.notna() & expected_position.notna()
higher_expected = ((expected_position > last_position) & known_ranges).sum()
same_expected = ((expected_position == last_position) & known_ranges).sum()
lower_expected = ((expected_position < last_position) & known_ranges).sum()

up, same, down = st.columns(3)
up.metric("Expected range is higher", int(higher_expected))
same.metric("Expected range is the same", int(same_expected))
down.metric("Expected range is lower", int(lower_expected))
st.caption(
    "This compares two reported bands for each record. It does not measure actual improvement or predict a final CGPA."
)

st.divider()
left, right = st.columns(2)

with left:
    st.subheader("Grade pattern")
    grade_counts = filtered_data["Grade_Label"].value_counts().sort_index()
    st.bar_chart(grade_counts, color="#5479A5")
    st.caption("Number of records for each grade label.")

with right:
    st.subheader("CGPA range comparison")
    last_counts = filtered_data["Last_Semester_CGPA_Range"].value_counts().to_dict()
    expected_counts = filtered_data["Expected_Graduation_CGPA_Range"].value_counts().to_dict()
    range_counts = pd.DataFrame({
        "Last semester": [last_counts.get(band, 0) for band in cgpa_order],
        "Expected at graduation": [expected_counts.get(band, 0) for band in cgpa_order],
    }, index=cgpa_order)
    st.bar_chart(range_counts, color=["#E5A34D", "#5E9B84"])
    st.caption("Each bar shows the number of student records in a reported CGPA band.")

# The comparison table lets the presenter show the movement between bands.
st.subheader("CGPA band movement")
last_ranges = filtered_data["Last_Semester_CGPA_Range"]
expected_ranges = filtered_data["Expected_Graduation_CGPA_Range"]
transition_values = {}
for last_band in cgpa_order:
    transition_values[last_band] = {}
    for expected_band in cgpa_order:
        matches = (last_ranges == last_band) & (expected_ranges == expected_band)
        transition_values[last_band][expected_band] = int(matches.sum())
transition = pd.DataFrame.from_dict(transition_values, orient="index")
st.dataframe(transition, use_container_width=True)
st.caption("Rows are last-semester bands; columns are expected graduation bands.")

st.divider()
st.subheader("✨ Expected CGPA range explorer")
target_band = st.selectbox(
    "Choose an expected graduation CGPA band",
    cgpa_order,
    index=2,
    help="This finds records whose expected range is at or above the selected band."
)
target_position = band_position[target_band]
reaches_target = expected_position.ge(target_position) & known_ranges
count_at_target = int(reaches_target.sum())
st.success(
    f"{count_at_target} of {len(filtered_data)} records have an expected CGPA range "
    f"of **{target_band}** or higher."
)
st.caption("This is a count of reported expectations, not a grade-target recommendation.")

# A record spotlight adds an interactive detail for a live presentation.
st.subheader("🔎 Student record spotlight")
st.write("Choose a record to view its grade and CGPA bands.")
record_ids = filtered_data["Student_ID"].astype(str).tolist()
selected_student = st.selectbox("Student ID", record_ids)
student = filtered_data[filtered_data["Student_ID"].astype(str) == selected_student].iloc[0]
a, b, c = st.columns(3)
a.write(f"**Course ID:** {student['Course_ID']}")
b.write(f"**Grade:** {student['Grade_Label']}")
c.write(f"**Last-semester band:** {student['Last_Semester_CGPA_Range']}")
st.info(f"Expected graduation band: **{student['Expected_Graduation_CGPA_Range']}**")

with st.expander("View and download filtered records"):
    display_columns = [
        "Student_ID", "Course_ID", "Grade_Label",
        "Last_Semester_CGPA_Range", "Expected_Graduation_CGPA_Range"
    ]
    st.dataframe(filtered_data[display_columns], use_container_width=True, hide_index=True)
    csv_file = filtered_data[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button(
        "Download these records as CSV",
        data=csv_file,
        file_name="filtered_academic_performance.csv",
        mime="text/csv"
    )





