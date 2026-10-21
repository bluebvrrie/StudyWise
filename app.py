from pathlib import Path

import streamlit as st


st.set_page_config(
    page_title="StudyWise | Academic Support",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)


def show_homepage():
    st.markdown(
        """
        <style>
        .block-container {max-width: 1180px; padding-top: 2rem; padding-bottom: 2rem;}
        .hero {padding: 2.4rem 2.6rem; border-radius: 24px;
          background: linear-gradient(120deg,#eef3ff 0%,#e8fbf8 100%);
          border: 1px solid #dfe8f5; margin: 1rem 0 2rem;}
        .hero h1 {font-size: clamp(2.3rem,5vw,3.6rem); letter-spacing: -0.04em;
          color: #172554; margin: .25rem 0 .65rem;}
        .hero p {font-size: 1.1rem; color: #46566f; max-width: 760px; margin-bottom: 0;}
        .eyebrow {font-size: .8rem; font-weight: 700; letter-spacing: .13em;
          text-transform: uppercase; color: #3976b8;}
        .module-card {height: 100%; min-height: 225px; padding: 1.35rem 1.4rem;
          border: 1px solid #e4eaf2; border-radius: 18px; background: #fff;
          box-shadow: 0 8px 24px rgba(28,48,84,.055);}
        .module-card h3 {margin: .5rem 0; color: #172554; font-size: 1.25rem;}
        .module-card p {color: #526176; line-height: 1.55;}
        .module-icon {font-size: 1.8rem;}
        .pending {background: #fafbfe; border-style: dashed;}
        .note {font-size: .82rem; color: #8a5b18; margin-top: .75rem;}
        .footer {text-align: center; color: #78859a; font-size: .85rem;
          padding-top: 1.4rem; border-top: 1px solid #e8edf4; margin-top: 2.5rem;}
        </style>
        <section class="hero">
          <div class="eyebrow">Your learning, in one place</div>
          <h1>Welcome to StudyWise <span>📚</span></h1>
          <p>A student academic support platform for planning study time,
          understanding attendance, and exploring academic performance.</p>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Explore your tools")
    st.caption("Choose a module to open its original StudyWise workspace.")

    first, second = st.columns(2, gap="large")
    with first:
        st.markdown(
            """<div class="module-card"><div class="module-icon">🗓️</div>
            <h3>Study Planner &amp; Dashboard</h3>
            <p>Review study records and performance, set grade targets, prioritize
            subjects, plan study hours, and explore dashboard insights and reports.</p></div>""",
            unsafe_allow_html=True,
        )
        st.page_link("study_dashboard.py", label="Open Study Planner", icon="📚", use_container_width=True)

    with second:
        st.markdown(
            """<div class="module-card"><div class="module-icon">📅</div>
            <h3>Attendance Analytics</h3>
            <p>Explore attendance trends and student records, use the 75% attendance
            calculator, manage entries, and view charts and reports.</p></div>""",
            unsafe_allow_html=True,
        )
        st.page_link("pages/Attendance_Analysis.py", label="Open Attendance Analytics", icon="📈", use_container_width=True)

    third, fourth = st.columns(2, gap="large")
    with third:
        st.markdown(
            """<div class="module-card"><div class="module-icon">📊</div>
            <h3>Student Performance Analysis</h3>
            <p>Filter student assessment results by department, year, and estimated
            outcome; inspect mark distributions and download filtered results or a report.</p>
            <div class="note">The source module expects its default CSV beside its script;
            the supplied CSV currently lives in <code>data/</code>.</div></div>""",
            unsafe_allow_html=True,
        )
        st.page_link("student_performance_app.py", label="Open Performance Analysis", icon="🎓", use_container_width=True)

    with fourth:
        st.markdown(
            """<div class="module-card pending"><div class="module-icon">✨</div>
            <h3>Coming soon</h3>
            <p><strong>Teammate module</strong><br>Her page will be connected here
            when it is ready. This space is reserved for a future StudyWise tool.</p></div>""",
            unsafe_allow_html=True,
        )
        st.button("Module not available yet", disabled=True, use_container_width=True)

    st.markdown(
        '<div class="footer">StudyWise · Student academic support platform</div>',
        unsafe_allow_html=True,
    )


PROJECT = Path(__file__).resolve().parent
pages = [
    st.Page(show_homepage, title="Home", icon="🏠", default=True),
    st.Page(PROJECT / "study_dashboard.py", title="Study Planner", icon="📚"),
    st.Page(PROJECT / "pages" / "Attendance_Analysis.py", title="Attendance Analytics", icon="📅"),
    st.Page(PROJECT / "student_performance_app.py", title="Student Performance", icon="📊"),
]
navigation = st.navigation(pages)
navigation.run()
