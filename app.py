import streamlit as st
import os
from dotenv import load_dotenv
import plotly.graph_objects as go

# Import our utility functions
from utils.css_styles import inject_custom_css
from utils.resume_parser import parse_pdf_resume
from utils.ai_helper import (
    analyze_resume_ai,
    generate_custom_questions,
    generate_first_question,
    generate_next_question,
    transcribe_audio,
    evaluate_interview_feedback,
    text_to_speech_bytes,
    evaluate_answer_correctness,
    generate_adaptive_question
)
# Load environment variables
load_dotenv(override=True)

# Page configuration
st.set_page_config(
    page_title="AI Interview Prep Platform",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject custom styling
inject_custom_css()

# Initialize session state variables
if "current_page" not in st.session_state:
    st.session_state.current_page = "📊 Dashboard & Setup"
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
if "difficulty_history" not in st.session_state:
    st.session_state.difficulty_history = []
if "evaluations_history" not in st.session_state:
    st.session_state.evaluations_history = []

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
        
    page_options = ["📊 Dashboard & Setup", "🎙️ Mock Interview", "📈 Performance Feedback"]
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
        st.session_state.evaluation_results = None
        st.session_state.current_answer_text = ""
        st.session_state.last_audio_hash = 0
        st.session_state.waiting_for_next = False
        st.session_state.job_description = ""
        st.session_state.last_played_question_idx = -1
        st.session_state.current_difficulty = "Beginner"
        st.session_state.difficulty_history = []
        st.session_state.evaluations_history = []
        st.session_state.current_page = "📊 Dashboard & Setup"
        st.rerun()

# Title banner
st.markdown("<div class='main-title'>AI Interview Preparation Platform</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Tailored resumes, voice feedback, and deep performance metrics powered by Gemini</div>", unsafe_allow_html=True)

# ----------------- PAGE 1: DASHBOARD & SETUP -----------------
if nav_option == "📊 Dashboard & Setup":
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
            
            level = st.selectbox(
                "Experience Level",
                ["Junior", "Mid-level", "Senior", "Lead / Manager"],
                key="level"
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
                                    st.session_state.resume_summary = analysis.get("experience_summary", "")
                                    st.session_state.resume_text = resume_text
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
                                    st.session_state.skills = []
                                    st.session_state.custom_questions = []
                            else:
                                st.error("Failed to parse text from the PDF. Please make sure it's a readable text PDF.")

                    # Show previous successful analysis output
                    if st.session_state.resume_summary:
                        st.markdown("<div class='status-banner success'>✅ Resume successfully parsed & analyzed!</div>", unsafe_allow_html=True)
                        st.markdown(f"**Profile Summary:** {st.session_state.resume_summary}")
                        
                        # Show parsed skills
                        if st.session_state.skills:
                            st.markdown("**Identified Skills:**")
                            skills_html = "".join([f"<span style='background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.skills])
                            st.markdown(skills_html, unsafe_allow_html=True)
                            
                        # Show parsed suggested questions
                        if st.session_state.custom_questions:
                            st.markdown("**Initial Tailored Questions (from Resume):**")
                            for q in st.session_state.custom_questions:
                                st.markdown(f"- {q}")
            elif st.session_state.demo_mode:
                # In Demo Mode, automatically mock resume parsed status if no upload
                if not st.session_state.resume_summary:
                    st.session_state.resume_summary = "Junior/Mid Software Developer with experience in Python, SQL, OOP, and backend frameworks."
                    st.session_state.resume_text = "Senior Python Software Engineer with SQL, OOP, and data structure experience."
                    st.session_state.skills = ["Python", "SQL", "OOP", "Data Structures", "Django", "REST APIs"]
                    st.session_state.custom_questions = [
                        "Tell me about a basic programming project that you've built.",
                        "Explain session state vs local variables in Streamlit.",
                        "How do you design a database schema?"
                    ]
                
                st.markdown("<div class='status-banner success'>✅ Demo Resume Loaded Automatically!</div>", unsafe_allow_html=True)
                st.markdown(f"**Demo Profile Summary:** {st.session_state.resume_summary}")
                
                # Show parsed skills
                if st.session_state.skills:
                    st.markdown("**Identified Skills:**")
                    skills_html = "".join([f"<span style='background: rgba(99,102,241,0.2); border: 1px solid rgba(99,102,241,0.4); border-radius: 20px; padding: 4px 12px; margin-right: 8px; margin-bottom: 8px; display: inline-block; font-size: 0.85rem;'>{skill}</span>" for skill in st.session_state.skills])
                    st.markdown(skills_html, unsafe_allow_html=True)
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
                    demo_mode=st.session_state.demo_mode
                )
                st.rerun()
        
        eval_data = st.session_state.evaluation_results
        raw_scores = eval_data.get("scores", {})
        
        # Coerce values to integers to prevent errors
        scores = {}
        for key in ["technical", "communication", "confidence", "problem_solving", "overall_readiness"]:
            try:
                # Provide a reasonable fallback if not generated
                fallback_val = 80 if key == "overall_readiness" else 75
                scores[key] = int(raw_scores.get(key, fallback_val))
            except Exception:
                scores[key] = 75
        
        # Display score cards
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('technical')}%</div>
            <div class='metric-label'>Technical Skills</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('communication')}%</div>
            <div class='metric-label'>Communication</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('confidence')}%</div>
            <div class='metric-label'>Confidence</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('problem_solving')}%</div>
            <div class='metric-label'>Problem Solving</div>
        </div>
        <div class='metric-card' style='background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.4);'>
            <div class='metric-value' style='background: linear-gradient(135deg, #EC4899, #818CF8); -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>{scores.get('overall_readiness')}%</div>
            <div class='metric-label' style='color: #A5B4FC; font-weight: bold;'>Overall Readiness</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.markdown("### 📊 Performance Analytics")
                
                # Interactive Plotly Radar / Polar Chart
                categories = ['Technical Skills', 'Communication', 'Confidence', 'Problem Solving', 'Overall Readiness']
                score_values = [
                    scores.get('technical'),
                    scores.get('communication'),
                    scores.get('confidence'),
                    scores.get('problem_solving'),
                    scores.get('overall_readiness')
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
