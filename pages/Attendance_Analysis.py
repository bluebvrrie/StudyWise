"""
pages/Attendance_Analysis.py - the Attendance Analytics screen.

How this file is organised (top to bottom on screen):
  header -> filter panel -> metric cards -> navigation -> one section -> footer
Calculations live in attendance_analysis.py, CRUD in attendance_manager.py, the calculator in
attendance_calculator.py, charts in attendance_charts.py and the look in ui_style.py.
"""
import sys
from datetime import date, datetime, time
from pathlib import Path

import pandas as pd
import streamlit as st

# Make the project folder importable when Streamlit runs this page.
PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

import attendance_analysis as aa
import attendance_calculator as calc
import attendance_charts as charts
import clean_attendance
import ui_style
from attendance_manager import (CLEAN_CSV, DATE_FORMAT, AttendanceDataError, AttendanceManager,
                                record_label)

st.set_page_config(page_title="Attendance Analytics | EduTrack", page_icon="📅", layout="wide")
ui_style.apply_style()

THRESHOLD = aa.THRESHOLD      # replaced by the user's choice in the filter panel (default 75)
MAX_OPTIONS = 300             # keeps select boxes fast
SECTIONS = ["📊 Overview", "🎓 Students", "🗂️ Records", "🧮 Calculator", "📥 Reports"]
RECORD_MODES = ["View records", "Add record", "Edit record", "Delete record"]


# =============================================================== small helpers
def to_time(text, fallback):
    """'09:15' -> datetime.time (for st.time_input)."""
    try:
        return datetime.strptime(str(text), "%H:%M").time()
    except ValueError:
        return fallback


def flash_and_rerun(kind, message, reset_filters=False):
    """Show a message AFTER the page reloads, so tables and charts show the new data."""
    st.session_state["flash"] = (kind, message)
    if reset_filters:                       # so a record you just added is not hidden by a filter
        st.session_state["_reset"] = True
    st.rerun()


def request_reset():
    st.session_state["_reset"] = True


def reset_filters(min_day, max_day):
    """Put every filter back to its default (runs BEFORE the filter widgets are drawn)."""
    state = st.session_state
    state["f_search"] = ""
    state["f_sem"] = []
    state["f_sub"] = []
    state["f_status"] = "All"
    state["f_late"] = "All"
    state["f_exam"] = "All"
    state["f_date"] = (min_day, max_day)
    state["f_sort"] = "Student ID"
    state["f_order"] = "Ascending"
    state["f_thr"] = 75


def show_chart(container, fig, empty_message):
    """Draw a chart, or show a message if there is not enough data.
    (Written as a normal if/else on purpose: a bare 'a if x else b' line makes Streamlit
    print the returned object on the page.)"""
    if fig is not None:
        container.pyplot(fig)
    else:
        container.info(empty_message)


def show_table(df, height=380):
    st.dataframe(df, hide_index=True, width="stretch", height=height)


def record_details(row):
    details = row.copy()
    details["date"] = row["date"].strftime(DATE_FORMAT)
    return pd.DataFrame({"Field": details.index, "Value": details.astype(str).values})


def pick_record(data, key):
    """Let the user look up ONE record. Returns the chosen row or None."""
    c1, c2, c3 = st.columns(3)
    student = c1.text_input("Student ID", key=f"{key}_student", placeholder="e.g. ST1411")
    day = c2.date_input("Date (optional)", value=None, key=f"{key}_date", format="YYYY-MM-DD")
    code = c3.text_input("Subject code (optional)", key=f"{key}_code", placeholder="e.g. DS301")
    if not student.strip():
        st.info("Type a student ID to find that student's records.")
        return None
    found = aa.apply_filters(data, student_search=student, start_date=day, end_date=day)
    if code.strip():
        found = found[found["subject_code"].str.contains(code.strip(), case=False, regex=False)]
    exact = found[found["student_id"].str.upper() == student.strip().upper()]
    found = exact if len(exact) else found          # prefer the exact ID (ST1 should not list ST1000...)
    if found.empty:
        st.warning("No record matches that search.")
        return None
    found = found.sort_values(["date", "record_id"], ascending=False)
    if len(found) > MAX_OPTIONS:
        st.caption(f"{len(found)} matches - showing the newest {MAX_OPTIONS}. Add a date or subject to narrow down.")
        found = found.head(MAX_OPTIONS)
    labels = {record_label(row): row["record_id"] for _, row in found.iterrows()}
    choice = st.selectbox(f"Select a record ({len(labels)} found)", list(labels), key=f"{key}_choice")
    return AttendanceManager.get_record(data, labels[choice])


def record_form(prefix, d, button_text):
    """Shared form body for Add and Edit. Returns (submitted, data_dict)."""
    ui_style.small_label("Student and class")
    c1, c2, c3 = st.columns(3)
    student_id = c1.text_input("Student ID *", value=d["student_id"], key=f"{prefix}_sid")
    semester = c2.selectbox("Semester *", list(range(1, 13)), index=int(d["semester"]) - 1, key=f"{prefix}_sem")
    class_date = c3.date_input("Date *", value=d["date"], max_value=date.today(), key=f"{prefix}_date", format="YYYY-MM-DD")
    c1, c2, c3 = st.columns(3)
    code = c1.text_input("Subject code *", value=d["subject_code"], key=f"{prefix}_code")
    name = c2.text_input("Subject name *", value=d["subject_name"], key=f"{prefix}_name")
    faculty = c3.text_input("Faculty ID *", value=d["faculty_id"], key=f"{prefix}_fac")
    c1, c2, c3 = st.columns(3)
    start = c1.time_input("Class start *", value=d["class_start_time"], key=f"{prefix}_start")
    end = c2.time_input("Class end *", value=d["class_end_time"], key=f"{prefix}_end")
    remarks = c3.text_input("Remarks (optional)", value=d["remarks"], key=f"{prefix}_remarks")
    ui_style.small_label("Attendance")
    c1, c2, c3, c4, c5 = st.columns(5)
    status = c1.selectbox("Status *", ["Present", "Absent"], index=0 if d["status"] == 1 else 1, key=f"{prefix}_status")
    time_in = c2.time_input("Time in", value=d["time_in"], key=f"{prefix}_in", help="Used only when Present")
    time_out = c3.time_input("Time out", value=d["time_out"], key=f"{prefix}_out", help="Used only when Present")
    late = c4.checkbox("Late entry", value=bool(d["late_entry"]), key=f"{prefix}_late")
    exam = c5.checkbox("Exam week", value=bool(d["is_exam_week"]), key=f"{prefix}_exam")
    submitted = st.form_submit_button(button_text, type="primary")
    absent = status == "Absent"
    data = {
        "student_id": student_id, "semester": semester, "subject_code": code, "subject_name": name,
        "faculty_id": faculty, "date": class_date, "class_start_time": start, "class_end_time": end,
        "time_in": None if absent else time_in, "time_out": None if absent else time_out,
        "status": 0 if absent else 1, "late_entry": int(late), "is_exam_week": int(exam), "remarks": remarks,
    }
    return submitted, data


def defaults_from_record(row):
    start = to_time(row["class_start_time"], time(9, 0))
    end = to_time(row["class_end_time"], time(10, 0))
    return {
        "student_id": row["student_id"], "semester": int(row["semester"]), "date": row["date"].date(),
        "subject_code": row["subject_code"], "subject_name": row["subject_name"], "faculty_id": row["faculty_id"],
        "class_start_time": start, "class_end_time": end,
        "time_in": to_time(row["time_in"], start), "time_out": to_time(row["time_out"], end),
        "status": int(row["status"]), "late_entry": int(row["late_entry"]),
        "is_exam_week": int(row["is_exam_week"]), "remarks": "" if pd.isna(row["remarks"]) else row["remarks"],
    }


def show_messages(ok, message, warnings):
    for w in warnings:
        st.warning(w)
    if not ok:
        st.error(message)


# =============================================================== sections
def section_overview(filtered, m):
    insights = aa.key_insights(filtered, THRESHOLD)
    if insights:
        ui_style.insight_chips(insights)

    subject_table = aa.group_summary(filtered, ["subject_code", "subject_name"])
    subject_table["label"] = subject_table["subject_code"] + " " + subject_table["subject_name"]
    semester_table = aa.group_summary(filtered, "semester")
    semester_table["label"] = "Semester " + semester_table["semester"].astype(str)

    left, right = st.columns([3, 2])
    with left.container(border=True):
        show_chart(st, charts.bar_attendance(subject_table, "label", "Attendance by subject", "Subject", THRESHOLD),
                   "No subject data to chart.")
    with right.container(border=True):
        show_chart(st, charts.pie_present_absent(m["present"], m["absent"]), "No data for the donut chart.")

    left, right = st.columns([3, 2])
    with left.container(border=True):
        frequency = st.radio("Trend period", ["Monthly", "Weekly"], horizontal=True, key="trend_freq")
        trend = aa.trend_summary(filtered, frequency)
        show_chart(st, charts.line_trend(trend, frequency, THRESHOLD),
                   "A trend line needs records from at least two different periods.")
    with right.container(border=True):
        show_chart(st, charts.bar_attendance(semester_table, "label", "Attendance by semester", "Semester", THRESHOLD),
                   "No semester data to chart.")

    left, right = st.columns(2)
    late = aa.late_summary(filtered)
    with left.container(border=True):
        ui_style.section_header("Late entries", f"{late['late']:,} of {late['present_records']:,} present records "
                                f"({late['late_pct_of_present']}%)" + (f" · average {late['avg_minutes_late']} min late"
                                                                       if late["avg_minutes_late"] is not None else ""))
        show_chart(st, charts.hist_minutes_late(aa.minutes_late(filtered)), "No late entries in the current selection.")
    with right.container(border=True):
        exam = aa.exam_summary(filtered)
        exam["label"] = exam["period_type"]
        show_chart(st, charts.bar_attendance(exam, "label", "Exam week vs regular week", "Period type", THRESHOLD),
                   "No exam-week data in the current selection.")


def section_students(filtered):
    students = aa.student_summary(filtered)
    s = aa.numeric_stats(filtered)
    with st.container(border=True):
        ui_style.section_header("Summary statistics", f"Student attendance % across {s['students_counted']:,} student(s), "
                                "calculated with NumPy.")
        cols = st.columns(5)
        cols[0].metric("Mean", f"{s['mean_pct']}%")
        cols[1].metric("Median", f"{s['median_pct']}%")
        cols[2].metric("Lowest", f"{s['min_pct']}%")
        cols[3].metric("Highest", f"{s['max_pct']}%")
        cols[4].metric("Std deviation", "n/a" if s["std_pct"] is None else f"{s['std_pct']}")
        st.caption("Mean = average, median = middle value, std deviation = how spread out students are (sample formula). "
                   "Students with very few recorded classes can have extreme percentages.")

    left, right = st.columns([3, 2])
    with left.container(border=True):
        show_chart(st, charts.hist_student_pct(students["attendance_pct"].to_numpy(), THRESHOLD),
                   "No student data to chart.")
    with right.container(border=True):
        ui_style.section_header("Highest and lowest")
        low = students.head(5)[["student_id", "attendance_pct"]].rename(columns={"student_id": "Lowest 5", "attendance_pct": "%"})
        high = (students.sort_values(["attendance_pct", "student_id"], ascending=[False, True]).head(5)
                [["student_id", "attendance_pct"]].rename(columns={"student_id": "Highest 5", "attendance_pct": "%"}))
        a, b = st.columns(2)
        a.dataframe(low, hide_index=True, width="stretch")
        b.dataframe(high, hide_index=True, width="stretch")

    with st.container(border=True):
        ui_style.section_header("Student-wise attendance", "Each row is one student (not one class record).")
        below = students[students["attendance_pct"] < THRESHOLD]
        ok = students[students["attendance_pct"] >= THRESHOLD]
        t1, t2, t3 = st.tabs([f"All ({len(students)})", f"Below {THRESHOLD:g}% ({len(below)})",
                              f"{THRESHOLD:g}% or above ({len(ok)})"])
        names = {"student_id": "Student", "semester": "Sem", "classes_recorded": "Classes", "classes_attended": "Attended",
                 "attendance_pct": "Attendance %", "meets_threshold": "Meets"}
        for tab, table in [(t1, students), (t2, below), (t3, ok)]:
            with tab:
                show_table(table.drop(columns=["meets_threshold"], errors="ignore").rename(columns=names), height=300)


def section_records(manager, data, filtered):
    mode = st.segmented_control("Action", RECORD_MODES, default=RECORD_MODES[0], key="records_mode",
                                label_visibility="collapsed") or RECORD_MODES[0]
    nonce = st.session_state.setdefault("form_nonce", 0)

    if mode == "View records":
        with st.container(border=True):
            ui_style.section_header("Attendance records", f"{len(filtered):,} record(s) match the current filters.")
            if filtered.empty:
                st.warning("No records match the current filters.")
                return
            show_table(aa.display_table(filtered), height=420)
            with st.expander("Inspect one record"):
                options = filtered.head(MAX_OPTIONS)
                labels = {record_label(row): row["record_id"] for _, row in options.iterrows()}
                if len(filtered) > MAX_OPTIONS:
                    st.caption(f"Listing the first {MAX_OPTIONS} matches - narrow the filters to find others.")
                choice = st.selectbox("Choose a record", list(labels), key="inspect_choice")
                row = AttendanceManager.get_record(filtered, labels[choice])
                if row is not None:
                    show_table(record_details(row), height=300)

    elif mode == "Add record":
        with st.container(border=True):
            ui_style.section_header("Add a new attendance record",
                                    "Fill in the form and press Save. Nothing is saved until you submit.")
            subjects = data[["subject_code", "subject_name", "faculty_id"]].dropna().drop_duplicates("subject_code")
            lookup = {f"{r.subject_code} – {r.subject_name}": r for r in subjects.itertuples()}
            choice = st.selectbox("Subject (pre-fills the form below)", ["➕ New subject"] + list(lookup), key="create_subject")
            picked = lookup.get(choice)
            defaults = {
                "student_id": "", "semester": 1, "date": date.today(),
                "subject_code": picked.subject_code if picked else "", "subject_name": picked.subject_name if picked else "",
                "faculty_id": picked.faculty_id if picked else "",
                "class_start_time": time(9, 0), "class_end_time": time(10, 0), "time_in": time(9, 0), "time_out": time(10, 0),
                "status": 1, "late_entry": 0, "is_exam_week": 0, "remarks": "",
            }
            prefix = f"create_{choice}_{nonce}"
            with st.form(prefix, border=False):
                submitted, record = record_form(prefix, defaults, "Save new record")
            if submitted:
                ok, message, warnings = manager.add_record(record)
                if ok:
                    st.session_state["form_nonce"] = nonce + 1
                    flash_and_rerun("success", message + ("\n\n" + "\n".join(warnings) if warnings else ""), reset_filters=True)
                show_messages(ok, message, warnings)

    elif mode == "Edit record":
        with st.container(border=True):
            ui_style.section_header("Edit a record", "Find the record, change the values, then press Save changes.")
            row = pick_record(data, "upd")
            if row is not None:
                st.caption(f"Editing record {row['record_id']}. Only this record will change.")
                prefix = f"upd_{row['record_id']}_{nonce}"
                with st.form(prefix, border=False):
                    submitted, record = record_form(prefix, defaults_from_record(row), "Save changes")
                if submitted:
                    ok, message, warnings = manager.update_record(row["record_id"], record)
                    if ok:
                        st.session_state["form_nonce"] = nonce + 1
                        flash_and_rerun("success", message + ("\n\n" + "\n".join(warnings) if warnings else ""))
                    show_messages(ok, message, warnings)

    else:
        with st.container(border=True):
            ui_style.section_header("Delete a record", "This permanently removes ONE record from the working CSV "
                                    "(the original raw file is never touched).")
            row = pick_record(data, "del")
            if row is not None:
                st.warning(f"You are about to delete record {row['record_id']}:")
                show_table(record_details(row), height=300)
                confirm = st.checkbox(f"Yes, permanently delete record {row['record_id']}", key=f"del_confirm_{row['record_id']}")
                if st.button("Delete record", type="primary", disabled=not confirm):
                    ok, message = manager.delete_record(row["record_id"])
                    if ok:
                        flash_and_rerun("success", message)
                    st.error(message)


def section_calculator(data):
    with st.container(border=True):
        ui_style.section_header("75% Attendance Calculator",
                                "Find out how many additional classes you can miss while maintaining your required attendance.")
        c1, c2, c3 = st.columns(3)
        attended = c1.number_input("Classes attended", min_value=0, step=1, value=0)
        total = c2.number_input("Total classes conducted", min_value=0, step=1, value=0)
        required = c3.number_input("Required attendance (%)", min_value=1.0, max_value=100.0, step=1.0, value=75.0)

        if total == 0:
            st.info("Enter the total number of classes conducted to see your result.")
        else:
            errors = calc.validate_inputs(attended, total, required)
            for e in errors:
                st.error(e)
            if not errors:
                r = calc.calculate(attended, total, required)
                tiles = [("Current attendance", f"{r['current_pct']:.2f}%"), ("Required", f"{required:g}%")]
                if r["meets"] and r["can_miss"] > 0:
                    tiles.append(("Classes you can still miss", str(r["can_miss"])))
                    ui_style.result_panel("green", "You are above the requirement",
                        f"After missing {r['can_miss']} more class(es) you would have {attended}/{total + r['can_miss']} = "
                        f"{r['pct_after_missing']:.2f}% (still OK). Missing one more would drop you to "
                        f"{r['pct_if_one_more_missed']:.2f}%.", tiles, r["current_pct"], required)
                elif r["meets"]:
                    tiles.append(("Classes you can still miss", "0"))
                    ui_style.result_panel("amber", "You are exactly on the edge",
                        f"You meet {required:g}% but cannot miss any more classes: one more absence would drop you to "
                        f"{r['pct_if_one_more_missed']:.2f}%.", tiles, r["current_pct"], required)
                elif r["recovery_possible"]:
                    tiles.append(("Classes to attend in a row", str(r["need_to_attend"])))
                    ui_style.result_panel("red", "You are below the requirement",
                        f"Attend the next {r['need_to_attend']} class(es) without missing any to reach "
                        f"{r['pct_after_recovery']:.2f}% ({attended + r['need_to_attend']}/{total + r['need_to_attend']}).",
                        tiles, r["current_pct"], required)
                else:
                    ui_style.result_panel("red", "Requirement cannot be reached",
                        "You are below 100% and the requirement is 100%, so it cannot be reached again.",
                        tiles, r["current_pct"], required)
                st.caption("Rule: attended ÷ (total + missed) must stay at or above the required %. "
                           "Exact fractions are used, so boundary cases such as 75/100 are correct.")

        with st.expander("Look up a student's numbers from the dataset (optional)"):
            sid = st.text_input("Student ID", key="calc_lookup", placeholder="e.g. ST1411")
            if sid.strip():
                mine = data[data["student_id"].str.upper() == sid.strip().upper()]
                if mine.empty:
                    st.warning("Student ID not found.")
                else:
                    s = aa.student_summary(mine).iloc[0]
                    st.write(f"{sid.strip().upper()} attended **{s['classes_attended']}** of **{s['classes_recorded']}** "
                             "recorded classes. Type these into the boxes above.")


def section_reports(filtered, total_in_file, filters):
    now = datetime.now()
    report = aa.build_report(filtered, total_in_file, filters, THRESHOLD, generated_at=now)
    stamp = now.strftime("%Y%m%d_%H%M%S")
    with st.container(border=True):
        ui_style.section_header("Reports and downloads", "Both downloads use the current filters. "
                                f"Report generated at {now.strftime('%Y-%m-%d %H:%M:%S')} (local time).")
        c1, c2 = st.columns(2)
        with c1.container(border=True):
            st.markdown("**Summary report (.txt)**")
            st.caption("Counts, active filters, overall %, students below the threshold, subject and semester tables.")
            st.download_button("Download summary report", report, file_name=f"edutrack_attendance_report_{stamp}.txt",
                               mime="text/plain", type="primary")
        with c2.container(border=True):
            st.markdown("**Filtered records (.csv)**")
            st.caption(f"{len(filtered):,} record(s) that match the filters.")
            export = filtered.copy()
            export["date"] = export["date"].dt.strftime(DATE_FORMAT)
            st.download_button("Download filtered records", export.to_csv(index=False),
                               file_name=f"edutrack_attendance_records_{stamp}.csv", mime="text/csv",
                               disabled=filtered.empty)
        with st.expander("Preview the summary report"):
            st.code(report, language=None)


# =============================================================== page start
manager = AttendanceManager(CLEAN_CSV)
try:
    data = manager.load()                    # never cached, so CRUD changes appear straight away
except AttendanceDataError as err:
    ui_style.sidebar(None)
    ui_style.hero("Attendance Analytics", "Understand attendance patterns and identify students who may need academic support.",
                  ["SDG 4 · Quality Education"])
    st.error(str(err))
    st.info("You can rebuild the cleaned file from the raw CSV (the raw file is never changed).")
    if st.button("Build cleaned dataset from raw CSV"):
        try:
            result = clean_attendance.clean()
            flash_and_rerun("success", f"Cleaned dataset created with {result['cleaned_rows']} records.")
        except AttendanceDataError as err2:
            st.error(str(err2))
    st.stop()

ui_style.sidebar(len(data))
ui_style.hero("Attendance Analytics",
              "Understand attendance patterns, monitor student participation, and identify students who may need academic support.",
              ["Analyses attendance records", "SDG 4 · Quality Education", f"{len(data):,} records in dataset"])

if "flash" in st.session_state:
    kind, message = st.session_state.pop("flash")
    getattr(st, kind)(message)
if data["date"].isna().any():
    st.warning(f"{int(data['date'].isna().sum())} record(s) have an invalid date and are excluded from date filters and the trend chart.")
if (~data["status"].isin([0, 1])).any():
    st.warning(f"{int((~data['status'].isin([0, 1])).sum())} record(s) have an invalid status and are excluded from percentages.")
if data.empty:
    st.info("The dataset has no records yet. Open **Records → Add record** to add the first one.")

# ---------------------------------------------------------------- filter panel
valid_dates = data["date"].dropna()
min_day = valid_dates.min().date() if len(valid_dates) else date.today()
max_day = valid_dates.max().date() if len(valid_dates) else date.today()
if "f_status" not in st.session_state or st.session_state.pop("_reset", False):
    reset_filters(min_day, max_day)

sort_options = {"Student ID": "student_id", "Date": "date", "Semester": "semester", "Subject code": "subject_code",
                "Status": "status", "Late entry": "late_entry", "Record ID": "record_id"}
subject_pairs = data[["subject_code", "subject_name"]].dropna().drop_duplicates().sort_values("subject_code")
subject_names = dict(zip(subject_pairs["subject_code"], subject_pairs["subject_name"]))

with st.container(border=True):
    ui_style.section_header("Search and filter", "Every number, chart and table below follows these filters.")
    c1, c2, c3, c4 = st.columns([1.2, 1.4, 1.8, 1])
    search = c1.text_input("Student ID", key="f_search", placeholder="e.g. ST1411")
    semesters = c2.multiselect("Semester", sorted(data["semester"].dropna().unique().tolist()), key="f_sem",
                               placeholder="All semesters")
    subjects = c3.multiselect("Subject", list(subject_names), key="f_sub", format_func=lambda c: f"{c} – {subject_names[c]}",
                              placeholder="All subjects")
    status_choice = c4.selectbox("Attendance status", ["All", "Present", "Absent"], key="f_status")
    with st.expander("More filters, sorting and threshold"):
        d1, d2, d3 = st.columns(3)
        picked = d1.date_input("Date range", key="f_date", min_value=date(2000, 1, 1), max_value=date(2100, 12, 31),
                               format="YYYY-MM-DD")
        late_choice = d2.selectbox("Late entry", ["All", "Late entries only", "Not late"], key="f_late")
        exam_choice = d3.selectbox("Exam week", ["All", "Exam week only", "Regular week only"], key="f_exam")
        s1, s2, s3 = st.columns(3)
        sort_label = s1.selectbox("Sort by", list(sort_options), key="f_sort")
        descending = s2.radio("Order", ["Ascending", "Descending"], horizontal=True, key="f_order") == "Descending"
        THRESHOLD = float(s3.number_input("Attendance threshold (%)", min_value=1, max_value=100, step=5, key="f_thr",
                                          help="Students below this percentage are flagged."))
    if isinstance(picked, (tuple, list)):
        start_day = picked[0] if len(picked) > 0 else min_day
        end_day = picked[1] if len(picked) > 1 else max_day
        if len(picked) < 2:
            st.caption("Pick an end date to finish the date range.")
    else:
        start_day, end_day = picked, max_day

    filtered = aa.apply_filters(data, search, semesters, subjects, status_choice, start_day, end_day, late_choice, exam_choice)
    filtered = aa.sort_data(filtered, sort_options[sort_label], ascending=not descending)
    f1, f2 = st.columns([4, 1])
    f1.caption(f"**{len(filtered):,}** of {len(data):,} records match the current filters.")
    f2.button("Reset filters", on_click=request_reset)

filters_used = {
    "Student ID search": search.strip() or "None",
    "Semester": ", ".join(map(str, semesters)) or "All",
    "Subject": ", ".join(subjects) or "All",
    "Status": status_choice, "Late entry": late_choice, "Exam week": exam_choice,
    "Date range": f"{start_day} to {end_day}", "Threshold": f"{THRESHOLD:g}%",
    "Sorted by": f"{sort_label} ({'descending' if descending else 'ascending'})",
}

# ---------------------------------------------------------------- metric cards
m = aa.overall_metrics(filtered, THRESHOLD)
pct_tone = "green" if m["overall_pct"] >= THRESHOLD else "amber"
cards = [
    ("Attendance records", f"{m['total_records']:,}", "📋", "blue", "class records (rows)"),
    ("Unique students", f"{m['unique_students']:,}", "👥", "indigo", "different student IDs"),
    ("Overall attendance", f"{m['overall_pct']}%", "📈", pct_tone, "present ÷ records"),
    ("Present records", f"{m['present']:,}", "✅", "teal", "status = Present"),
    ("Absent records", f"{m['absent']:,}", "🚫", "amber", "status = Absent"),
    (f"Students below {THRESHOLD:g}%", f"{m['below_threshold']:,}", "⚠️", "red" if m["below_threshold"] else "green",
     "may need support"),
]
for col, card in zip(st.columns(6), cards):
    col.markdown(ui_style.metric_card(*card), unsafe_allow_html=True)
st.write("")

# ---------------------------------------------------------------- navigation + section
section = st.segmented_control("Section", SECTIONS, default=SECTIONS[0], key="nav", label_visibility="collapsed") or SECTIONS[0]
no_data = m["total_records"] == 0

if section == "📊 Overview":
    if no_data:
        st.warning("No records match the current filters. Change a filter or press Reset filters.")
    else:
        section_overview(filtered, m)
elif section == "🎓 Students":
    if no_data:
        st.warning("No records match the current filters. Change a filter or press Reset filters.")
    else:
        section_students(filtered)
elif section == "🗂️ Records":
    section_records(manager, data, filtered)
elif section == "🧮 Calculator":
    section_calculator(data)
else:
    section_reports(filtered, len(data), filters_used)

ui_style.footer()
