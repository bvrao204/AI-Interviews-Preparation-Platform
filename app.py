import streamlit as st
import os
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
import plotly.graph_objects as go
import plotly.express as px
import streamlit_authenticator as stauth
from yaml.loader import SafeLoader

# Import our utility functions
from streamlit_ace import st_ace
from utils.css_styles import inject_custom_css
from utils.recruiter_store import add_candidate, get_candidates, to_csv, clear_store
from utils.history_store import add_session, get_history, clear_history, TRACKED_METRICS
from utils.data_store import (
    load_history as ds_load_history, append_history_session,
    load_candidates as ds_load_candidates, append_candidate as ds_append_candidate,
    load_users, save_users, delete_user, register_user,
    load_questions, add_question, delete_question,
    get_analytics_summary
)
from utils.skill_graph import (
    build_skill_network_chart, predict_skill_gap,
    predict_difficulty, get_resources, categorize_skills
)
from utils.resume_parser import parse_pdf_resume
from utils.eye_tracker import (
    start_eye_tracker_server, get_session_id,
    get_current_eye_status, get_eye_contact_percentages,
    get_eye_tracker_html
)
from utils.ai_helper import (
    analyze_resume_ai,
    generate_custom_questions,
    generate_first_question,
    generate_next_question,
    transcribe_audio,
    evaluate_interview_feedback,
    text_to_speech_bytes,
    evaluate_answer_correctness,
    generate_adaptive_question,
    generate_ai_coaching
)

# Start background eye tracking local TCP receiver service
start_eye_tracker_server()

# Load environment variables
load_dotenv(override=True)

def hex_to_rgba(hex_str: str, alpha: float = 0.1) -> str:
    """Converts a standard 3/6-digit hex color to a Plotly-safe rgba string."""
    hex_clean = hex_str.lstrip('#')
    if len(hex_clean) == 3:
        hex_clean = "".join(c * 2 for c in hex_clean)
    r = int(hex_clean[0:2], 16)
    g = int(hex_clean[2:4], 16)
    b = int(hex_clean[4:6], 16)
    return f"rgba({r}, {g}, {b}, {alpha})"


# Page configuration
st.set_page_config(
    page_title="AI Interview Prep Platform",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styling
inject_custom_css()

# ── Authentication Setup ──────────────────────────────────────────────────
_auth_config_path = os.path.join(os.path.dirname(__file__), "auth_config.yaml")
with open(_auth_config_path) as f:
    _auth_config = yaml.load(f, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    _auth_config["credentials"],
    _auth_config["cookie"]["name"],
    _auth_config["cookie"]["key"],
    _auth_config["cookie"]["expiry_days"],
)

# Render login/register widget if not authenticated
auth_status = st.session_state.get("authentication_status")

# Initialize login mode state
if "auth_mode" not in st.session_state:
    st.session_state.auth_mode = "Login"

if not auth_status:
    st.markdown("""
    <div style='text-align:center;padding:30px 0 10px;'>
        <div style='font-size:3rem;'>🎙️</div>
        <h2 style='color:#818CF8;margin:0;'>AI Interview Prep Platform</h2>
        <p style='color:#9CA3AF;margin-top:8px;'>Please sign in or create an account to start</p>
    </div>""", unsafe_allow_html=True)

    auth_mode = st.radio(
        "Action Selection",
        ["🔑 Login", "📝 Create Account"],
        index=0 if st.session_state.auth_mode == "Login" else 1,
        horizontal=True,
        label_visibility="collapsed"
    )

    if auth_mode == "🔑 Login":
        st.session_state.auth_mode = "Login"
        authenticator.login()
        if st.session_state.get("authentication_status") is False:
            st.error("❌ Username or password is incorrect.")
            st.markdown("""
            <div style='background:rgba(255,255,255,0.03);padding:10px;border-radius:6px;border:1px solid rgba(255,255,255,0.08);margin-top:10px;'>
                <strong style='color:#818CF8;'>Default System Credentials:</strong><br/>
                💼 <strong>Admin:</strong> <code>admin</code> / <code>Admin@123</code><br/>
                🎓 <strong>Candidate:</strong> <code>candidate</code> / <code>Demo@123</code>
            </div>""", unsafe_allow_html=True)
        elif st.session_state.get("authentication_status") is None:
            st.markdown("""
            <div style='background:rgba(255,255,255,0.03);padding:10px;border-radius:6px;border:1px solid rgba(255,255,255,0.08);margin-top:10px;'>
                <strong style='color:#818CF8;'>Default System Credentials:</strong><br/>
                💼 <strong>Admin:</strong> <code>admin</code> / <code>Admin@123</code><br/>
                🎓 <strong>Candidate:</strong> <code>candidate</code> / <code>Demo@123</code>
            </div>""", unsafe_allow_html=True)

    else:
        st.session_state.auth_mode = "Register"
        try:
            # Renders register form
            reg_result = authenticator.register_user(captcha=False)
            if reg_result:
                email_reg, username_reg, name_reg = reg_result
                if email_reg:
                    # Set role to candidate for new registrations
                    _auth_config["credentials"]["usernames"][username_reg]["role"] = "candidate"
                    with open(_auth_config_path, "w") as f:
                        yaml.dump(_auth_config, f, default_flow_style=False)
                    
                    # Programmatic redirect: set status to Login and reload
                    st.session_state.auth_mode = "Login"
                    st.toast("🎉 Account created successfully! Redirecting to login page...", icon="✅")
                    st.rerun()
        except Exception as e:
            st.error(f"Error creating account: {e}")
            
    st.stop()

auth_name   = st.session_state.get("name", "")
auth_user   = st.session_state.get("username", "")

# Register user on first login
register_user(auth_user, auth_name, role=_auth_config["credentials"]["usernames"].get(auth_user, {}).get("role", "candidate"))


# Initialize session state variables
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home"
# Initialize api_key from environment variables if not already set by user
if "demo_mode" not in st.session_state:
    st.session_state.demo_mode = False
if "api_key" not in st.session_state or not st.session_state.api_key:
    env_key = os.getenv("GEMINI_API_KEY", "").strip().strip("'\"")
    if env_key and env_key not in ["YOUR_GEMINI_API_KEY", "your_actual_copied_key_here"]:
        st.session_state.api_key = env_key
    else:
        st.session_state.api_key = ""
if "interview_started" not in st.session_state:
    st.session_state.interview_started = False
if "interview_complete" not in st.session_state:
    st.session_state.interview_complete = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "current_question_idx" not in st.session_state:
    st.session_state.current_question_idx = 0
if "total_questions" not in st.session_state:
    st.session_state.total_questions = 5
if "role" not in st.session_state:
    st.session_state.role = "Software Engineer"
if "level" not in st.session_state:
    st.session_state.level = "Mid-level"
if "resume_summary" not in st.session_state:
    st.session_state.resume_summary = ""
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "uploaded_filename" not in st.session_state:
    st.session_state.uploaded_filename = None
if "uploaded_file_bytes" not in st.session_state:
    st.session_state.uploaded_file_bytes = None
if "custom_questions" not in st.session_state:
    st.session_state.custom_questions = []
if "skills" not in st.session_state:
    st.session_state.skills = []
if "projects" not in st.session_state:
    st.session_state.projects = []
if "education" not in st.session_state:
    st.session_state.education = []
if "experience" not in st.session_state:
    st.session_state.experience = []
if "certifications" not in st.session_state:
    st.session_state.certifications = []
if "soft_skills" not in st.session_state:
    st.session_state.soft_skills = []
if "technical_skills" not in st.session_state:
    st.session_state.technical_skills = []
if "candidate_profile" not in st.session_state:
    st.session_state.candidate_profile = ""
if "evaluation_results" not in st.session_state:
    st.session_state.evaluation_results = None
if "recorder_key" not in st.session_state:
    st.session_state.recorder_key = 0
if "current_answer_text" not in st.session_state:
    st.session_state.current_answer_text = ""
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = 0
if "waiting_for_next" not in st.session_state:
    st.session_state.waiting_for_next = False
if "job_description" not in st.session_state:
    st.session_state.job_description = ""
if "last_played_question_idx" not in st.session_state:
    st.session_state.last_played_question_idx = -1
if "current_difficulty" not in st.session_state:
    st.session_state.current_difficulty = "Beginner"
if "interview_format" not in st.session_state:
    st.session_state.interview_format = "Standard Q&A"
if "programming_language" not in st.session_state:
    st.session_state.programming_language = "Python"
if "recruiter_candidates" not in st.session_state:
    st.session_state.recruiter_candidates = []
if "candidate_name" not in st.session_state:
    st.session_state.candidate_name = "Anonymous"
if "interview_history" not in st.session_state:
    st.session_state.interview_history = []
if "coaching_result" not in st.session_state:
    st.session_state.coaching_result = None
if "difficulty_history" not in st.session_state:
    st.session_state.difficulty_history = []
if "evaluations_history" not in st.session_state:
    st.session_state.evaluations_history = []
if "eye_contact_tracked" not in st.session_state:
    st.session_state.eye_contact_tracked = {"looking_at_screen": 100, "looking_away": 0, "reading_paper": 0}
# Initialize user's unique eye tracker session key
session_id = get_session_id()
if "current_page" not in st.session_state:
    st.session_state.current_page = "🏠 Home"

# Sidebar settings
with st.sidebar:
    st.markdown("# 🎙️ AI Interview Prep")
    st.markdown("Prepare for your dream role with interactive AI-powered mock interviews.")
    st.markdown("---")
    
    # API key setup (from .env or user input override)
    api_key_input = st.text_input(
        "Enter Gemini API Key",
        value=st.session_state.api_key,
        type="password",
        help="Get your key from https://aistudio.google.com/ or configure it in .env"
    )
    if api_key_input != st.session_state.api_key:
        st.session_state.api_key = api_key_input.strip().strip("'\"")
        st.success("API Key updated!")
        
    st.markdown("---")
    
    # Demo Mode toggle
    st.session_state.demo_mode = st.toggle(
        "Demo Mode (No API Key) 🧪",
        value=st.session_state.demo_mode,
        help="Test the interview interface and custom features with pre-configured realistic mock data."
    )
    
    st.markdown("---")
    
    # Navigation
    st.markdown("### Navigation")
    if not st.session_state.api_key and not st.session_state.demo_mode:
        st.warning("⚠️ Set API key or enable Demo Mode")
    elif st.session_state.demo_mode:
        st.info("🧪 Running in Demo Mode (Mock AI)")
        
    # Show user info
    st.markdown(f"<div style='font-size:0.85rem;color:#9CA3AF;margin-bottom:4px;'>👤 Logged in as <strong style='color:#818CF8;'>{auth_name}</strong></div>", unsafe_allow_html=True)

    _is_admin = _auth_config["credentials"]["usernames"].get(auth_user, {}).get("role") == "admin"
    _base_pages = ["🏠 Home", "📊 Dashboard & Setup", "🎙️ Mock Interview", "📈 Performance Feedback", "🏢 Recruiter Dashboard", "📜 Interview History", "📈 Analytics", "🔬 Skill Intelligence"]
    _admin_pages = ["🔐 Admin Panel"]
    page_options = _base_pages + (_admin_pages if _is_admin else [])
    if st.session_state.current_page not in page_options:
        st.session_state.current_page = page_options[0]
        
    nav_option = st.radio(
        "Go to",
        page_options,
        index=page_options.index(st.session_state.current_page)
    )
    if nav_option != st.session_state.current_page:
        st.session_state.current_page = nav_option
        st.rerun()
    
    st.markdown("---")
    if st.sidebar.button("🔄 Reset Platform", use_container_width=True):
        st.session_state.interview_started = False
        st.session_state.interview_complete = False
        st.session_state.chat_history = []
        st.session_state.current_question_idx = 0
        st.session_state.resume_summary = ""
        st.session_state.resume_text = ""
        st.session_state.uploaded_filename = None
        st.session_state.uploaded_file_bytes = None
        st.session_state.custom_questions = []
        st.session_state.skills = []
        st.session_state.projects = []
        st.session_state.education = []
        st.session_state.experience = []
        st.session_state.certifications = []
        st.session_state.soft_skills = []
        st.session_state.technical_skills = []
        st.session_state.candidate_profile = ""
        st.session_state.evaluation_results = None
        st.session_state.current_answer_text = ""
        st.session_state.last_audio_hash = 0
        st.session_state.waiting_for_next = False
        st.session_state.job_description = ""
        st.session_state.last_played_question_idx = -1
        st.session_state.current_difficulty = "Beginner"
        st.session_state.difficulty_history = []
        st.session_state.evaluations_history = []
        st.session_state.current_page = "🏠 Home"
        st.rerun()

    st.markdown("---")
    authenticator.logout("🚪 Logout", "sidebar")


# ----------------- PAGE 0: HOME -----------------
if nav_option == "🏠 Home":
    st.markdown("""
    <div class="hero-section">
        <div class="main-title">AI Interview Preparation Platform</div>
        <div class="subtitle">Tailored resumes, voice feedback, and deep performance metrics powered by Gemini</div>
    </div>
    """, unsafe_allow_html=True)
    
    col_cta1, col_cta2, col_cta3 = st.columns([1, 2, 1])
    with col_cta2:
        if st.button("Get Started Now 🚀", type="primary", use_container_width=True):
            st.session_state.current_page = "📊 Dashboard & Setup"
            st.rerun()

    # Animated Statistics
    st.markdown("""
    <div class="metric-container" style="margin-top: 50px;">
        <div class="metric-card" style="animation: fadeInUp 1.2s ease-out;">
            <div class="metric-value">98%</div>
            <div class="metric-label">Success Rate</div>
        </div>
        <div class="metric-card" style="animation: fadeInUp 1.4s ease-out;">
            <div class="metric-value">10k+</div>
            <div class="metric-label">Mock Interviews</div>
        </div>
        <div class="metric-card" style="animation: fadeInUp 1.6s ease-out;">
            <div class="metric-value">50+</div>
            <div class="metric-label">Roles Supported</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Why Choose Our Platform
    st.markdown("<h3 style='text-align: center; margin-top: 60px;'>Why Choose Our Platform?</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card">
            <span class="feature-icon">🎙️</span>
            <h4>Real-time Voice AI</h4>
            <p style="color: #9CA3AF; font-size: 0.9rem;">Practice with a conversational AI that listens and responds instantly using native browser speech recognition.</p>
        </div>
        <div class="feature-card">
            <span class="feature-icon">📈</span>
            <h4>Adaptive Difficulty</h4>
            <p style="color: #9CA3AF; font-size: 0.9rem;">Questions dynamically scale from Beginner to Advanced based on your on-the-fly answers.</p>
        </div>
        <div class="feature-card">
            <span class="feature-icon">🧠</span>
            <h4>Deep Skill Analytics</h4>
            <p style="color: #9CA3AF; font-size: 0.9rem;">Receive radar chart scorecards, gap analysis, and tailored 4-week learning roadmaps.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Companies Supported
    st.markdown("""
    <div class="company-marquee-container">
        <div class="company-marquee">
            <span class="company-logo">Google</span>
            <span class="company-logo">Meta</span>
            <span class="company-logo">Amazon</span>
            <span class="company-logo">Netflix</span>
            <span class="company-logo">Microsoft</span>
            <span class="company-logo">Apple</span>
            <span class="company-logo">Tesla</span>
            <!-- Repeat for seamless scroll -->
            <span class="company-logo">Google</span>
            <span class="company-logo">Meta</span>
            <span class="company-logo">Amazon</span>
            <span class="company-logo">Netflix</span>
            <span class="company-logo">Microsoft</span>
            <span class="company-logo">Apple</span>
            <span class="company-logo">Tesla</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Testimonials
    st.markdown("<h3 style='text-align: center; margin-top: 30px;'>Success Stories</h3>", unsafe_allow_html=True)
    st.markdown("""
    <div class="testimonial-grid">
        <div class="testimonial-card">
            "The adaptive difficulty perfectly simulated my final-round interview at Meta. The system design questions were incredibly realistic!"
            <div class="testimonial-author">Sarah J. <br/><span>Senior Software Engineer</span></div>
        </div>
        <div class="testimonial-card">
            "I used the skill gap analysis to identify my weakness in caching strategies. Two weeks later, I got the job."
            <div class="testimonial-author">Michael T. <br/><span>Backend Developer</span></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Platform User Guidelines Section ──
    st.markdown("<hr style='border:1px solid rgba(255,255,255,0.08);margin-top:50px;margin-bottom:40px;'/>", unsafe_allow_html=True)
    st.markdown("<h3 style='text-align: center; color: #F3F4F6;'>📖 Platform User Guidelines & Walkthrough</h3>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9CA3AF; font-size: 0.95rem; margin-bottom: 30px;'>Step-by-step instructions to configure and navigate all modules of the platform successfully</p>", unsafe_allow_html=True)

    g1, g2, g3 = st.columns(3, gap="medium")

    with g1:
        st.markdown("""
        <div style='background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px;min-height:220px;'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>
                <span style='background:#818CF8;color:white;width:28px;height:28px;border-radius:50%;display:flex;justify-content:center;align-items:center;font-weight:700;font-size:0.9rem;'>1</span>
                <strong style='color:#F3F4F6;font-size:1.05rem;'>Configure & Setup</strong>
            </div>
            <ul style='color:#9CA3AF;font-size:0.88rem;padding-left:18px;margin:0;'>
                <li style='margin-bottom:8px;'>Go to the <strong>📊 Dashboard & Setup</strong> tab.</li>
                <li style='margin-bottom:8px;'>Upload your <strong>Resume (PDF)</strong> for automatic skill parsing.</li>
                <li style='margin-bottom:8px;'>Provide a target <strong>Job Description (JD)</strong> or keep the default software engineering track.</li>
                <li style='margin-bottom:8px;'>Enter your <strong>Gemini API Key</strong> in the sidebar, or enable <strong>Demo Mode 🧪</strong> to proceed instantly.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with g2:
        st.markdown("""
        <div style='background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px;min-height:220px;'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>
                <span style='background:#34D399;color:white;width:28px;height:28px;border-radius:50%;display:flex;justify-content:center;align-items:center;font-weight:700;font-size:0.9rem;'>2</span>
                <strong style='color:#F3F4F6;font-size:1.05rem;'>Interview & Gaze</strong>
            </div>
            <ul style='color:#9CA3AF;font-size:0.88rem;padding-left:18px;margin:0;'>
                <li style='margin-bottom:8px;'>Click <strong>🚀 Start Mock Interview</strong> to load the mock room.</li>
                <li style='margin-bottom:8px;'>Grant camera access for the <strong>👁️ Eye Contact Tracker</strong> to log focus metrics.</li>
                <li style='margin-bottom:8px;'>In <strong>Standard Q&A</strong>, record audio responses. In <strong>Technical Coding</strong>, write code in the Ace Editor.</li>
                <li style='margin-bottom:8px;'>Submit your answer to check correctness and view the <strong>🧠 AI Coach</strong> lessons.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    with g3:
        st.markdown("""
        <div style='background:rgba(30,41,59,0.4);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:20px;min-height:220px;'>
            <div style='display:flex;align-items:center;gap:10px;margin-bottom:12px;'>
                <span style='background:#EC4899;color:white;width:28px;height:28px;border-radius:50%;display:flex;justify-content:center;align-items:center;font-weight:700;font-size:0.9rem;'>3</span>
                <strong style='color:#F3F4F6;font-size:1.05rem;'>Feedback & Roadmaps</strong>
            </div>
            <ul style='color:#9CA3AF;font-size:0.88rem;padding-left:18px;margin:0;'>
                <li style='margin-bottom:8px;'>Go to <strong>📈 Performance Feedback</strong> to view metrics and overall hiring outcomes.</li>
                <li style='margin-bottom:8px;'>Explore <strong>📈 Analytics</strong> for Plotly trend charts, radar charts, and eye gaze logs.</li>
                <li style='margin-bottom:8px;'>Visit <strong>🔬 Skill Intelligence</strong> for interactive network graphs, gap analyses, and curated YouTube/Book roadmap links.</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

# ----------------- PAGE 1: DASHBOARD & SETUP -----------------
elif nav_option == "📊 Dashboard & Setup":
    st.markdown("<div class='main-title' style='font-size: 2.2rem !important;'>Dashboard & Setup</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Configure your interview parameters and upload your resume</div>", unsafe_allow_html=True)
    if not st.session_state.api_key and not st.session_state.demo_mode:
        st.info(
            "👋 **To begin, please enter your Gemini API Key in the sidebar.**\n\n"
            "**Alternatively, you can configure your key in the `.env` file:**\n"
            "1. Open `.env` and paste your key: `GEMINI_API_KEY=your_actual_key`\n"
            "2. Or run this command in your project terminal:\n"
            "```bash\n"
            "python set_api_key.py YOUR_GEMINI_API_KEY\n"
            "```\n\n"
            "💡 *Don't have an API Key?* You can toggle **Demo Mode (No API Key) 🧪** in the sidebar to try out all the features using realistic mock AI data!"
        )
    
    col1, col2 = st.columns([1, 1], gap="large")
    
    with col1:
        with st.container(border=True):
            st.markdown("### ⚙️ Interview Configuration")
            
            role = st.selectbox(
                "Target Job Role",
                ["Software Engineer", "Frontend Developer", "Backend Developer", "Data Scientist", 
                 "Product Manager", "UX Designer", "DevOps Engineer", "Business Analyst", "Marketing Manager"],
                key="role"
            )
            
            st.text_input(
                "Candidate Name (for Recruiter Dashboard)",
                key="candidate_name",
                placeholder="e.g. Alice Chen"
            )
            
            level = st.selectbox(
                "Experience Level",
                ["Junior", "Mid-level", "Senior", "Lead / Manager"],
                key="level"
            )
            
            interview_format = st.selectbox(
                "Interview Format",
                ["Standard Q&A", "Technical Coding"],
                key="interview_format"
            )
            
            if st.session_state.interview_format == "Technical Coding":
                programming_language = st.selectbox(
                    "Programming Language",
                    ["Python", "Java", "C++", "SQL"],
                    key="programming_language"
                )
            
            total_questions = st.slider(
                "Number of Interview Questions",
                min_value=3, max_value=8, key="total_questions"
            )
            
            job_description = st.text_area(
                "Target Job Description (Required) 🏢",
                key="job_description",
                placeholder="Paste target job responsibilities, company name, and requirements here to align the questions..."
            )
        
    with col2:
        with st.container(border=True):
            st.markdown("### 📄 Resume Analysis")
            st.markdown("Upload your resume in PDF format to receive custom resume-tailored questions.")
            
            uploaded_file = st.file_uploader("Upload PDF Resume", type=["pdf"])
            
            if uploaded_file is not None:
                # Store name and bytes if this is a new file upload
                if st.session_state.uploaded_filename != uploaded_file.name or st.session_state.uploaded_file_bytes is None:
                    st.session_state.uploaded_file_bytes = uploaded_file.read()
                    st.session_state.uploaded_filename = uploaded_file.name
                    # Reset analysis output to force re-analysis on new upload
                    st.session_state.resume_summary = ""
                    st.session_state.resume_text = ""
                    st.session_state.candidate_profile = ""
                    st.session_state.projects = []
                    st.session_state.education = []
                    st.session_state.experience = []
                    st.session_state.certifications = []
                    st.session_state.soft_skills = []
                    st.session_state.technical_skills = []
                    st.session_state.skills = []
                    st.session_state.custom_questions = []

                if not st.session_state.api_key and not st.session_state.demo_mode:
                    st.error("Please enter a Gemini API Key or enable Demo Mode to proceed.")
                else:
                    # Rerun analysis if the API key is present/demo mode is active but we don't have analysis results yet
                    if not st.session_state.resume_summary:
                        with st.spinner("Parsing and analyzing resume..."):
                            resume_text = parse_pdf_resume(st.session_state.uploaded_file_bytes)
                            
                            if resume_text:
                                analysis = analyze_resume_ai(
                                    api_key=st.session_state.api_key,
                                    resume_text=resume_text,
                                    job_description=job_description,
                                    demo_mode=st.session_state.demo_mode
                                )
                                
                                if analysis.get("success", False):
                                    st.session_state.candidate_profile = analysis.get("candidate_profile", "")
                                    st.session_state.resume_summary = analysis.get("candidate_profile", "") # backward compatibility
                                    st.session_state.resume_text = resume_text
                                    st.session_state.projects = analysis.get("projects", [])
                                    st.session_state.education = analysis.get("education", [])
                                    st.session_state.experience = analysis.get("experience", [])
                                    st.session_state.certifications = analysis.get("certifications", [])
                                    st.session_state.soft_skills = analysis.get("soft_skills", [])
                                    st.session_state.technical_skills = analysis.get("technical_skills", [])
                                    st.session_state.skills = analysis.get("skills", [])
                                    st.session_state.custom_questions = analysis.get("suggested_questions", [])
                                    st.rerun()
                                else:
                                    error_msg = analysis.get("error_message", "Unknown error occurred during API call.")
                                    st.error(f"⚠️ AI Resume Analysis failed: {error_msg}")
                                    st.info("Please make sure your Gemini API Key in the sidebar or .env file is correct, active, and has access to Gemini models.")
                                    # Reset states on failure
                                    st.session_state.resume_summary = ""
                                    st.session_state.resume_text = ""
                                    st.session_state.candidate_profile = ""
                                    st.session_state.projects = []
                                    st.session_state.education = []
                                    st.session_state.experience = []
                                    st.session_state.certifications = []
                                    st.session_state.soft_skills = []
                                    st.session_state.technical_skills = []
                                    st.session_state.skills = []
                                    st.session_state.custom_questions = []
                            else:
                                st.error("Failed to parse text from the PDF. Please make sure it's a readable text PDF.")

                    # Show previous successful analysis output
                    if st.session_state.candidate_profile or st.session_state.resume_summary:
                        st.markdown("<div class='status-banner success'>✅ Resume successfully parsed into Candidate Profile!</div>", unsafe_allow_html=True)
                        st.markdown(f"**Executive Summary:** {st.session_state.candidate_profile or st.session_state.resume_summary}")
                        
                        tab1, tab2, tab3 = st.tabs(["🎯 Skills & Tech", "💼 Experience & Projects", "🎓 Education & Certs"])
                        
                        with tab1:
                            if st.session_state.technical_skills:
                                st.markdown("**Technical Skills:**")
                                st.markdown("".join([f"<span style='background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.technical_skills]), unsafe_allow_html=True)
                            if st.session_state.soft_skills:
                                st.markdown("**Soft Skills:**")
                                st.markdown("".join([f"<span style='background: rgba(236,72,153,0.2); border: 1px solid rgba(236,72,153,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.soft_skills]), unsafe_allow_html=True)
                            if not st.session_state.technical_skills and st.session_state.skills:
                                st.markdown("**General Skills:**")
                                st.markdown("".join([f"<span style='background: rgba(139,92,246,0.2); border: 1px solid rgba(139,92,246,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.skills]), unsafe_allow_html=True)
                        with tab2:
                            if st.session_state.experience:
                                st.markdown("**Experience:**")
                                for exp in st.session_state.experience:
                                    st.markdown(f"- {exp}")
                            if st.session_state.projects:
                                st.markdown("**Key Projects:**")
                                for proj in st.session_state.projects:
                                    st.markdown(f"- {proj}")
                        with tab3:
                            if st.session_state.education:
                                st.markdown("**Education:**")
                                for ed in st.session_state.education:
                                    st.markdown(f"- {ed}")
                            if st.session_state.certifications:
                                st.markdown("**Certifications:**")
                                for cert in st.session_state.certifications:
                                    st.markdown(f"- {cert}")
            elif st.session_state.demo_mode:
                # In Demo Mode, automatically mock resume parsed status if no upload
                if not st.session_state.candidate_profile:
                    st.session_state.candidate_profile = "A highly capable Junior Developer with proven experience in AI-integrated Python architectures."
                    st.session_state.resume_summary = st.session_state.candidate_profile
                    st.session_state.resume_text = "Python Developer with SQL, APIs, and Data structures."
                    st.session_state.projects = ["Interactive Mock Interview System", "E-commerce Backend"]
                    st.session_state.education = ["B.S. Computer Science"]
                    st.session_state.experience = ["Intern at StartupX (6 Months)"]
                    st.session_state.certifications = ["Google Data Analytics Certificate"]
                    st.session_state.soft_skills = ["Teamwork", "Agile Methodologies", "Communication"]
                    st.session_state.technical_skills = ["Python", "SQL", "OOP", "Data Structures", "Django", "REST APIs"]
                    st.session_state.skills = st.session_state.technical_skills
                    st.session_state.custom_questions = [
                        "Tell me about a basic programming project that you've built.",
                        "Explain session state vs local variables in Streamlit.",
                        "How do you design a database schema?"
                    ]
                
                st.markdown("<div class='status-banner success'>✅ Demo Resume Loaded Automatically!</div>", unsafe_allow_html=True)
                st.markdown(f"**Executive Summary:** {st.session_state.candidate_profile or st.session_state.resume_summary}")
                
                tab1, tab2, tab3 = st.tabs(["🎯 Skills & Tech", "💼 Experience & Projects", "🎓 Education & Certs"])
                
                with tab1:
                    if st.session_state.technical_skills:
                        st.markdown("**Technical Skills:**")
                        st.markdown("".join([f"<span style='background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.technical_skills]), unsafe_allow_html=True)
                    if st.session_state.soft_skills:
                        st.markdown("**Soft Skills:**")
                        st.markdown("".join([f"<span style='background: rgba(236,72,153,0.2); border: 1px solid rgba(236,72,153,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.soft_skills]), unsafe_allow_html=True)
                    if not st.session_state.technical_skills and st.session_state.skills:
                        st.markdown("**General Skills:**")
                        st.markdown("".join([f"<span style='background: rgba(139,92,246,0.2); border: 1px solid rgba(139,92,246,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.skills]), unsafe_allow_html=True)
                with tab2:
                    if st.session_state.experience:
                        st.markdown("**Experience:**")
                        for exp in st.session_state.experience:
                            st.markdown(f"- {exp}")
                    if st.session_state.projects:
                        st.markdown("**Key Projects:**")
                        for proj in st.session_state.projects:
                            st.markdown(f"- {proj}")
                with tab3:
                    if st.session_state.education:
                        st.markdown("**Education:**")
                        for ed in st.session_state.education:
                            st.markdown(f"- {ed}")
                    if st.session_state.certifications:
                        st.markdown("**Certifications:**")
                        for cert in st.session_state.certifications:
                            st.markdown(f"- {cert}")
            else:
                # If demo mode is disabled and there is no uploaded file, reset mock resume summary
                if st.session_state.uploaded_filename is None and st.session_state.resume_summary == "Junior/Mid Software Developer with experience in Python, SQL, OOP, and backend frameworks.":
                    st.session_state.resume_summary = ""
                    st.session_state.resume_text = ""
                    st.session_state.skills = []
                    st.session_state.custom_questions = []
                st.warning("🔒 No resume uploaded. Please upload a PDF resume and paste a target job description to unlock the mock interview room.")

    # Start Button
    st.markdown("---")
    start_col1, start_col2, start_col3 = st.columns([1, 2, 1])
    with start_col2:
        is_disabled = not st.session_state.resume_summary or not st.session_state.job_description.strip()
        if is_disabled:
            st.warning("🔒 Please upload your resume AND paste a target job description above to unlock the mock interview room.")
        if st.button("🚀 Start Mock Interview", use_container_width=True, type="primary", disabled=is_disabled):
            if not st.session_state.api_key and not st.session_state.demo_mode:
                st.error("You must enter your Gemini API Key or enable Demo Mode to start.")
            else:
                with st.spinner("Preparing your custom adaptive interview questions..."):
                    # Map the initial level to difficulty
                    if st.session_state.level == "Junior":
                        start_difficulty = "Beginner"
                    elif st.session_state.level == "Mid-level":
                        start_difficulty = "Intermediate"
                    else:
                        start_difficulty = "Advanced"
                    
                    st.session_state.current_difficulty = start_difficulty
                    st.session_state.difficulty_history = [start_difficulty]
                    st.session_state.evaluations_history = []
                    st.session_state.custom_questions = []
                    
                    # Generate the first question matching starting difficulty
                    first_q = generate_adaptive_question(
                        api_key=st.session_state.api_key,
                        role=st.session_state.role,
                        level=st.session_state.level,
                        chat_history=[],
                        current_difficulty=st.session_state.current_difficulty,
                        resume_text=st.session_state.resume_text,
                        job_description=st.session_state.job_description,
                        interview_format=st.session_state.interview_format,
                        programming_language=st.session_state.programming_language,
                        demo_mode=st.session_state.demo_mode
                    )
                    
                    st.session_state.chat_history = [{"role": "ai", "text": first_q}]
                    st.session_state.current_question_idx = 1
                    st.session_state.interview_started = True
                    st.session_state.interview_complete = False
                    st.session_state.evaluation_results = None
                    
                    # Update radio selection
                    st.session_state.current_page = "🎙️ Mock Interview"
                    st.rerun()

# ----------------- PAGE 2: MOCK INTERVIEW -----------------
elif nav_option == "🎙️ Mock Interview":
    if not st.session_state.interview_started:
        with st.container(border=True):
            st.markdown("### Interview Not Started")
            st.markdown("Go to the **Dashboard & Setup** tab, configure your parameters, and click **Start Mock Interview**.")
    elif st.session_state.interview_complete:
        with st.container(border=True):
            st.markdown("### Interview Completed")
            st.markdown("You have completed the interview! Go to the **Performance Feedback** tab to view your scores and feedback.")
            if st.button("Go to Performance Feedback", type="primary"):
                st.session_state.current_page = "📈 Performance Feedback"
                st.rerun()
    else:
        # Build timeline HTML for Adaptive Difficulty path
        timeline_items = []
        for i in range(st.session_state.current_question_idx):
            # Retrieve difficulty for this step
            diff = st.session_state.difficulty_history[i] if i < len(st.session_state.difficulty_history) else "Beginner"
            
            # Retrieve rating if answered
            if i < len(st.session_state.evaluations_history):
                eval_item = st.session_state.evaluations_history[i]
                rating = eval_item.get("rating", "Partially Correct")
                if rating == "Correct":
                    badge = "<span style='color: #10B981;'>✔ Correct</span>"
                    bg_glow = "rgba(16, 185, 129, 0.15)"
                    border_color = "rgba(16, 185, 129, 0.4)"
                elif rating == "Incorrect":
                    badge = "<span style='color: #EF4444;'>✘ Wrong/Poor</span>"
                    bg_glow = "rgba(239, 68, 68, 0.15)"
                    border_color = "rgba(239, 68, 68, 0.4)"
                else:
                    badge = "<span style='color: #F59E0B;'>⚡ Partial</span>"
                    bg_glow = "rgba(245, 158, 11, 0.15)"
                    border_color = "rgba(245, 158, 11, 0.4)"
            else:
                badge = "<span style='color: #818CF8;'>🎙️ Current</span>"
                bg_glow = "rgba(129, 140, 248, 0.2)"
                border_color = "rgba(129, 140, 248, 0.5)"
                
            timeline_items.append(
                f'<div style="flex: 1; text-align: center; padding: 8px 12px; background: {bg_glow}; border: 1px solid {border_color}; border-radius: 8px; min-width: 130px; margin: 4px;">'
                f'<div style="font-size: 0.75rem; color: #9CA3AF; text-transform: uppercase; font-weight: bold; letter-spacing: 0.05em;">Q{i+1}: {diff}</div>'
                f'<div style="font-weight: 600; font-size: 0.85rem; margin-top: 4px;">{badge}</div>'
                f'</div>'
            )
            
        separator = "<span style='color: rgba(255, 255, 255, 0.15); font-weight: bold;'>➔</span>"
        timeline_html = (
            f'<div style="display: flex; flex-wrap: wrap; align-items: center; gap: 8px; padding: 12px; background: rgba(30, 41, 59, 0.3); border: 1px solid rgba(255, 255, 255, 0.05); border-radius: 10px; margin-bottom: 20px;">'
            f'{separator.join(timeline_items)}'
            f'</div>'
        )
        st.markdown("##### 📈 Adaptive Difficulty Path")
        st.markdown(timeline_html, unsafe_allow_html=True)

        # Progress Bar
        progress_val = st.session_state.current_question_idx / st.session_state.total_questions
        st.progress(progress_val)
        st.markdown(f"<div style='text-align: right; color: #9CA3AF; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px;'>Question {st.session_state.current_question_idx} of {st.session_state.total_questions} (Difficulty: <strong>{st.session_state.current_difficulty}</strong>)</div>", unsafe_allow_html=True)

        col1, col2 = st.columns([2, 1], gap="medium")
        
        with col1:
            with st.container(border=True):
                st.markdown("### 💬 Interview Dialogue")
                
                # Chat messages display container with scroll
                chat_container = st.container(height=380)
                with chat_container:
                    for msg in st.session_state.chat_history:
                        role_class = "ai" if msg["role"] == "ai" else "user"
                        bubble_text = msg["text"]
                        st.markdown(f"<div class='chat-bubble {role_class}'>{bubble_text}</div>", unsafe_allow_html=True)
            
        with col2:
            # 👁️ Live Eye Contact Tracker Webcam (Phase 13 / Research Contribution)
            with st.container(border=True):
                st.markdown("### 👁️ Focus & Eye Tracker")
                st.components.v1.html(get_eye_tracker_html(session_id), height=255, scrolling=False)
                
                # Fetch live status from TCP backend
                current_status = get_current_eye_status(session_id)
                if current_status == "Looking at screen":
                    st.success("🟢 Gaze: Focused on screen")
                elif current_status == "Looking away":
                    st.warning("🟡 Gaze: Looking away — please focus!")
                elif current_status == "Reading from paper":
                    st.error("🔴 Gaze: Reading from paper/notes!")

            if st.session_state.waiting_for_next:
                with st.container(border=True):
                    st.markdown("### ➡️ Ready for Next Question?")
                    
                    # Show last answer evaluation detail if available
                    if st.session_state.evaluations_history:
                        last_eval = st.session_state.evaluations_history[-1]
                        rating = last_eval.get("rating", "Partially Correct")
                        reason = last_eval.get("reason", "")
                        if rating == "Correct":
                            alert_icon = "🟢"
                            rating_color = "#34D399"
                        elif rating == "Incorrect":
                            alert_icon = "🔴"
                            rating_color = "#F87171"
                        else:
                            alert_icon = "🟡"
                            rating_color = "#FBBF24"
                        st.markdown(f"""
                        <div style="background: rgba(255, 255, 255, 0.03); border-left: 4px solid {rating_color}; border-radius: 4px; padding: 10px 14px; margin-bottom: 15px;">
                            <strong style="color: {rating_color};">{alert_icon} AI Eval: {rating}</strong><br/>
                            <span style="font-size: 0.88rem; color: #D1D5DB;">{reason}</span>
                        </div>
                        """, unsafe_allow_html=True)

                        # ── AI Coach Panel ──────────────────────────
                        if st.session_state.coaching_result:
                            coach = st.session_state.coaching_result
                            st.markdown("---")
                            st.markdown("### 🧠 AI Coach")

                            # 1. Correct Answer
                            st.markdown(f"""
                            <div style='background:rgba(16,185,129,0.08);border-left:4px solid #10B981;border-radius:6px;padding:12px 16px;margin-bottom:10px;'>
                                <div style='color:#34D399;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>✅ Correct Answer Approach</div>
                                <div style='color:#E5E7EB;font-size:0.93rem;'>{coach.get('correct_answer','')}</div>
                            </div>""", unsafe_allow_html=True)

                            # 2. Why
                            st.markdown(f"""
                            <div style='background:rgba(99,102,241,0.08);border-left:4px solid #6366F1;border-radius:6px;padding:12px 16px;margin-bottom:10px;'>
                                <div style='color:#818CF8;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>💡 Why This Works</div>
                                <div style='color:#E5E7EB;font-size:0.93rem;'>{coach.get('why','')}</div>
                            </div>""", unsafe_allow_html=True)

                            # 3. Common Mistakes
                            mistakes = coach.get("common_mistakes", [])
                            mistakes_html = "".join(f"<li style='margin-bottom:4px;color:#E5E7EB;'>{m}</li>" for m in mistakes)
                            st.markdown(f"""
                            <div style='background:rgba(239,68,68,0.07);border-left:4px solid #EF4444;border-radius:6px;padding:12px 16px;margin-bottom:10px;'>
                                <div style='color:#F87171;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:6px;'>⚠️ Common Mistakes</div>
                                <ul style='margin:0;padding-left:18px;font-size:0.9rem;'>{mistakes_html}</ul>
                            </div>""", unsafe_allow_html=True)

                            # 4. How Recruiters Think
                            st.markdown(f"""
                            <div style='background:rgba(245,158,11,0.08);border-left:4px solid #F59E0B;border-radius:6px;padding:12px 16px;margin-bottom:10px;'>
                                <div style='color:#FBBF24;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>🎯 How Recruiters Think</div>
                                <div style='color:#E5E7EB;font-size:0.93rem;'>{coach.get('recruiter_perspective','')}</div>
                            </div>""", unsafe_allow_html=True)

                            # 5. Sample Best Answer
                            st.markdown(f"""
                            <div style='background:rgba(236,72,153,0.08);border-left:4px solid #EC4899;border-radius:6px;padding:12px 16px;margin-bottom:10px;'>
                                <div style='color:#F472B6;font-weight:700;font-size:0.82rem;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:4px;'>⭐ Sample Best Answer</div>
                                <div style='color:#E5E7EB;font-size:0.9rem;font-style:italic;line-height:1.6;'>{coach.get('sample_best_answer','')}</div>
                            </div>""", unsafe_allow_html=True)
                    
                    st.info("Your response has been submitted successfully! Take a breath, and click below when you're ready to proceed.")
                    
                    col_next1, col_next2 = st.columns([1, 1])
                    with col_next1:
                        if st.button("Proceed to Next ➡️", type="primary", use_container_width=True):
                            with st.spinner("Generating next question..."):
                                next_q = generate_adaptive_question(
                                    api_key=st.session_state.api_key,
                                    role=st.session_state.role,
                                    level=st.session_state.level,
                                    chat_history=st.session_state.chat_history,
                                    current_difficulty=st.session_state.current_difficulty,
                                    resume_text=st.session_state.resume_text,
                                    job_description=st.session_state.job_description,
                                    interview_format=st.session_state.interview_format,
                                    programming_language=st.session_state.programming_language,
                                    demo_mode=st.session_state.demo_mode
                                )
                                # Acknowledge last answer in the AI text
                                last_eval = st.session_state.evaluations_history[-1] if st.session_state.evaluations_history else {}
                                eval_rating = last_eval.get("rating", "Partially Correct")
                                
                                transition_prefix = ""
                                if eval_rating == "Correct":
                                    transition_prefix = "Great answer! Let's step up the difficulty. "
                                elif eval_rating == "Incorrect":
                                    transition_prefix = "Understood. Let's try a different concept to check your background. "
                                else:
                                    transition_prefix = "Thanks for the explanation. Let's proceed. "
                                
                                final_ai_text = f"{transition_prefix}{next_q}"
                                
                                st.session_state.chat_history.append({"role": "ai", "text": final_ai_text})
                                st.session_state.difficulty_history.append(st.session_state.current_difficulty)
                                st.session_state.current_question_idx += 1
                                st.session_state.waiting_for_next = False
                                st.session_state.current_answer_text = ""
                                st.session_state.recorder_key += 1
                                st.session_state.coaching_result = None
                                st.rerun()
                    with col_next2:
                        if st.button("End Early & Evaluate 📊", use_container_width=True):
                            st.session_state.interview_complete = True
                            st.session_state.current_page = "📈 Performance Feedback"
                            st.rerun()
            else:
                # 🤖 AI Voice Assistant Container
                with st.container(border=True):
                    st.markdown("### 🤖 AI Voice Assistant")
                    if st.session_state.chat_history:
                        latest_ai_msg = ""
                        for msg in reversed(st.session_state.chat_history):
                            if msg["role"] == "ai":
                                latest_ai_msg = msg["text"]
                                break
                        
                        if latest_ai_msg:
                            audio_bytes = text_to_speech_bytes(latest_ai_msg)
                            if audio_bytes:
                                should_autoplay = (st.session_state.last_played_question_idx != st.session_state.current_question_idx)
                                st.audio(audio_bytes, format="audio/mp3", autoplay=should_autoplay)
                                if should_autoplay:
                                    st.session_state.last_played_question_idx = st.session_state.current_question_idx
                                    st.rerun()
                            else:
                                st.warning("🔇 Speech synthesis unavailable.")

                with st.container(border=True):
                    if st.session_state.interview_format == "Technical Coding":
                        st.markdown(f"### 💻 Code Editor ({st.session_state.programming_language})")
                        
                        # Map programming languages to Ace Editor modes
                        lang_map = {
                            "Python": "python",
                            "Java": "java",
                            "C++": "c_cpp",
                            "SQL": "sql"
                        }
                        mode = lang_map.get(st.session_state.programming_language, "python")
                        
                        current_typed_text = st_ace(
                            value=st.session_state.current_answer_text,
                            language=mode,
                            theme="monokai",
                            keybinding="vscode",
                            font_size=14,
                            tab_size=4,
                            show_gutter=True,
                            show_print_margin=False,
                            wrap=True,
                            auto_update=True,
                            readonly=False,
                            min_lines=15,
                            key=f"ace_editor_{st.session_state.recorder_key}"
                        )
                    else:
                        st.markdown("### 🎙️ Record or Type Answer")
                        
                        # Sub-mode selection
                        input_mode = st.radio("Input Mode", ["Voice Recording", "Text Input"], horizontal=True)
                        
                        if input_mode == "Voice Recording":
                            st.markdown("<div class='recorder-wrapper'>", unsafe_allow_html=True)
                            st.markdown("<div class='recorder-title'>Voice Recorder</div>", unsafe_allow_html=True)
                            
                            # Native audio input widget
                            audio_file = st.audio_input(
                                "Record Response 🎙️",
                                key=f"recorder_{st.session_state.recorder_key}"
                            )
                            
                            if audio_file is not None:
                                audio_bytes = audio_file.read()
                                audio_hash = hash(audio_bytes)
                                if audio_hash != st.session_state.last_audio_hash:
                                    with st.spinner("Transcribing audio..."):
                                        transcription = transcribe_audio(st.session_state.api_key, audio_bytes)
                                        if not transcription.startswith("[Transcription failed"):
                                            st.session_state.current_answer_text = transcription
                                            st.session_state.last_audio_hash = audio_hash
                                            st.rerun()
                                        else:
                                            st.error(transcription)
                            
                            st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Display text area for review or manual typing with a dynamic key
                        current_typed_text = st.text_area(
                            "Your Answer:",
                            value=st.session_state.current_answer_text,
                            key=f"current_answer_widget_{st.session_state.recorder_key}",
                            height=150,
                            placeholder="Type your answer here or record using the voice recorder above..."
                        )
                    
                    # Action Buttons
                    col_btn1, col_btn2 = st.columns([1, 1])
                    with col_btn1:
                        # Submit Answer
                        is_last_q = st.session_state.current_question_idx >= st.session_state.total_questions
                        btn_label = "Complete Interview 🏁" if is_last_q else "Submit Answer ➡️"
                        
                        if st.button(btn_label, type="primary", use_container_width=True):
                            if not current_typed_text.strip():
                                st.error("Please record or type an answer before submitting.")
                            else:
                                # Save candidate answer
                                st.session_state.chat_history.append({"role": "user", "text": current_typed_text})
                                
                                # Run the evaluation on the response
                                with st.spinner("AI is evaluating your response..."):
                                    eval_result = evaluate_answer_correctness(
                                        api_key=st.session_state.api_key,
                                        question=st.session_state.chat_history[-2]["text"],
                                        answer=current_typed_text,
                                        interview_format=st.session_state.interview_format,
                                        demo_mode=st.session_state.demo_mode
                                    )
                                st.session_state.evaluations_history.append(eval_result)
                                
                                # Adjust difficulty
                                rating = eval_result.get("rating", "Partially Correct")
                                prev_difficulty = st.session_state.current_difficulty
                                
                                if rating == "Correct":
                                    if prev_difficulty == "Beginner":
                                        st.session_state.current_difficulty = "Intermediate"
                                    elif prev_difficulty == "Intermediate":
                                        st.session_state.current_difficulty = "Advanced"
                                elif rating == "Incorrect":
                                    if prev_difficulty == "Advanced":
                                        st.session_state.current_difficulty = "Intermediate"
                                    elif prev_difficulty == "Intermediate":
                                        st.session_state.current_difficulty = "Beginner"
                                
                                if is_last_q:
                                    # Complete interview
                                    st.session_state.interview_complete = True
                                    st.session_state.current_answer_text = ""
                                    st.session_state.recorder_key += 1
                                    st.session_state.current_page = "📈 Performance Feedback"
                                    st.rerun()
                                else:
                                    # Generate coaching for wrong/partial answers
                                    if rating in ["Incorrect", "Partially Correct"]:
                                        with st.spinner("🧠 AI Coach is preparing your feedback..."):
                                            st.session_state.coaching_result = generate_ai_coaching(
                                                api_key=st.session_state.api_key,
                                                question=st.session_state.chat_history[-2]["text"],
                                                answer=current_typed_text,
                                                rating=rating,
                                                demo_mode=st.session_state.demo_mode
                                            )
                                    else:
                                        st.session_state.coaching_result = None
                                    st.session_state.waiting_for_next = True
                                    st.rerun()
                    with col_btn2:
                        if st.button("End Early & Evaluate", use_container_width=True):
                            if len(st.session_state.chat_history) < 2:
                                st.error("You need to answer at least one question to evaluate.")
                            else:
                                st.session_state.interview_complete = True
                                st.session_state.current_answer_text = ""
                                st.session_state.recorder_key += 1
                                st.session_state.current_page = "📈 Performance Feedback"
                                st.rerun()

# ----------------- PAGE 3: PERFORMANCE FEEDBACK -----------------
elif nav_option == "📈 Performance Feedback":
    if not st.session_state.interview_complete:
        with st.container(border=True):
            st.markdown("### Feedback Not Ready")
            st.markdown("Feedback will be available once you complete your mock interview.")
            if st.session_state.interview_started:
                if st.button("Return to Mock Interview"):
                    st.session_state.current_page = "🎙️ Mock Interview"
                    st.rerun()
            else:
                if st.button("Configure Setup"):
                    st.session_state.current_page = "📊 Dashboard & Setup"
                    st.rerun()
    else:
        # Load feedback if not already processed
        if st.session_state.evaluation_results is None:
            with st.spinner("AI is evaluating your interview transcript and generating metrics. This might take a few moments..."):
                st.session_state.evaluation_results = evaluate_interview_feedback(
                    api_key=st.session_state.api_key,
                    role=st.session_state.role,
                    level=st.session_state.level,
                    chat_history=st.session_state.chat_history,
                    resume_profile=st.session_state.candidate_profile or st.session_state.resume_summary,
                    demo_mode=st.session_state.demo_mode
                )
                
                # Fetch eye tracking percentages from the tracker module
                eye_percentages = get_eye_contact_percentages(session_id)
                st.session_state.evaluation_results["eye_contact"] = eye_percentages
                
                # ── Auto-save to Recruiter Dashboard ──
                add_candidate(
                    eval_data=st.session_state.evaluation_results,
                    candidate_name=st.session_state.get("candidate_name", "Anonymous") or "Anonymous",
                    role=st.session_state.role
                )
                # ── Auto-save to Interview History ──
                add_session(
                    eval_data=st.session_state.evaluation_results,
                    role=st.session_state.role
                )
                st.rerun()
        
        eval_data = st.session_state.evaluation_results
        raw_scores = eval_data.get("scores", {})
        
        # Coerce values to integers to prevent errors
        # Coerce values to integers to prevent errors
        scores = {}
        for key in ["resume_score", "interview_score", "communication", "technical_knowledge", "problem_solving", "confidence", "hiring_probability"]:
            try:
                # Provide a reasonable fallback if not generated
                scores[key] = int(raw_scores.get(key, 75))
            except Exception:
                scores[key] = 75
                
        insights = eval_data.get("recruiter_insights", {})
        recommended_role = insights.get("recommended_role", st.session_state.role)
        expected_salary = insights.get("expected_salary", "N/A")
        final_recommendation = insights.get("final_recommendation", "Consider")
        
        # Recommendation Banner
        banner_color = "rgba(16, 185, 129, 0.15)" # Green
        border_color = "rgba(16, 185, 129, 0.4)"
        text_color = "#10B981"
        if "No" in final_recommendation or "Reject" in final_recommendation:
            banner_color = "rgba(239, 68, 68, 0.15)" # Red
            border_color = "rgba(239, 68, 68, 0.4)"
            text_color = "#EF4444"
        elif "Waitlist" in final_recommendation or "Consider" in final_recommendation:
            banner_color = "rgba(245, 158, 11, 0.15)" # Yellow
            border_color = "rgba(245, 158, 11, 0.4)"
            text_color = "#F59E0B"
            
        st.markdown(f"""
        <div style='background: {banner_color}; border: 1px solid {border_color}; border-radius: 12px; padding: 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;'>
            <div>
                <h3 style='margin: 0; color: #F3F4F6;'>Recruiter Recommendation: <span style='color: {text_color}; font-weight: 800;'>{final_recommendation}</span></h3>
                <p style='margin: 5px 0 0 0; color: #9CA3AF; font-size: 1.1rem;'>Target: {recommended_role} | Expected Comp: {expected_salary}</p>
            </div>
            <div style='text-align: right;'>
                <div style='font-size: 0.9rem; color: #9CA3AF;'>Hiring Probability</div>
                <div style='font-size: 2.5rem; font-weight: 800; color: {text_color}; line-height: 1;'>{scores.get('hiring_probability')}%</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display score cards
        st.markdown(f"""
        <div class='metric-container'>
            <div class='metric-card'>
                <div class='metric-value'>{scores.get('resume_score')}%</div>
                <div class='metric-label'>Resume Score</div>
            </div>
            <div class='metric-card'>
                <div class='metric-value'>{scores.get('technical_knowledge')}%</div>
                <div class='metric-label'>Technical Skills</div>
            </div>
            <div class='metric-card'>
                <div class='metric-value'>{scores.get('communication')}%</div>
                <div class='metric-label'>Communication</div>
            </div>
            <div class='metric-card'>
                <div class='metric-value'>{scores.get('problem_solving')}%</div>
                <div class='metric-label'>Problem Solving</div>
            </div>
            <div class='metric-card' style='background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4);'>
                <div class='metric-value' style='background: linear-gradient(135deg, #EC4899, #818CF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{scores.get('interview_score')}%</div>
                <div class='metric-label' style='color: #A5B4FC; font-weight: bold;'>Interview Score</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.markdown("### 📊 Performance Analytics")
                
                # Interactive Plotly Radar / Polar Chart
                categories = ['Technical Skills', 'Communication', 'Confidence', 'Problem Solving', 'Interview Score']
                score_values = [
                    scores.get('technical_knowledge'),
                    scores.get('communication'),
                    scores.get('confidence'),
                    scores.get('problem_solving'),
                    scores.get('interview_score')
                ]
                
                fig = go.Figure()
                fig.add_trace(go.Scatterpolar(
                    r=score_values + [score_values[0]],
                    theta=categories + [categories[0]],
                    fill='toself',
                    fillcolor='rgba(99, 102, 241, 0.2)',
                    line=dict(color='#6366F1', width=2),
                    marker=dict(color='#EC4899', size=6)
                ))
                
                fig.update_layout(
                    polar=dict(
                        radialaxis=dict(
                            visible=True,
                            range=[0, 100],
                            gridcolor='rgba(255,255,255,0.08)',
                            angle=0,
                            tickfont=dict(color='#9CA3AF')
                        ),
                        angularaxis=dict(
                            gridcolor='rgba(255,255,255,0.08)',
                            tickfont=dict(color='#F3F4F6', size=11)
                        ),
                        bgcolor='rgba(0,0,0,0)'
                    ),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#F3F4F6', family='Outfit'),
                    showlegend=False,
                    height=350,
                    margin=dict(l=60, r=60, t=30, b=30)
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # 👁️ Eye Contact Analytics Card (Phase 13 / Research Contribution)
            with st.container(border=True):
                st.markdown("### 👁️ Eye Contact & Attention Analysis")
                eye_stats = eval_data.get("eye_contact", {"looking_at_screen": 85, "looking_away": 10, "reading_paper": 5})
                
                scr = eye_stats.get("looking_at_screen", 85)
                away = eye_stats.get("looking_away", 10)
                paper = eye_stats.get("reading_paper", 5)
                
                st.progress(scr / 100, text=f"🟢 Focused on Screen: {scr}%")
                st.progress(away / 100, text=f"🟡 Looking Away: {away}%")
                st.progress(paper / 100, text=f"🔴 Reading from Paper: {paper}%")
                
                st.markdown("<div style='margin-top: 12px;'></div>", unsafe_allow_html=True)
                if scr >= 80:
                    st.success("✔ Excellent eye contact! You maintained strong focus on the screen throughout the interview.")
                elif paper > away:
                    st.warning("⚠ Attention Alert: You spent significant time looking down. Avoid reading directly from notes to show confidence.")
                else:
                    st.warning("⚠ Attention Alert: You looked away frequently. Try to maintain consistent eye contact with the screen/camera to show engagement.")
            
        with col2:
            with st.container(border=True):
                st.markdown("### 📝 Overall Summary")
                st.markdown(eval_data.get("overall_summary", "No summary generated."))
                st.markdown("---")
                st.markdown("#### Key Recommendations")
                
                # If recommendations are not explicitly in gap analysis, show fallback list
                gap_recs = eval_data.get("skill_gap_analysis", {}).get("recommended_learning_path", [])
                if gap_recs:
                    for rec in gap_recs:
                        st.markdown(f"- {rec}")
                else:
                    st.markdown("- **Refine technical vocabulary:** Make sure to explain key abstractions clearly using correct terminology.")
                    st.markdown("- **Structure responses:** Use methods like STAR (Situation, Task, Action, Result) for behavioral questions.")
                    st.markdown("- **Quantify achievements:** Where possible, list metrics and outcomes in your project explanations.")

        # AI Skill Gap Analysis section
        st.markdown("### 🎯 AI Skill Gap Analysis")
        gap_data = eval_data.get("skill_gap_analysis", {
            "strengths": ["Core Concepts", "Communication Skills"],
            "weaknesses": ["System Architecture"],
            "recommended_learning_path": ["Practice coding mocks"]
        })
        
        col_gap1, col_gap2, col_gap3 = st.columns([1, 1, 1.2], gap="medium")
        
        with col_gap1:
            with st.container(border=True):
                st.markdown("##### 🟢 Strengths")
                for s in gap_data.get("strengths", []):
                    st.markdown(f"<div style='color: #34D399; font-weight: 500; margin-bottom: 6px;'>✔ {s}</div>", unsafe_allow_html=True)
                    
        with col_gap2:
            with st.container(border=True):
                st.markdown("##### 🔴 Weaknesses")
                for w in gap_data.get("weaknesses", []):
                    st.markdown(f"<div style='color: #F87171; font-weight: 500; margin-bottom: 6px;'>✘ {w}</div>", unsafe_allow_html=True)
                    
        with col_gap3:
            with st.container(border=True):
                st.markdown("##### 🗺️ Recommended Learning Path")
                for p in gap_data.get("recommended_learning_path", []):
                    st.markdown(f"<div style='color: #60A5FA; font-weight: 500; margin-bottom: 6px;'>➔ {p}</div>", unsafe_allow_html=True)

        # AI Learning Roadmap section
        st.markdown("### 📅 AI Learning Roadmap")
        roadmap_data = eval_data.get("learning_roadmap", [
            {"week": "Week 1", "topic": "Fundamentals"},
            {"week": "Week 2", "topic": "Coding Practice"},
            {"week": "Week 3", "topic": "System Design"},
            {"week": "Week 4", "topic": "Mock Interview Again"}
        ])
        
        col_road1, col_road2, col_road3, col_road4 = st.columns([1, 1, 1, 1], gap="small")
        cols = [col_road1, col_road2, col_road3, col_road4]
        
        for idx, item in enumerate(roadmap_data[:4]):
            with cols[idx]:
                st.markdown(f"""
                <div style="background: rgba(30, 41, 59, 0.5); border: 1px solid rgba(99, 102, 241, 0.3); border-radius: 12px; padding: 18px 12px; text-align: center; box-shadow: 0 4px 12px rgba(0,0,0,0.15); min-height: 120px; display: flex; flex-direction: column; justify-content: center; align-items: center;">
                    <div style="color: #818CF8; font-weight: bold; font-size: 0.9rem; text-transform: uppercase; margin-bottom: 6px;">{item.get('week', f'Week {idx+1}')}</div>
                    <div style="color: #F3F4F6; font-size: 0.95rem; font-weight: 500; line-height: 1.4;">{item.get('topic', 'Focus Topic')}</div>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("---")
            
        # Question-by-question breakdown
        st.markdown("### 🔍 Question-by-Question Breakdown")
        breakdown = eval_data.get("breakdown", [])
        
        for idx, item in enumerate(breakdown):
            with st.expander(f"Question {idx+1}: {item.get('question', 'N/A')[:90]}...", expanded=(idx == 0)):
                st.markdown(f"**Interviewer Question:**\n>{item.get('question', 'N/A')}")
                st.markdown(f"**Your Answer:**\n*{item.get('candidate_answer', 'N/A')}*")
                st.markdown(f"**Critique:**\n{item.get('critique', 'N/A')}")
                st.markdown(f"**Rating Explanation:**\n{item.get('rating_explanation', 'N/A')}")
                
                # Model Answer box styled beautifully
                st.markdown(f"""
                <div style='background: rgba(16, 185, 129, 0.08); border-left: 4px solid #10B981; border-radius: 4px; padding: 12px 18px; margin-top: 15px;'>
                    <strong style='color: #34D399;'>Suggested Exemplary Answer:</strong><br/>
                    {item.get('model_answer', 'N/A')}
                </div>
                """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE 4 : RECRUITER DASHBOARD
# ─────────────────────────────────────────────────────────────
elif nav_option == "🏢 Recruiter Dashboard":
    st.markdown("<div class='main-title' style='font-size:2.2rem!important;'>🏢 Recruiter Dashboard</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Rank, compare and download reports for all interviewed candidates</div>", unsafe_allow_html=True)

    candidates = get_candidates(demo_mode=st.session_state.demo_mode)

    # ── Top KPI bar ──────────────────────────────────────────
    total   = len(candidates)
    hires   = sum(1 for c in candidates if "Hire" in c["final_recommendation"] and "No" not in c["final_recommendation"])
    avg_prob = int(sum(c["hiring_probability"] for c in candidates) / total) if total else 0

    k1, k2, k3, k4 = st.columns(4, gap="medium")
    kpi_data = [
        (k1, str(total), "Total Candidates"),
        (k2, str(hires), "Recommended Hires"),
        (k3, f"{avg_prob}%", "Avg Hire Probability"),
        (k4, candidates[0]["name"] if candidates else "—", "Top Candidate"),
    ]
    for col, val, label in kpi_data:
        with col:
            st.markdown(f"""
            <div class='recruiter-stat'>
                <div class='stat-value'>{val}</div>
                <div class='stat-label'>{label}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("---")

    if not candidates:
        st.info("No candidates yet. Complete a mock interview to see results here, or enable **Demo Mode** to see sample data.")
    else:
        # ── Ranked Candidate Table ────────────────────────────
        st.markdown("### 📋 Candidate Rankings")

        for rank, c in enumerate(candidates, 1):
            rec = c["final_recommendation"]
            if "No" in rec or "Reject" in rec:
                pill_cls, pill_icon = "pill-reject", "✘"
            elif "Waitlist" in rec or "Consider" in rec:
                pill_cls, pill_icon = "pill-wait", "⏳"
            else:
                pill_cls, pill_icon = "pill-hire", "✔"

            if rank == 1:   badge = f"<span style='font-size:1.4rem'>🥇</span>"
            elif rank == 2: badge = f"<span style='font-size:1.4rem'>🥈</span>"
            elif rank == 3: badge = f"<span style='font-size:1.4rem'>🥉</span>"
            else:           badge = f"<span style='color:#9CA3AF;font-weight:700;'>#{rank}</span>"

            top_chips  = "".join(f"<span class='skill-chip chip-green'>{s}</span>" for s in c.get("top_skills", [])[:4])
            weak_chips = "".join(f"<span class='skill-chip chip-red'>{w}</span>"   for w in c.get("weak_skills", [])[:3])

            with st.expander(f"  {c['name']}  ·  {c['role']}  ·  Hire Probability: {c['hiring_probability']}%", expanded=(rank == 1)):
                col_a, col_b, col_c = st.columns([0.5, 3, 1.5], gap="medium")
                with col_a:
                    st.markdown(badge, unsafe_allow_html=True)
                with col_b:
                    st.markdown(f"""
                    <table style='width:100%;border-collapse:collapse;color:#E5E7EB;font-size:0.9rem;'>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Resume Score</td>
                        <td style='padding:4px 8px;font-weight:700;color:#818CF8;'>{c['resume_score']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Interview Score</td>
                        <td style='padding:4px 8px;font-weight:700;color:#C084FC;'>{c['interview_score']}%</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Technical</td>
                        <td style='padding:4px 8px;font-weight:700;color:#60A5FA;'>{c['technical_knowledge']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Communication</td>
                        <td style='padding:4px 8px;font-weight:700;color:#34D399;'>{c['communication']}%</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Problem Solving</td>
                        <td style='padding:4px 8px;font-weight:700;color:#FBBF24;'>{c['problem_solving']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Recommended Role</td>
                        <td style='padding:4px 8px;font-weight:600;'>{c['recommended_role']}</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Expected Salary</td>
                        <td style='padding:4px 8px;font-weight:600;'>{c['expected_salary']}</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Eye Contact</td>
                        <td style='padding:4px 8px;font-weight:700;color:#34D399;'>🟢 {c.get('eye_contact', {}).get('looking_at_screen', 85)}% Focused</td>
                      </tr>
                    </table>
                    """, unsafe_allow_html=True)
                with col_c:
                    st.markdown(f"<span class='hire-pill {pill_cls}'>{pill_icon} {rec}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:12px;'>{top_chips}</div>",  unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:6px;'>{weak_chips}</div>",  unsafe_allow_html=True)

        # ── Skill Comparison Chart ────────────────────────────
        st.markdown("---")
        st.markdown("### 📊 Skill Comparison Chart")

        names  = [c["name"] for c in candidates]
        fig = go.Figure()
        metrics = {
            "Technical":        ("technical_knowledge", "#60A5FA"),
            "Communication":    ("communication",       "#34D399"),
            "Problem Solving":  ("problem_solving",     "#FBBF24"),
            "Resume Score":     ("resume_score",        "#818CF8"),
        }
        for label, (key, color) in metrics.items():
            fig.add_trace(go.Bar(
                name=label,
                x=names,
                y=[c[key] for c in candidates],
                marker_color=color,
                opacity=0.85,
            ))

        fig.update_layout(
            barmode="group",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.05)", range=[0, 105]),
            margin=dict(l=10, r=10, t=30, b=10),
            height=380,
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Download CSV ──────────────────────────────────────
        st.markdown("---")
        col_dl, col_clr = st.columns([2, 1], gap="medium")
        with col_dl:
            csv_data = to_csv(candidates)
            st.download_button(
                label="⬇️ Download Full Candidate Report (CSV)",
                data=csv_data,
                file_name="recruiter_report.csv",
                mime="text/csv",
                use_container_width=True,
                type="primary"
            )
        with col_clr:
            if st.button("🗑️ Clear All Candidates", use_container_width=True):
                clear_store()
                st.success("Candidate registry cleared.")
                st.rerun()

# ─────────────────────────────────────────────────────────────
# PAGE 5 : INTERVIEW HISTORY
# ─────────────────────────────────────────────────────────────
elif nav_option == "📜 Interview History":
    st.markdown("<div class='main-title' style='font-size:2.2rem!important;'>📜 Interview History</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Track your progress and improvement across every practice session</div>", unsafe_allow_html=True)

    history = get_history(demo_mode=st.session_state.demo_mode)

    if not history:
        st.info("No interview history yet. Complete a mock interview to start tracking your progress, or enable **Demo Mode** to see a sample progression arc.")
    else:
        n = len(history)

        # ── Summary KPI bar ──────────────────────────────────
        first, last = history[0], history[-1]
        comm_delta  = last["communication"]      - first["communication"]
        tech_delta  = last["technical_knowledge"] - first["technical_knowledge"]
        prob_delta  = last["problem_solving"]    - first["problem_solving"]
        conf_delta  = last["confidence"]         - first["confidence"]

        def _arrow(d):
            return ("🟢 +" if d >= 0 else "🔴 ") + str(d) + "%"

        k1, k2, k3, k4, k5 = st.columns(5, gap="small")
        for col, label, val in [
            (k1, "Sessions",        str(n)),
            (k2, "Communication",   _arrow(comm_delta)),
            (k3, "Technical",       _arrow(tech_delta)),
            (k4, "Problem Solving", _arrow(prob_delta)),
            (k5, "Confidence",      _arrow(conf_delta)),
        ]:
            with col:
                st.markdown(f"""
                <div class='recruiter-stat'>
                    <div class='stat-value' style='font-size:1.6rem;'>{val}</div>
                    <div class='stat-label'>{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Progress Line Chart ──────────────────────────────
        st.markdown("### 📈 Performance Progress Over Time")

        labels = [s["label"] for s in history]
        fig_line = go.Figure()

        for key, name, color in TRACKED_METRICS:
            vals = [s[key] for s in history]
            fig_line.add_trace(go.Scatter(
                x=labels,
                y=vals,
                mode="lines+markers+text",
                name=name,
                line=dict(color=color, width=3),
                marker=dict(size=10, color=color,
                            line=dict(color="#0F172A", width=2)),
                text=[f"{v}%" for v in vals],
                textposition="top center",
                textfont=dict(color=color, size=11),
            ))

        fig_line.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)", showline=False),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", range=[0, 110]),
            margin=dict(l=10, r=10, t=40, b=10),
            height=420,
            hovermode="x unified",
        )
        st.plotly_chart(fig_line, use_container_width=True)

        st.markdown("---")

        # ── Per-metric Improvement Arrows ───────────────────
        st.markdown("### 🎯 Score Progression by Skill")
        
        for key, name, color in TRACKED_METRICS:
            vals = [s[key] for s in history]
            col_name, *score_cols = st.columns([1.2] + [1]*len(vals), gap="small")
            with col_name:
                st.markdown(f"<div style='color:{color};font-weight:700;padding-top:14px;font-size:0.95rem;'>{name}</div>", unsafe_allow_html=True)
            for i, (col, val) in enumerate(zip(score_cols, vals)):
                with col:
                    if i == 0:
                        arrow_html = ""
                    else:
                        delta = val - vals[i-1]
                        arrow_color = "#10B981" if delta >= 0 else "#EF4444"
                        arrow_sym   = "▲" if delta >= 0 else "▼"
                        arrow_html  = f"<div style='color:{arrow_color};font-size:0.8rem;text-align:center;'>{arrow_sym} {abs(delta)}%</div>"
                    st.markdown(f"""
                    <div style='background:rgba(30,41,59,0.6);border:1px solid rgba(255,255,255,0.07);
                         border-radius:10px;padding:10px 8px;text-align:center;'>
                        {arrow_html}
                        <div style='font-size:1.5rem;font-weight:800;color:{color};'>{val}%</div>
                        <div style='font-size:0.72rem;color:#6B7280;'>{history[i]["label"]}</div>
                    </div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Session Cards Timeline ───────────────────────────
        st.markdown("### 🗂️ Session-by-Session Breakdown")

        for s in reversed(history):
            rec = s["final_recommendation"]
            if "No" in rec or "Reject" in rec:
                badge_color = "#EF4444"
            elif "Waitlist" in rec or "Consider" in rec:
                badge_color = "#F59E0B"
            else:
                badge_color = "#10B981"

            top_chips  = "".join(f"<span class='skill-chip chip-green'>{sk}</span>" for sk in s.get("top_skills",  [])[:4])
            weak_chips = "".join(f"<span class='skill-chip chip-red'>{sk}</span>"   for sk in s.get("weak_skills", [])[:3])

            with st.expander(f"📅 {s['label']}  ·  {s['date']}  ·  Overall: {s['interview_score']}%", expanded=(s["session"] == history[-1]["session"])):
                c1, c2 = st.columns([2, 1], gap="large")
                with c1:
                    st.markdown(f"**Role:** {s['role']}")
                    if s.get("summary"):
                        st.markdown(f"> {s['summary']}")
                    st.markdown(f"""
                    <table style='width:100%;border-collapse:collapse;color:#E5E7EB;font-size:0.88rem;margin-top:8px;'>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Communication</td>
                        <td style='font-weight:700;color:#34D399;'>{s['communication']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Technical</td>
                        <td style='font-weight:700;color:#60A5FA;'>{s['technical_knowledge']}%</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Problem Solving</td>
                        <td style='font-weight:700;color:#FBBF24;'>{s['problem_solving']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Confidence</td>
                        <td style='font-weight:700;color:#C084FC;'>{s['confidence']}%</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Resume Score</td>
                        <td style='font-weight:700;color:#818CF8;'>{s['resume_score']}%</td>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Hire Probability</td>
                        <td style='font-weight:700;color:#EC4899;'>{s['hiring_probability']}%</td>
                      </tr>
                      <tr>
                        <td style='padding:4px 8px;color:#9CA3AF;'>Eye Contact Focus</td>
                        <td style='font-weight:700;color:#10B981;'>{s.get('eye_contact', {}).get('looking_at_screen', 85)}%</td>
                        <td></td><td></td>
                      </tr>
                    </table>""", unsafe_allow_html=True)
                with c2:
                    st.markdown(f"<span style='background:{badge_color}20;color:{badge_color};border:1px solid {badge_color}60;padding:4px 14px;border-radius:20px;font-weight:700;font-size:0.82rem;'>{rec}</span>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:12px;'><strong style='color:#9CA3AF;font-size:0.78rem;'>TOP SKILLS</strong><br/>{top_chips}</div>", unsafe_allow_html=True)
                    st.markdown(f"<div style='margin-top:8px;'><strong style='color:#9CA3AF;font-size:0.78rem;'>NEEDS WORK</strong><br/>{weak_chips}</div>", unsafe_allow_html=True)

        # ── Clear button ─────────────────────────────────────
        st.markdown("---")
        if st.button("🗑️ Clear Interview History", use_container_width=False):
            clear_history()
            st.success("History cleared.")
            st.rerun()

# ─────────────────────────────────────────────────────────────
# PAGE 6 : ANALYTICS  (Phase 9)
# ─────────────────────────────────────────────────────────────
elif nav_option == "📈 Analytics":
    st.markdown("<div class='main-title' style='font-size:2.2rem!important;'>📈 Performance Analytics</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>Deep-dive charts across every interview metric</div>", unsafe_allow_html=True)

    history = get_history(demo_mode=st.session_state.demo_mode)

    if not history:
        st.info("No data yet. Complete a mock interview or enable **Demo Mode** for sample analytics.")
    else:
        labels = [s["label"] for s in history]

        # ── KPI row ───────────────────────────────────────────
        n = len(history)
        last = history[-1]
        k1,k2,k3,k4,k5,k6 = st.columns(6, gap="small")
        for col, label, val, color in [
            (k1, "Sessions",        str(n),                        "#818CF8"),
            (k2, "Avg Interview",   f"{int(sum(s['interview_score'] for s in history)/n)}%", "#34D399"),
            (k3, "Avg Resume",      f"{int(sum(s['resume_score'] for s in history)/n)}%",    "#60A5FA"),
            (k4, "Avg Confidence",  f"{int(sum(s['confidence'] for s in history)/n)}%",      "#FBBF24"),
            (k5, "Avg Technical",   f"{int(sum(s['technical_knowledge'] for s in history)/n)}%", "#EC4899"),
            (k6, "Hire Prob",       f"{last['hiring_probability']}%", "#10B981"),
        ]:
            with col:
                st.markdown(f"""<div class='recruiter-stat'>
                    <div class='stat-value' style='font-size:1.5rem;color:{color};-webkit-text-fill-color:{color};'>{val}</div>
                    <div class='stat-label'>{label}</div></div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Multi-metric area chart ───────────────────────────
        st.markdown("### 📊 All Metrics Over Time")
        fig_area = go.Figure()
        for key, name, color in TRACKED_METRICS:
            vals = [s[key] for s in history]
            fig_area.add_trace(go.Scatter(
                x=labels, y=vals, name=name, mode="lines+markers",
                line=dict(color=color, width=2.5),
                fill="tozeroy", fillcolor=hex_to_rgba(color, 0.08),
                marker=dict(size=8, color=color)
            ))
        fig_area.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Inter"),
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", range=[0,110]),
            height=380, margin=dict(l=10,r=10,t=30,b=10), hovermode="x unified"
        )
        st.plotly_chart(fig_area, use_container_width=True)

        c1, c2 = st.columns(2, gap="medium")

        # ── Radar chart ───────────────────────────────────────
        with c1:
            st.markdown("### 🕸️ Latest Session Radar")
            cats_radar = ["Communication","Technical","Problem Solving","Confidence","Resume Score"]
            vals_radar = [
                last["communication"], last["technical_knowledge"],
                last["problem_solving"], last["confidence"], last["resume_score"]
            ]
            vals_radar += [vals_radar[0]]
            cats_radar += [cats_radar[0]]
            fig_radar = go.Figure(go.Scatterpolar(
                r=vals_radar, theta=cats_radar,
                fill="toself", fillcolor="rgba(99,102,241,0.15)",
                line=dict(color="#818CF8", width=2.5),
                marker=dict(size=7, color="#818CF8")
            ))
            fig_radar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                polar=dict(bgcolor="rgba(0,0,0,0)",
                           radialaxis=dict(visible=True, range=[0,100], color="#6B7280"),
                           angularaxis=dict(color="#9CA3AF")),
                font=dict(color="#E5E7EB"), height=360, margin=dict(l=40,r=40,t=30,b=10)
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        # ── Hiring probability trend ──────────────────────────
        with c2:
            st.markdown("### 🎯 Hiring Probability Trend")
            hp_vals = [s["hiring_probability"] for s in history]
            colors_hp = ["#10B981" if v >= 80 else "#F59E0B" if v >= 60 else "#EF4444" for v in hp_vals]
            fig_hp = go.Figure(go.Bar(
                x=labels, y=hp_vals, marker_color=colors_hp, opacity=0.85,
                text=[f"{v}%" for v in hp_vals], textposition="outside",
                textfont=dict(color="#E5E7EB")
            ))
            fig_hp.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB", family="Inter"),
                xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)", range=[0,115]),
                height=360, margin=dict(l=10,r=10,t=30,b=10)
            )
            st.plotly_chart(fig_hp, use_container_width=True)

        # ── Improvement trend (delta bar) ─────────────────────
        if len(history) >= 2:
            st.markdown("---")
            st.markdown("### 📈 Improvement Trend (First → Last Session)")
            first = history[0]
            metric_keys   = ["communication","technical_knowledge","problem_solving","confidence","interview_score"]
            metric_labels = ["Communication","Technical","Problem Solving","Confidence","Overall Score"]
            deltas = [last[k] - first[k] for k in metric_keys]
            delta_colors = ["#10B981" if d >= 0 else "#EF4444" for d in deltas]
            fig_delta = go.Figure(go.Bar(
                x=metric_labels, y=deltas, marker_color=delta_colors, opacity=0.85,
                text=[f"{'+'if d>=0 else ''}{d}%" for d in deltas],
                textposition="outside", textfont=dict(color="#E5E7EB")
            ))
            fig_delta.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_dash="dash")
            fig_delta.update_layout(
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E5E7EB", family="Inter"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
                height=320, margin=dict(l=10,r=10,t=30,b=10)
            )
            st.plotly_chart(fig_delta, use_container_width=True)

        # ── Eye Contact Trend Chart ───────────────────────────
        st.markdown("---")
        st.markdown("### 👁️ Eye Contact & Attention Trend")
        
        scr_vals = [s.get("eye_contact", {}).get("looking_at_screen", 85) for s in history]
        away_vals = [s.get("eye_contact", {}).get("looking_away", 10) for s in history]
        paper_vals = [s.get("eye_contact", {}).get("reading_paper", 5) for s in history]
        
        fig_eye = go.Figure()
        fig_eye.add_trace(go.Scatter(
            x=labels, y=scr_vals, name="Looking at Screen", mode="lines+markers",
            line=dict(color="#34D399", width=3), marker=dict(size=8)
        ))
        fig_eye.add_trace(go.Scatter(
            x=labels, y=away_vals, name="Looking Away", mode="lines+markers",
            line=dict(color="#FBBF24", width=2, dash="dash"), marker=dict(size=6)
        ))
        fig_eye.add_trace(go.Scatter(
            x=labels, y=paper_vals, name="Reading from Paper", mode="lines+markers",
            line=dict(color="#F87171", width=2, dash="dot"), marker=dict(size=6)
        ))
        
        fig_eye.update_layout(
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#E5E7EB", family="Inter"),
            legend=dict(orientation="h", y=1.05, x=1, xanchor="right"),
            xaxis=dict(gridcolor="rgba(255,255,255,0.06)"),
            yaxis=dict(gridcolor="rgba(255,255,255,0.06)", range=[0, 110]),
            height=320, margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_eye, use_container_width=True)

# ─────────────────────────────────────────────────────────────
# PAGE 7 : SKILL INTELLIGENCE  (Phase 13)
# ─────────────────────────────────────────────────────────────
elif nav_option == "🔬 Skill Intelligence":
    st.markdown("<div class='main-title' style='font-size:2.2rem!important;'>🔬 Skill Intelligence</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>AI-powered skill graph · gap analysis · adaptive difficulty · learning roadmap</div>", unsafe_allow_html=True)

    # Gather skills from session
    all_skills = (
        st.session_state.get("skills", []) +
        st.session_state.get("technical_skills", []) +
        st.session_state.get("soft_skills", [])
    )
    weak_skills = []
    if st.session_state.get("evaluation_results"):
        gap = st.session_state.evaluation_results.get("skill_gap_analysis", {})
        weak_skills = gap.get("weaknesses", [])

    if not all_skills and not st.session_state.demo_mode:
        st.info("Upload your resume on the **Dashboard & Setup** page first, or enable **Demo Mode** to see a sample skill graph.")
    else:
        # Demo skills
        if not all_skills:
            all_skills = ["Python","Django","REST APIs","SQL","PostgreSQL","Docker","AWS",
                          "System Design","Machine Learning","Communication","Leadership",
                          "Data Structures","Algorithms","React","Node.js"]
            weak_skills = ["System Design","Leadership","Distributed Systems"]

        # ── Skill Network Graph ────────────────────────────────
        st.markdown("### 🕸️ Skill Network Graph")
        st.caption("🟢 Green = Strong skill  |  🔴 Red = Weak/Gap skill  |  Large node = Category")
        fig_network = build_skill_network_chart(all_skills, weak_skills)
        st.plotly_chart(fig_network, use_container_width=True)

        st.markdown("---")

        # ── Skill categories breakdown ─────────────────────────
        st.markdown("### 📂 Skills by Category")
        categorized = categorize_skills(all_skills)
        cat_cols = st.columns(min(len(categorized), 4), gap="medium")
        for i, (cat, cat_skills) in enumerate(categorized.items()):
            with cat_cols[i % 4]:
                chips = "".join(f"<span class='skill-chip chip-green'>{s}</span>" for s in cat_skills)
                st.markdown(f"""<div style='background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;min-height:100px;'>
                    <div style='font-size:0.78rem;color:#9CA3AF;font-weight:700;text-transform:uppercase;margin-bottom:8px;'>{cat}</div>
                    {chips}</div>""", unsafe_allow_html=True)

        st.markdown("---")

        # ── Skill Gap vs Job Description ────────────────────────
        st.markdown("### 🎯 Skill Gap Predictor")
        jd = st.session_state.get("job_description", "")
        if not jd:
            jd = "Looking for a Software Engineer with Python, Django, AWS, Docker, System Design, SQL, and communication skills."
        gap_result = predict_skill_gap(all_skills, jd)

        g1, g2, g3 = st.columns(3, gap="medium")
        with g1:
            st.markdown(f"<div class='recruiter-stat'><div class='stat-value' style='color:#10B981;-webkit-text-fill-color:#10B981;'>{gap_result['coverage']}%</div><div class='stat-label'>JD Coverage</div></div>", unsafe_allow_html=True)
        with g2:
            matched_chips = "".join(f"<span class='skill-chip chip-green'>{s}</span>" for s in gap_result["matched"])
            st.markdown(f"<div style='background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;'><div style='color:#34D399;font-weight:700;font-size:0.78rem;margin-bottom:6px;'>✔ MATCHED SKILLS</div>{matched_chips}</div>", unsafe_allow_html=True)
        with g3:
            missing_chips = "".join(f"<span class='skill-chip chip-red'>{s}</span>" for s in gap_result["missing"])
            missing_fallback = missing_chips if missing_chips else "<span style='color:#6B7280;'>None — great coverage!</span>"
            st.markdown(f"<div style='background:rgba(30,41,59,0.5);border:1px solid rgba(255,255,255,0.07);border-radius:12px;padding:14px;'><div style='color:#F87171;font-weight:700;font-size:0.78rem;margin-bottom:6px;'>✘ MISSING SKILLS</div>{missing_fallback}</div>", unsafe_allow_html=True)

        st.markdown("---")

        # ── Adaptive Difficulty Prediction ─────────────────────
        st.markdown("### ⚡ Adaptive Difficulty Prediction")
        skill_scores = {}
        if st.session_state.get("evaluation_results"):
            raw = st.session_state.evaluation_results.get("scores", {})
            skill_scores = {k: int(v) for k, v in raw.items() if isinstance(v, (int, float, str)) and str(v).isdigit()}
        if not skill_scores:
            skill_scores = {"technical_knowledge": 72, "communication": 68, "problem_solving": 65, "confidence": 60}
        predicted = predict_difficulty(skill_scores)
        diff_color = {"Beginner": "#34D399", "Intermediate": "#F59E0B", "Advanced": "#EF4444"}.get(predicted, "#818CF8")
        st.markdown(f"<div class='recruiter-stat' style='max-width:300px;'><div class='stat-value' style='color:{diff_color};-webkit-text-fill-color:{diff_color};'>{predicted}</div><div class='stat-label'>Recommended Difficulty Level</div></div>", unsafe_allow_html=True)

        st.markdown("---")

        # ── Personalised Learning Roadmap (Phase 8) ────────────
        st.markdown("### 📚 Personalized Learning Roadmap")
        st.caption("Resources curated for your weakest skills")
        if not weak_skills:
            weak_skills = ["System Design", "Communication", "Algorithms"]

        from datetime import date, timedelta
        next_interview = (date.today() + timedelta(days=14)).strftime("%d %b %Y")

        for i, skill in enumerate(weak_skills[:5]):
            res = get_resources(skill)
            with st.expander(f"📌 {skill}", expanded=(i == 0)):
                r1, r2, r3 = st.columns(3, gap="medium")
                with r1:
                    st.markdown(f"""<div style='background:rgba(236,72,153,0.08);border:1px solid rgba(236,72,153,0.2);border-radius:10px;padding:14px;'>
                        <div style='color:#F472B6;font-weight:700;font-size:0.8rem;margin-bottom:6px;'>▶ YouTube Playlist</div>
                        <a href='{res["youtube"]}' target='_blank' style='color:#E5E7EB;font-size:0.88rem;text-decoration:none;'>🎬 Watch on YouTube ↗</a></div>""", unsafe_allow_html=True)
                with r2:
                    st.markdown(f"""<div style='background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);border-radius:10px;padding:14px;'>
                        <div style='color:#818CF8;font-weight:700;font-size:0.8rem;margin-bottom:6px;'>📖 Recommended Book</div>
                        <span style='color:#E5E7EB;font-size:0.85rem;'>{res["book"]}</span></div>""", unsafe_allow_html=True)
                with r3:
                    st.markdown(f"""<div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.2);border-radius:10px;padding:14px;'>
                        <div style='color:#34D399;font-weight:700;font-size:0.8rem;margin-bottom:6px;'>💻 Practice Problems</div>
                        <a href='{res["practice"]}' target='_blank' style='color:#E5E7EB;font-size:0.88rem;text-decoration:none;'>🧩 Practice Now ↗</a></div>""", unsafe_allow_html=True)

        st.markdown(f"""<div style='background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:12px;padding:16px 20px;margin-top:20px;display:flex;align-items:center;gap:16px;'>
            <div style='font-size:2rem;'>📅</div>
            <div><div style='color:#FBBF24;font-weight:700;font-size:0.9rem;'>Suggested Next Interview Date</div>
            <div style='color:#E5E7EB;font-size:1.1rem;font-weight:600;margin-top:4px;'>{next_interview}</div>
            <div style='color:#9CA3AF;font-size:0.8rem;'>Based on your current skill gaps — 2 weeks of focused study recommended</div></div>
        </div>""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# PAGE 8 : ADMIN PANEL  (Phase 12)
# ─────────────────────────────────────────────────────────────
elif nav_option == "🔐 Admin Panel":
    if not _is_admin:
        st.error("🔒 Access denied. Admin privileges required.")
        st.stop()

    st.markdown("<div class='main-title' style='font-size:2.2rem!important;'>🔐 Admin Panel</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>System administration · users · questions · reports</div>", unsafe_allow_html=True)

    tab_users, tab_interviews, tab_questions, tab_analytics, tab_export = st.tabs(
        ["👥 Users", "📋 Interviews", "❓ Questions", "📊 Analytics", "📥 Export"])

    # ── Users tab ─────────────────────────────────────────────
    with tab_users:
        st.markdown("### 👥 Registered Users")
        users = load_users()
        if not users:
            st.info("No users registered yet.")
        else:
            for uname, udata in users.items():
                with st.expander(f"👤 {udata.get('name', uname)} (@{uname}) — {udata.get('role','candidate')}"):
                    st.write(f"**Email:** {udata.get('email', 'N/A')}  |  **Registered:** {udata.get('registered','N/A')}  |  **Interviews:** {udata.get('interviews',0)}")
                    if st.button(f"🗑️ Delete {uname}", key=f"del_user_{uname}"):
                        delete_user(uname)
                        st.success(f"User @{uname} deleted.")
                        st.rerun()

    # ── Interviews tab ─────────────────────────────────────────
    with tab_interviews:
        st.markdown("### 📋 All Interview Sessions")
        all_history = ds_load_history()
        if not all_history:
            st.info("No saved interview sessions yet.")
        else:
            for i, session in enumerate(reversed(all_history)):
                st.markdown(f"**Session {len(all_history)-i}** · {session.get('date','N/A')} · {session.get('role','N/A')} · Score: **{session.get('interview_score','?')}%**")

    # ── Questions Bank tab ─────────────────────────────────────
    with tab_questions:
        st.markdown("### ❓ Question Bank")
        with st.form("add_q_form"):
            new_q   = st.text_area("New Question", placeholder="Enter interview question...")
            q_cat   = st.selectbox("Category", ["Technical","Behavioral","System Design","Coding","HR"])
            q_diff  = st.selectbox("Difficulty", ["Beginner","Intermediate","Advanced"])
            if st.form_submit_button("➕ Add Question", type="primary"):
                if new_q.strip():
                    add_question(new_q.strip(), q_cat, q_diff)
                    st.success("Question added!")
                    st.rerun()
        questions = load_questions()
        if questions:
            st.markdown(f"**{len(questions)} questions in bank**")
            for i, q in enumerate(questions):
                with st.expander(f"Q{i+1}: {q['question'][:80]}..."):
                    st.write(f"**Category:** {q['category']}  |  **Difficulty:** {q['difficulty']}  |  **Added:** {q['added'][:10]}")
                    if st.button("🗑️ Delete", key=f"del_q_{i}"):
                        delete_question(i)
                        st.rerun()

    # ── Analytics tab ─────────────────────────────────────────
    with tab_analytics:
        st.markdown("### 📊 System Analytics")
        summary = get_analytics_summary()
        a1,a2,a3 = st.columns(3, gap="medium")
        for col, label, val in [
            (a1, "Total Sessions",   summary["total_sessions"]),
            (a2, "Total Candidates", summary["total_candidates"]),
            (a3, "Registered Users", summary["total_users"]),
        ]:
            with col:
                st.markdown(f"<div class='recruiter-stat'><div class='stat-value'>{val}</div><div class='stat-label'>{label}</div></div>", unsafe_allow_html=True)
        if summary.get("averages"):
            st.markdown("#### Platform Average Scores")
            avgs = summary["averages"]
            for k,v in avgs.items():
                st.progress(v/100, text=f"{k.replace('_',' ').title()}: {v}%")

    # ── Export tab ─────────────────────────────────────────────
    with tab_export:
        st.markdown("### 📥 Export Data")
        candidates = ds_load_candidates()
        csv_data = to_csv(candidates) if candidates else "No candidate data yet."
        st.download_button("⬇️ Download All Candidates (CSV)", data=csv_data, file_name="admin_candidates.csv", mime="text/csv", use_container_width=True, type="primary")
        history_json = ds_load_history()
        import json as _json
        st.download_button("⬇️ Download Interview History (JSON)", data=_json.dumps(history_json, indent=2, default=str), file_name="admin_history.json", mime="application/json", use_container_width=True)
        users_data = load_users()
        st.download_button("⬇️ Download Users (JSON)", data=_json.dumps(users_data, indent=2, default=str), file_name="admin_users.json", mime="application/json", use_container_width=True)
