"""
attendance_charts.py
--------------------
Matplotlib charts with one shared visual style. Each function takes already-calculated data and
returns a Figure
"""
import textwrap

import matplotlib
import numpy as np
from matplotlib.figure import Figure

# ---- Design palette
COLORS = {
    "primary": "#243B6B",    # deep indigo / navy
    "secondary": "#4776E6",  # blue
    "accent": "#14B8A6",     # teal
    "success": "#16A34A",
    "warning": "#F59E0B",
    "danger": "#DC2626",
    "text": "#1F2937",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "card": "#FFFFFF",
}


matplotlib.rcParams["font.family"] = "sans-serif"
matplotlib.rcParams["font.sans-serif"] = ["Segoe UI", "Arial", "DejaVu Sans"]


def _new_figure(width, height):
    fig = Figure(figsize=(width, height), facecolor=COLORS["card"])
    return fig, fig.subplots()


def _style_axes(ax, title, xlabel=None, ylabel=None):
    """Clean look: no top/right frame, light horizontal grid, left-aligned title."""
    ax.set_title(title, loc="left", fontsize=12, fontweight="semibold", color=COLORS["primary"], pad=12)
    ax.set_facecolor(COLORS["card"])
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(COLORS["border"])
    ax.tick_params(colors=COLORS["muted"], labelsize=9, length=0)
    ax.yaxis.grid(True, color="#EEF2F7", linewidth=1)
    ax.set_axisbelow(True)
    if xlabel:
        ax.set_xlabel(xlabel, color=COLORS["muted"], fontsize=9)
    if ylabel:
        ax.set_ylabel(ylabel, color=COLORS["muted"], fontsize=9)


def bar_attendance(summary, label_column, title, xlabel, threshold=75):
    """Bars = attendance % per group. Blue = meets the threshold, amber = below it."""
    if summary is None or len(summary) == 0:
        return None
    labels = [textwrap.fill(str(x), 13) for x in summary[label_column]]
    values = summary["attendance_pct"].to_numpy(dtype=float)
    colors = [COLORS["secondary"] if v >= threshold else COLORS["warning"] for v in values]
    fig, ax = _new_figure(7, 3.8)
    bars = ax.bar(labels, values, color=colors, width=0.6)
    ax.axhline(threshold, color=COLORS["muted"], linestyle="--", linewidth=1, label=f"{threshold:g}% threshold")
    for bar, pct, n in zip(bars, values, summary["total"]):
        ax.text(bar.get_x() + bar.get_width() / 2, pct + 1.5, f"{pct:.1f}%", ha="center", va="bottom",
                fontsize=9, fontweight="semibold", color=COLORS["text"])
        ax.text(bar.get_x() + bar.get_width() / 2, 3, f"n={n:,}", ha="center", va="bottom", fontsize=8, color="white")
    ax.set_ylim(0, 112)
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.set_yticklabels(["0%", "25%", "50%", "75%", "100%"])
    _style_axes(ax, title, xlabel, "Attendance")
    ax.legend(loc="upper right", fontsize=8, frameon=False, labelcolor=COLORS["muted"])
    fig.tight_layout()
    return fig


def pie_present_absent(present, absent):
    """Donut chart of present vs absent with the overall % in the centre."""
    total = present + absent
    if total == 0:
        return None
    sizes, labels, colors = [], [], []
    for count, name, color in [(present, "Present", COLORS["accent"]), (absent, "Absent", COLORS["warning"])]:
        if count > 0:                                       # skip empty slices
            sizes.append(count)
            labels.append(f"{name}  {count:,}")
            colors.append(color)
    fig, ax = _new_figure(4.2, 3.8)
    ax.pie(sizes, colors=colors, startangle=90, counterclock=False,
           wedgeprops={"width": 0.38, "edgecolor": "white", "linewidth": 2})
    ax.text(0, 0.06, f"{present / total * 100:.1f}%", ha="center", va="center", fontsize=20,
            fontweight="bold", color=COLORS["primary"])
    ax.text(0, -0.22, "present", ha="center", va="center", fontsize=9, color=COLORS["muted"])
    ax.set_title("Present vs absent", loc="left", fontsize=12, fontweight="semibold", color=COLORS["primary"], pad=12)
    ax.legend(labels, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=2, frameon=False, fontsize=9,
              labelcolor=COLORS["text"])
    fig.tight_layout()
    return fig


def line_trend(trend, frequency, threshold=75):
    """Attendance % per month/week. Needs at least 2 periods to draw a line."""
    if trend is None or len(trend) < 2:
        return None
    fig, ax = _new_figure(7, 3.8)
    ax.plot(trend["period"], trend["attendance_pct"], marker="o", markersize=5, linewidth=2.2,
            color=COLORS["secondary"], label="Attendance")
    ax.fill_between(trend["period"], trend["attendance_pct"], trend["attendance_pct"].min() - 10,
                    color=COLORS["secondary"], alpha=0.08)
    ax.axhline(threshold, color=COLORS["muted"], linestyle="--", linewidth=1, label=f"{threshold:g}% threshold")
    low = max(0, float(trend["attendance_pct"].min()) - 10)
    ax.set_ylim(low, min(105, float(trend["attendance_pct"].max()) + 6))
    _style_axes(ax, f"Attendance over time ({frequency.lower()})", "Period start", "Attendance (%)")
    ax.legend(fontsize=8, frameon=False, loc="lower left", labelcolor=COLORS["muted"])
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def hist_minutes_late(minutes):
    if minutes is None or len(minutes) == 0:
        return None
    fig, ax = _new_figure(5, 3.4)
    ax.hist(minutes, bins=np.arange(0, max(minutes) + 3, 2), color=COLORS["warning"], edgecolor="white")
    _style_axes(ax, "How late were late arrivals?", "Minutes after class start", "Late entries")
    fig.tight_layout()
    return fig


def hist_student_pct(percentages, threshold=75):
    """Spread of student attendance %: how many students fall in each band."""
    if percentages is None or len(percentages) == 0:
        return None
    values = np.asarray(percentages, dtype=float)
    fig, ax = _new_figure(7, 3.4)
    _, bins, patches = ax.hist(values, bins=np.arange(0, 105, 5), edgecolor="white")
    for left_edge, patch in zip(bins[:-1], patches):
        patch.set_facecolor(COLORS["secondary"] if left_edge >= threshold else COLORS["warning"])
    ax.axvline(threshold, color=COLORS["muted"], linestyle="--", linewidth=1)
    _style_axes(ax, "How student attendance is spread", "Student attendance (%)", "Number of students")
    fig.tight_layout()
    return fig
