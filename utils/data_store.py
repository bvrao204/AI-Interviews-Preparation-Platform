"""
utils/data_store.py
-------------------
JSON file-based persistence layer.
Saves/loads interview history, candidate records, and user data to disk
so data survives app restarts — a stepping stone before a full DB.
"""

import json
import os
from datetime import datetime
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

HISTORY_FILE    = DATA_DIR / "interview_history.json"
CANDIDATES_FILE = DATA_DIR / "recruiter_candidates.json"
USERS_FILE      = DATA_DIR / "users.json"
QUESTIONS_FILE  = DATA_DIR / "questions_bank.json"


def _load(path: Path) -> list | dict:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return [] if path != USERS_FILE else {}


def _save(path: Path, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


# ── Interview History ──────────────────────────────────────────────────────
def load_history() -> list:
    return _load(HISTORY_FILE)


def save_history(history: list) -> None:
    _save(HISTORY_FILE, history)


def append_history_session(session: dict) -> None:
    h = load_history()
    h.append(session)
    save_history(h)


# ── Recruiter Candidates ───────────────────────────────────────────────────
def load_candidates() -> list:
    return _load(CANDIDATES_FILE)


def save_candidates(candidates: list) -> None:
    _save(CANDIDATES_FILE, candidates)


def append_candidate(record: dict) -> None:
    c = load_candidates()
    existing = [x["name"] for x in c]
    if record.get("name") not in existing:
        c.append(record)
        save_candidates(c)


# ── Users ──────────────────────────────────────────────────────────────────
def load_users() -> dict:
    return _load(USERS_FILE)


def save_users(users: dict) -> None:
    _save(USERS_FILE, users)


def register_user(username: str, name: str, role: str = "candidate") -> None:
    users = load_users()
    if username not in users:
        users[username] = {
            "name": name,
            "role": role,
            "registered": datetime.now().isoformat(),
            "interviews": 0
        }
        save_users(users)


def increment_user_interviews(username: str) -> None:
    users = load_users()
    if username in users:
        users[username]["interviews"] = users[username].get("interviews", 0) + 1
        save_users(users)


def delete_user(username: str) -> None:
    users = load_users()
    users.pop(username, None)
    save_users(users)


# ── Questions Bank ─────────────────────────────────────────────────────────
def load_questions() -> list:
    return _load(QUESTIONS_FILE)


def save_questions(questions: list) -> None:
    _save(QUESTIONS_FILE, questions)


def add_question(question: str, category: str, difficulty: str) -> None:
    qs = load_questions()
    qs.append({
        "question": question,
        "category": category,
        "difficulty": difficulty,
        "added": datetime.now().isoformat()
    })
    save_questions(qs)


def delete_question(index: int) -> None:
    qs = load_questions()
    if 0 <= index < len(qs):
        qs.pop(index)
        save_questions(qs)


# ── Analytics Helpers ─────────────────────────────────────────────────────
def get_analytics_summary() -> dict:
    history = load_history()
    candidates = load_candidates()
    users = load_users()
    if not history:
        return {"total_sessions": 0, "total_candidates": len(candidates), "total_users": len(users)}
    metrics = ["communication", "technical_knowledge", "problem_solving",
               "confidence", "interview_score", "hiring_probability"]
    avgs = {m: round(sum(s.get(m, 0) for s in history) / len(history)) for m in metrics}
    return {
        "total_sessions":    len(history),
        "total_candidates":  len(candidates),
        "total_users":       len(users),
        "averages":          avgs,
        "latest_session":    history[-1] if history else {},
    }
