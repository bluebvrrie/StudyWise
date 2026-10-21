"""
ui_style.py
-----------
The look of EduTrack in one place: colours, a small amount of CSS, and helpers that build
HTML cards (header, metric cards, result panel...). Only plain, safe numbers/labels are put into
the HTML, and every piece of text goes through html.escape().

If the CSS ever fails to load, the app still works - it just looks like normal Streamlit.
"""
import html

import streamlit as st

from attendance_charts import COLORS

TONES = {   # tone name -> (main colour, light tint used for icon tiles)
    "indigo": (COLORS["primary"], "#E8ECF6"),
    "blue": (COLORS["secondary"], "#E7EEFD"),
    "teal": (COLORS["accent"], "#DDF6F3"),
    "green": (COLORS["success"], "#DCF5E4"),
    "amber": (COLORS["warning"], "#FEF0D2"),
    "red": (COLORS["danger"], "#FBE0E0"),
}

CSS = f"""
<style>
.stApp {{ background: #F5F7FB; }}
.block-container, [data-testid="stMainBlockContainer"] {{ padding-top: 1.4rem; padding-bottom: 2.5rem; max-width: 1280px; }}

/* white "cards" for every bordered container */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 14px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}

/* header banner */
.et-hero {{ background: linear-gradient(120deg, {COLORS['primary']} 0%, {COLORS['secondary']} 100%);
    border-radius: 18px; padding: 26px 32px; color: #fff; margin-bottom: 16px; }}
.et-brand {{ font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; opacity: 0.85; font-weight: 600; }}
.et-title {{ font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif; font-size: 2.1rem;
    font-weight: 700; line-height: 1.15; margin: 4px 0 6px 0; }}
.et-subtitle {{ font-size: 1rem; opacity: 0.92; max-width: 760px; line-height: 1.45; }}
.et-chips {{ margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }}
.et-chip {{ background: rgba(255,255,255,0.16); border: 1px solid rgba(255,255,255,0.28); color: #fff;
    border-radius: 999px; padding: 3px 12px; font-size: 0.78rem; font-weight: 600; }}

/* metric cards */
.et-card {{ background: {COLORS['card']}; border: 1px solid {COLORS['border']}; border-radius: 14px;
    padding: 14px 16px; height: 118px; box-shadow: 0 1px 2px rgba(15,23,42,0.04); border-top-width: 3px; }}
.et-card-head {{ display: flex; align-items: center; gap: 8px; }}
.et-ico {{ width: 26px; height: 26px; border-radius: 8px; display: inline-flex; align-items: center;
    justify-content: center; font-size: 0.9rem; }}
.et-label {{ color: {COLORS['muted']}; font-size: 0.78rem; font-weight: 600; line-height: 1.2; }}
.et-value {{ color: {COLORS['text']}; font-size: 1.85rem; font-weight: 700; margin-top: 8px;
    font-variant-numeric: tabular-nums; line-height: 1.1; }}
.et-note {{ color: {COLORS['muted']}; font-size: 0.72rem; margin-top: 4px; }}

/* section titles */
.et-section {{ margin: 2px 0 10px 0; }}
.et-section-title {{ color: {COLORS['primary']}; font-size: 1.15rem; font-weight: 700; }}
.et-section-sub {{ color: {COLORS['muted']}; font-size: 0.85rem; margin-top: 1px; }}
.et-label-small {{ color: {COLORS['muted']}; font-size: 0.72rem; font-weight: 700; letter-spacing: 0.07em;
    text-transform: uppercase; margin-bottom: 4px; }}

/* insight chips */
.et-insights {{ display: flex; flex-wrap: wrap; gap: 8px; margin: 4px 0 6px 0; }}
.et-insight {{ border-radius: 10px; padding: 7px 12px; font-size: 0.83rem; font-weight: 500; border: 1px solid; }}

/* calculator result */
.et-result {{ border-radius: 14px; padding: 18px 20px; border: 1px solid; }}
.et-tiles {{ display: flex; gap: 12px; flex-wrap: wrap; margin: 10px 0 12px 0; }}
.et-tile {{ background: #fff; border: 1px solid {COLORS['border']}; border-radius: 12px; padding: 10px 16px; min-width: 150px; flex: 1; }}
.et-tile-label {{ color: {COLORS['muted']}; font-size: 0.74rem; font-weight: 600; }}
.et-tile-value {{ color: {COLORS['text']}; font-size: 1.6rem; font-weight: 700; font-variant-numeric: tabular-nums; }}
.et-headline {{ font-size: 1.05rem; font-weight: 700; }}
.et-body {{ color: {COLORS['text']}; font-size: 0.9rem; margin-top: 4px; line-height: 1.5; }}
.et-bar {{ position: relative; height: 10px; background: #E5EAF3; border-radius: 999px; margin-top: 10px; }}
.et-bar-fill {{ height: 10px; border-radius: 999px; }}
.et-bar-mark {{ position: absolute; top: -4px; width: 2px; height: 18px; background: {COLORS['primary']}; }}
.et-bar-legend {{ color: {COLORS['muted']}; font-size: 0.72rem; margin-top: 6px; }}

/* sidebar + footer */
.et-side-brand {{ font-size: 1.15rem; font-weight: 700; color: {COLORS['primary']}; }}
.et-footer {{ text-align: center; color: {COLORS['muted']}; font-size: 0.78rem; padding: 22px 0 4px 0;
    border-top: 1px solid {COLORS['border']}; margin-top: 28px; }}
</style>
"""


def apply_style():
    """Call once at the top of every page (after st.set_page_config)."""
    st.markdown(CSS, unsafe_allow_html=True)


def hero(title, subtitle, chips):
    chip_html = "".join(f'<span class="et-chip">{html.escape(c)}</span>' for c in chips)
    st.markdown(
        f'<div class="et-hero"><div class="et-brand">🎓 EduTrack</div>'
        f'<div class="et-title">{html.escape(title)}</div>'
        f'<div class="et-subtitle">{html.escape(subtitle)}</div>'
        f'<div class="et-chips">{chip_html}</div></div>', unsafe_allow_html=True)


def metric_card(label, value, icon, tone="blue", note=""):
    main, tint = TONES[tone]
    return (f'<div class="et-card" style="border-top-color:{main}">'
            f'<div class="et-card-head"><span class="et-ico" style="background:{tint}">{icon}</span>'
            f'<span class="et-label">{html.escape(label)}</span></div>'
            f'<div class="et-value">{html.escape(str(value))}</div>'
            f'<div class="et-note">{html.escape(note)}</div></div>')


def section_header(title, subtitle=""):
    sub = f'<div class="et-section-sub">{html.escape(subtitle)}</div>' if subtitle else ""
    st.markdown(f'<div class="et-section"><div class="et-section-title">{html.escape(title)}</div>{sub}</div>',
                unsafe_allow_html=True)


def small_label(text):
    st.markdown(f'<div class="et-label-small">{html.escape(text)}</div>', unsafe_allow_html=True)


def insight_chips(items):
    """items = [(tone, text)] with tone 'good' / 'warn' / 'info'."""
    colours = {"good": (COLORS["success"], "#F0FBF4"), "warn": ("#B45309", "#FFF8E6"), "info": (COLORS["secondary"], "#F1F5FE")}
    chips = ""
    for tone, text in items:
        main, bg = colours.get(tone, colours["info"])
        chips += (f'<span class="et-insight" style="color:{main};background:{bg};border-color:{main}33">'
                  f'{html.escape(text)}</span>')
    st.markdown(f'<div class="et-insights">{chips}</div>', unsafe_allow_html=True)


def result_panel(tone, headline, body, tiles, current_pct, required_pct):
    """Calculator result. tiles = [(label, value_text)]. All values are numbers made by the app."""
    main, tint = TONES[tone]
    tile_html = "".join(f'<div class="et-tile"><div class="et-tile-label">{html.escape(l)}</div>'
                        f'<div class="et-tile-value">{html.escape(v)}</div></div>' for l, v in tiles)
    fill = max(0.0, min(100.0, float(current_pct)))
    mark = max(0.0, min(100.0, float(required_pct)))
    st.markdown(
        f'<div class="et-result" style="background:{tint};border-color:{main}55">'
        f'<div class="et-headline" style="color:{main}">{html.escape(headline)}</div>'
        f'<div class="et-tiles">{tile_html}</div>'
        f'<div class="et-body">{html.escape(body)}</div>'
        f'<div class="et-bar"><div class="et-bar-fill" style="width:{fill:.2f}%;background:{main}"></div>'
        f'<div class="et-bar-mark" style="left:{mark:.2f}%"></div></div>'
        f'<div class="et-bar-legend">Bar = your attendance · dark line = required {mark:g}%</div></div>',
        unsafe_allow_html=True)


def sidebar(record_count=None):
    """Small, useful sidebar content (Streamlit adds the page links above it automatically)."""
    with st.sidebar:
        st.markdown('<div class="et-side-brand">🎓 EduTrack</div>', unsafe_allow_html=True)
        st.caption("Student Academic Analytics System")
        if record_count is not None:
            st.caption(f"Dataset: {record_count:,} attendance records")
        st.caption("Supports UN SDG 4 – Quality Education")


def footer():
    st.markdown('<div class="et-footer">EduTrack | Student Attendance Analytics | SDG 4: Quality Education</div>',
                unsafe_allow_html=True)
