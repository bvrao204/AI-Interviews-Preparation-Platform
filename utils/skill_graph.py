"""
utils/skill_graph.py
--------------------
Phase 13 – Research Contribution: AI Skill Intelligence Module
Builds a skill graph, predicts gaps, and generates adaptive learning paths.
"""

import streamlit as st
import plotly.graph_objects as go
import math

# ── Skill taxonomy: maps raw skills → category ────────────────────────────
SKILL_CATEGORIES = {
    "Programming Languages": ["Python","Java","C++","C","JavaScript","TypeScript","Go","Rust","Kotlin","Swift","R","Scala"],
    "Web & APIs":            ["React","Angular","Vue","Node.js","Flask","FastAPI","Django","REST","GraphQL","HTML","CSS"],
    "Databases":             ["SQL","MySQL","PostgreSQL","MongoDB","Redis","Cassandra","DynamoDB","SQLite"],
    "Cloud & DevOps":        ["AWS","GCP","Azure","Docker","Kubernetes","Terraform","CI/CD","Linux","Git"],
    "AI & ML":               ["Machine Learning","Deep Learning","PyTorch","TensorFlow","NLP","Computer Vision","Scikit-learn","Pandas","NumPy"],
    "System Design":         ["System Design","Distributed Systems","Microservices","Caching","Load Balancing","Message Queues","Event-Driven"],
    "Soft Skills":           ["Communication","Leadership","Teamwork","Problem Solving","Critical Thinking","Adaptability"],
    "Data Structures":       ["Algorithms","Data Structures","Dynamic Programming","Graph Algorithms","Tree Traversal","Binary Search"],
}

CATEGORY_COLORS = {
    "Programming Languages": "#818CF8",
    "Web & APIs":            "#34D399",
    "Databases":             "#FBBF24",
    "Cloud & DevOps":        "#60A5FA",
    "AI & ML":               "#EC4899",
    "System Design":         "#F97316",
    "Soft Skills":           "#A3E635",
    "Data Structures":       "#C084FC",
}

def categorize_skills(skills: list) -> dict:
    """Map a flat list of skills to their categories."""
    result = {}
    for skill in skills:
        matched = False
        for cat, cat_skills in SKILL_CATEGORIES.items():
            if any(skill.lower() == s.lower() or skill.lower() in s.lower() for s in cat_skills):
                result.setdefault(cat, []).append(skill)
                matched = True
                break
        if not matched:
            result.setdefault("Other", []).append(skill)
    return result


def build_skill_network_chart(skills: list, weak_skills: list = None) -> go.Figure:
    """
    Build a Plotly network graph showing skill nodes clustered by category.
    Green nodes = strong, Red nodes = weak.
    """
    weak_set = set(w.lower() for w in (weak_skills or []))
    categorized = categorize_skills(skills)

    node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
    edge_x, edge_y = [], []

    # Place categories in a circle; skills orbit around each category
    cats = list(categorized.keys())
    n_cats = len(cats)

    for ci, cat in enumerate(cats):
        angle = 2 * math.pi * ci / n_cats
        cx = math.cos(angle) * 3
        cy = math.sin(angle) * 3
        color = CATEGORY_COLORS.get(cat, "#9CA3AF")

        # Category node
        node_x.append(cx); node_y.append(cy)
        node_text.append(f"<b>{cat}</b>")
        node_color.append(color); node_size.append(28)

        # Skill nodes around category
        cat_skills = categorized[cat]
        n_skills = len(cat_skills)
        for si, skill in enumerate(cat_skills):
            skill_angle = angle + (si - n_skills/2) * 0.35
            sx = cx + math.cos(skill_angle) * 1.4
            sy = cy + math.sin(skill_angle) * 1.4

            is_weak = skill.lower() in weak_set
            s_color = "#EF4444" if is_weak else color

            node_x.append(sx); node_y.append(sy)
            node_text.append(f"{'⚠ ' if is_weak else ''}{skill}")
            node_color.append(s_color)
            node_size.append(18)

            # Edge from category to skill
            edge_x += [cx, sx, None]
            edge_y += [cy, sy, None]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=edge_x, y=edge_y,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.08)", width=1),
        hoverinfo="none",
    ))
    fig.add_trace(go.Scatter(
        x=node_x, y=node_y,
        mode="markers+text",
        text=node_text,
        textposition="top center",
        textfont=dict(size=10, color="#E5E7EB"),
        marker=dict(size=node_size, color=node_color,
                    line=dict(color="#0F172A", width=2)),
        hoverinfo="text",
    ))
    fig.update_layout(
        showlegend=False,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        margin=dict(l=10, r=10, t=20, b=10),
        height=500,
    )
    return fig


def predict_skill_gap(candidate_skills: list, job_description: str) -> dict:
    """
    Simple keyword-based skill gap predictor.
    Compares candidate skills against common JD keywords.
    """
    jd_lower = job_description.lower()
    all_skills = [s for cat in SKILL_CATEGORIES.values() for s in cat]

    jd_required = [s for s in all_skills if s.lower() in jd_lower]
    candidate_lower = [s.lower() for s in candidate_skills]

    matched   = [s for s in jd_required if s.lower() in candidate_lower]
    missing   = [s for s in jd_required if s.lower() not in candidate_lower]
    extra     = [s for s in candidate_skills if s.lower() not in [x.lower() for x in jd_required]]

    coverage  = round(len(matched) / len(jd_required) * 100) if jd_required else 0

    return {
        "required":  jd_required,
        "matched":   matched,
        "missing":   missing,
        "extra":     extra,
        "coverage":  coverage,
    }


def predict_difficulty(skill_scores: dict) -> str:
    """Predict recommended question difficulty based on average skill scores."""
    avg = sum(skill_scores.values()) / len(skill_scores) if skill_scores else 60
    if avg >= 82:   return "Advanced"
    elif avg >= 68: return "Intermediate"
    else:           return "Beginner"


RESOURCE_MAP = {
    "System Design":         {
        "youtube": "https://www.youtube.com/results?search_query=system+design+interview",
        "book":    "Designing Data-Intensive Applications – Martin Kleppmann",
        "practice": "https://leetcode.com/discuss/general-discussion/1122776/system-design-questions"
    },
    "Algorithms":            {
        "youtube": "https://www.youtube.com/results?search_query=algorithms+data+structures+tutorial",
        "book":    "Introduction to Algorithms – CLRS",
        "practice": "https://leetcode.com/explore/"
    },
    "Machine Learning":      {
        "youtube": "https://www.youtube.com/c/3blue1brown",
        "book":    "Hands-On Machine Learning – Aurélien Géron",
        "practice": "https://www.kaggle.com/learn"
    },
    "Communication":         {
        "youtube": "https://www.youtube.com/results?search_query=communication+skills+interview",
        "book":    "Crucial Conversations – Patterson et al.",
        "practice": "https://www.pramp.com/"
    },
    "SQL":                   {
        "youtube": "https://www.youtube.com/results?search_query=sql+interview+questions",
        "book":    "Learning SQL – Alan Beaulieu",
        "practice": "https://leetcode.com/studyplan/top-sql-50/"
    },
}

def get_resources(weak_skill: str) -> dict:
    """Return curated resources for a weak skill."""
    for key, res in RESOURCE_MAP.items():
        if key.lower() in weak_skill.lower() or weak_skill.lower() in key.lower():
            return res
    return {
        "youtube":  f"https://www.youtube.com/results?search_query={weak_skill.replace(' ', '+')}+tutorial",
        "book":     "Search for a dedicated book on this topic",
        "practice": f"https://leetcode.com/problemset/?search={weak_skill.replace(' ', '+')}",
    }
