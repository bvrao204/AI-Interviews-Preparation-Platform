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
    text_to_speech_bytes
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
            else:
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
                with st.spinner("Preparing your custom interview questions..."):
                    # Generate the custom questions based on role, level, full resume text, job description, and count
                    st.session_state.custom_questions = generate_custom_questions(
                        api_key=st.session_state.api_key,
                        role=st.session_state.role,
                        level=st.session_state.level,
                        resume_text=st.session_state.resume_text,
                        job_description=st.session_state.job_description,
                        total_questions=st.session_state.total_questions,
                        demo_mode=st.session_state.demo_mode
                    )
                    
                    # Generate the first question
                    first_q = generate_first_question(
                        api_key=st.session_state.api_key,
                        role=st.session_state.role,
                        level=st.session_state.level,
                        resume_summary=st.session_state.resume_summary,
                        customized_questions=st.session_state.custom_questions,
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
        # Progress Bar
        progress_val = st.session_state.current_question_idx / st.session_state.total_questions
        st.progress(progress_val)
        st.markdown(f"<div style='text-align: right; color: #9CA3AF; font-size: 0.9rem; margin-top: -10px; margin-bottom: 20px;'>Question {st.session_state.current_question_idx} of {st.session_state.total_questions}</div>", unsafe_allow_html=True)

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
                    st.info("Your response has been submitted successfully! Take a breath, and click below when you're ready to proceed.")
                    
                    col_next1, col_next2 = st.columns([1, 1])
                    with col_next1:
                        if st.button("Proceed to Next ➡️", type="primary", use_container_width=True):
                            with st.spinner("Generating next question..."):
                                next_q = generate_next_question(
                                    api_key=st.session_state.api_key,
                                    role=st.session_state.role,
                                    level=st.session_state.level,
                                    chat_history=st.session_state.chat_history,
                                    total_q=st.session_state.total_questions,
                                    current_idx=st.session_state.current_question_idx,
                                    resume_summary=st.session_state.resume_summary,
                                    customized_questions=st.session_state.custom_questions,
                                    demo_mode=st.session_state.demo_mode
                                )
                                st.session_state.chat_history.append({"role": "ai", "text": next_q})
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
                    
                    # Display text area for review or manual typing
                    st.text_area(
                        "Your Answer:",
                        key="current_answer_text",
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
                            if not st.session_state.current_answer_text.strip():
                                st.error("Please record or type an answer before submitting.")
                            else:
                                # Save candidate answer
                                st.session_state.chat_history.append({"role": "user", "text": st.session_state.current_answer_text})
                                
                                if is_last_q:
                                    # Complete interview
                                    st.session_state.interview_complete = True
                                    st.session_state.current_answer_text = ""
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
        raw_scores = eval_data.get("scores", {"technical": 50, "communication": 50, "problem_solving": 50})
        
        # Coerce values to integers to prevent errors
        scores = {}
        for key in ["technical", "communication", "problem_solving"]:
            try:
                scores[key] = int(raw_scores.get(key, 50))
            except Exception:
                scores[key] = 50
        
        # Calculate overall score
        overall_score = round(sum(scores.values()) / len(scores))
        
        # Display score cards
        st.markdown("<div class='metric-container'>", unsafe_allow_html=True)
        
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-value'>{overall_score}%</div>
            <div class='metric-label'>Overall Score</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('technical', 50)}%</div>
            <div class='metric-label'>Technical & Domain</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('communication', 50)}%</div>
            <div class='metric-label'>Communication</div>
        </div>
        <div class='metric-card'>
            <div class='metric-value'>{scores.get('problem_solving', 50)}%</div>
            <div class='metric-label'>Problem Solving</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1], gap="large")
        
        with col1:
            with st.container(border=True):
                st.markdown("### 📊 Performance Analytics")
                
                # Interactive Plotly Radar / Polar Chart
                categories = ['Technical Knowledge', 'Communication', 'Problem Solving']
                score_values = [scores.get('technical', 50), scores.get('communication', 50), scores.get('problem_solving', 50)]
                
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
                st.markdown("- **Refine technical vocabulary:** Make sure to explain key abstractions clearly using correct terminology.")
                st.markdown("- **Structure responses:** Use methods like STAR (Situation, Task, Action, Result) for behavioral questions.")
                st.markdown("- **Quantify achievements:** Where possible, list metrics and outcomes in your project explanations.")
            
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
