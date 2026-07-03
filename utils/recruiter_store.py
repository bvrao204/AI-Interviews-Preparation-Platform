"""
utils/recruiter_store.py
------------------------
Manages in-session candidate registry for the Recruiter Dashboard.
All data lives in st.session_state["recruiter_candidates"] so it persists
across page navigations within the same browser session.
"""

import streamlit as st

# --------------------------------------------------------------------------- #
# Demo seed data – shown when Demo Mode is active and no real interviews exist #
# --------------------------------------------------------------------------- #
DEMO_CANDIDATES = [
    {
        "name": "Alice Chen",
        "role": "Senior Software Engineer",
        "hiring_probability": 89,
        "resume_score": 92,
        "interview_score": 85,
        "technical_knowledge": 87,
        "communication": 82,
        "problem_solving": 76,
        "confidence": 80,
        "recommended_role": "Software Engineer",
        "expected_salary": "$110,000 – $130,000",
        "final_recommendation": "Hire",
        "top_skills": ["Python", "System Design", "Data Structures"],
        "weak_skills": ["Leadership", "Cloud Architecture"],
    },
    {
        "name": "Bob Kumar",
        "role": "Backend Developer",
        "hiring_probability": 74,
        "resume_score": 78,
        "interview_score": 71,
        "technical_knowledge": 73,
        "communication": 68,
        "problem_solving": 70,
        "confidence": 65,
        "recommended_role": "Junior Backend Developer",
        "expected_salary": "$75,000 – $90,000",
        "final_recommendation": "Waitlist",
        "top_skills": ["REST APIs", "SQL", "Node.js"],
        "weak_skills": ["System Design", "Concurrency", "Distributed Systems"],
    },
    {
        "name": "Sarah Lee",
        "role": "Data Scientist",
        "hiring_probability": 95,
        "resume_score": 96,
        "interview_score": 93,
        "technical_knowledge": 94,
        "communication": 90,
        "problem_solving": 91,
        "confidence": 88,
        "recommended_role": "Lead Data Scientist",
        "expected_salary": "$130,000 – $155,000",
        "final_recommendation": "Strong Hire",
        "top_skills": ["Machine Learning", "PyTorch", "Statistics", "Python"],
        "weak_skills": ["Frontend Integration"],
    },
]


from utils.data_store import load_candidates, save_candidates

def _ensure_store():
    """Initialise the candidate list in session state if not present."""
    if "recruiter_candidates" not in st.session_state:
        st.session_state.recruiter_candidates = load_candidates()


def add_candidate(eval_data: dict, candidate_name: str, role: str):
    """
    Persist a completed interview result to the recruiter store.
    Called automatically after evaluate_interview_feedback() returns.
    """
    _ensure_store()

    raw_scores = eval_data.get("scores", {})
    insights = eval_data.get("recruiter_insights", {})
    gap = eval_data.get("skill_gap_analysis", {})

    def _int(val, fallback=75):
        try:
            return int(val)
        except Exception:
            return fallback

    record = {
        "name": candidate_name or "Anonymous",
        "role": role,
        "hiring_probability": _int(raw_scores.get("hiring_probability", 75)),
        "resume_score": _int(raw_scores.get("resume_score", 75)),
        "interview_score": _int(raw_scores.get("interview_score", 75)),
        "technical_knowledge": _int(raw_scores.get("technical_knowledge", 75)),
        "communication": _int(raw_scores.get("communication", 75)),
        "problem_solving": _int(raw_scores.get("problem_solving", 75)),
        "confidence": _int(raw_scores.get("confidence", 75)),
        "recommended_role": insights.get("recommended_role", role),
        "expected_salary": insights.get("expected_salary", "N/A"),
        "final_recommendation": insights.get("final_recommendation", "Consider"),
        "top_skills": gap.get("strengths", []),
        "weak_skills": gap.get("weaknesses", []),
    }

    # Avoid saving the exact same session twice
    existing_names = [c["name"] for c in st.session_state.recruiter_candidates]
    if candidate_name not in existing_names:
        st.session_state.recruiter_candidates.append(record)
        save_candidates(st.session_state.recruiter_candidates)


def get_candidates(demo_mode: bool = False) -> list:
    """
    Return the full candidate list sorted by hiring_probability descending.
    In Demo Mode, merge real results with seeded demo data.
    """
    _ensure_store()
    real = st.session_state.recruiter_candidates

    if demo_mode and not real:
        return sorted(DEMO_CANDIDATES, key=lambda c: c["hiring_probability"], reverse=True)

    return sorted(real, key=lambda c: c["hiring_probability"], reverse=True)


def to_csv(candidates: list) -> str:
    """Convert candidate list to a CSV string for download."""
    if not candidates:
        return "No candidates found."

    headers = [
        "Rank", "Name", "Role", "Hiring Probability (%)", "Resume Score (%)",
        "Interview Score (%)", "Technical (%)", "Communication (%)",
        "Problem Solving (%)", "Confidence (%)", "Recommended Role",
        "Expected Salary", "Final Recommendation",
        "Top Skills", "Weak Skills"
    ]
    lines = [",".join(headers)]
    for rank, c in enumerate(candidates, 1):
        row = [
            str(rank),
            f'"{c["name"]}"',
            f'"{c["role"]}"',
            str(c["hiring_probability"]),
            str(c["resume_score"]),
            str(c["interview_score"]),
            str(c["technical_knowledge"]),
            str(c["communication"]),
            str(c["problem_solving"]),
            str(c["confidence"]),
            f'"{c["recommended_role"]}"',
            f'"{c["expected_salary"]}"',
            f'"{c["final_recommendation"]}"',
            f'"{" | ".join(c.get("top_skills", []))}"',
            f'"{" | ".join(c.get("weak_skills", []))}"',
        ]
        lines.append(",".join(row))
    return "\n".join(lines)


def clear_store():
    """Remove all candidate records from the session and JSON store."""
    st.session_state.recruiter_candidates = []
    save_candidates([])
