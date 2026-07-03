"""
utils/history_store.py
----------------------
Tracks per-candidate interview history within a session.
Each completed interview is appended as a timestamped snapshot.
Demo data shows a 3-session improvement arc.
"""

import streamlit as st
from datetime import datetime, timedelta

# ── Demo data: 3 past interviews showing clear improvement ─────────────────
DEMO_HISTORY = [
    {
        "session": 1,
        "label": "Interview 1",
        "date": (datetime.now() - timedelta(days=14)).strftime("%d %b %Y"),
        "role": "Software Engineer",
        "communication":      72,
        "technical_knowledge": 68,
        "problem_solving":    65,
        "confidence":         60,
        "resume_score":       78,
        "interview_score":    69,
        "hiring_probability": 62,
        "final_recommendation": "Waitlist",
        "top_skills":   ["Python", "REST APIs"],
        "weak_skills":  ["System Design", "Concurrency", "Communication"],
        "summary": "Struggled with system design depth. Communication was unclear under pressure.",
    },
    {
        "session": 2,
        "label": "Interview 2",
        "date": (datetime.now() - timedelta(days=7)).strftime("%d %b %Y"),
        "role": "Software Engineer",
        "communication":      81,
        "technical_knowledge": 76,
        "problem_solving":    74,
        "confidence":         72,
        "resume_score":       82,
        "interview_score":    78,
        "hiring_probability": 74,
        "final_recommendation": "Consider",
        "top_skills":   ["Python", "System Design", "REST APIs"],
        "weak_skills":  ["Concurrency", "Database Optimization"],
        "summary": "Clear improvement in communication. Still needs work on advanced DB topics.",
    },
    {
        "session": 3,
        "label": "Interview 3",
        "date": datetime.now().strftime("%d %b %Y"),
        "role": "Software Engineer",
        "communication":      89,
        "technical_knowledge": 87,
        "problem_solving":    85,
        "confidence":         83,
        "resume_score":       91,
        "interview_score":    88,
        "hiring_probability": 89,
        "final_recommendation": "Hire",
        "top_skills":   ["Python", "System Design", "Concurrency", "REST APIs"],
        "weak_skills":  ["Leadership"],
        "summary": "Excellent performance across all areas. Strong hire recommendation.",
    },
]

TRACKED_METRICS = [
    ("communication",       "Communication",       "#34D399"),
    ("technical_knowledge", "Technical Skills",    "#60A5FA"),
    ("problem_solving",     "Problem Solving",     "#FBBF24"),
    ("confidence",          "Confidence",          "#C084FC"),
    ("interview_score",     "Overall Score",       "#EC4899"),
]


from utils.data_store import load_history, save_history

def _ensure_store():
    if "interview_history" not in st.session_state:
        st.session_state.interview_history = load_history()


def add_session(eval_data: dict, role: str):
    """Append a completed interview result to the history store."""
    _ensure_store()
    raw = eval_data.get("scores", {})
    gap = eval_data.get("skill_gap_analysis", {})
    insights = eval_data.get("recruiter_insights", {})

    def _int(val, fb=75):
        try: return int(val)
        except: return fb

    n = len(st.session_state.interview_history) + 1
    record = {
        "session": n,
        "label":   f"Interview {n}",
        "date":    datetime.now().strftime("%d %b %Y"),
        "role":    role,
        "communication":       _int(raw.get("communication", 75)),
        "technical_knowledge": _int(raw.get("technical_knowledge", 75)),
        "problem_solving":     _int(raw.get("problem_solving", 75)),
        "confidence":          _int(raw.get("confidence", 75)),
        "resume_score":        _int(raw.get("resume_score", 75)),
        "interview_score":     _int(raw.get("interview_score", 75)),
        "hiring_probability":  _int(raw.get("hiring_probability", 75)),
        "final_recommendation": insights.get("final_recommendation", "Consider"),
        "top_skills":  gap.get("strengths", []),
        "weak_skills": gap.get("weaknesses", []),
        "summary":     eval_data.get("overall_summary", ""),
    }
    st.session_state.interview_history.append(record)
    save_history(st.session_state.interview_history)


def get_history(demo_mode: bool = False) -> list:
    """Return history list; use demo data when no real sessions exist."""
    _ensure_store()
    if demo_mode and not st.session_state.interview_history:
        return DEMO_HISTORY
    return st.session_state.interview_history


def clear_history():
    st.session_state.interview_history = []
    save_history([])
