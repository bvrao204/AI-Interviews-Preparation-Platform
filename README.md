# AI Interview Preparation Platform 🎙️

An interactive, AI-powered mock interview preparation web application built with **Streamlit**, **Python**, and **Google Gemini API**. Candidates can practice resume-focused or role-specific interviews using text or voice recording, and receive comprehensive evaluations, model answers, and interactive performance analytics.

---

## 🚀 Key Features

- **Custom Mock Interviews**: Generates realistic, non-repetitive interview questions tailored directly to your experience level (Junior, Mid, Senior, Lead) and target job description.
- **Dynamic Difficulty Progression**: Questions progress organically from Easy (resume validation/domain intro) to Medium (practical operational/design) to Hard (system architecture/leadership).
- **Speech-to-Text Integration**: Record responses directly using browser audio inputs, transcribed in real-time by the Gemini multimodal engine.
- **AI Voice Assistant**: Listen to the interviewer ask questions via natural local text-to-speech playback (`pyttsx3`).
- **Comprehensive Scorecards**: Evaluates candidates across three core dimensions (Technical & Domain, Communication, Problem Solving) with interactive Plotly polar radar charts.
- **Detailed Critiques & Model Answers**: Provides question-by-question rating explanations, itemized critiques, and exemplary model answers for learning.
- **Demo Mode**: Allows users to test the entire platform, UI, and workflows using pre-configured mock AI data without needing a Gemini API key.

---

## 🏗️ System Architecture & Workflow

The platform operates on a streamlined 4-step pipeline:

```mermaid
graph TD
    A[Upload Resume PDF & Paste Job Description] --> B[AI Resume Analysis & Skill Extraction]
    B --> C[Tailored Question Bank Generation]
    C --> D[Dialogue Simulation: Speech / Text Input & Text-to-Speech Output]
    D --> E[Gemini 2.5 Pro Evaluation & Scorecard]
    E --> F[Plotly Analytics Dashboard & Model Answers]
```

1. **Resume Processing**: The uploaded PDF is parsed using `pypdf`, extracting raw text from document pages.
2. **AI Analysis**: `gemini-2.5-flash` analyzes the resume text alongside target job criteria to extract key skills and draft a high-level experience profile.
3. **Dialogue & Session Management**: Streamlit manages session states for the interview loop. A dark glassmorphic styling system is injected using CSS. Custom audio recordings are transcribed using Gemini's native audio parsing.
4. **Grading & Evaluation**: At the end of the interview, the chat history is analyzed by `gemini-2.5-pro` to generate performance scores, a breakdown of strengths, growth areas, and suggested stellar answers.

---

## 📂 Project Structure

```
AI-Interviews-Preparation-Platform/
├── .env                  # Stores your private Google Gemini API Key
├── .env.example          # Template environment file
├── .gitignore            # Ensures virtual environments (.venv) and API keys are not pushed to Git
├── README.md             # Project documentation (this file)
├── requirements.txt      # Python package requirements
├── app.py                # Main Streamlit application entrypoint (UI & page layout)
├── set_api_key.py        # Command-line utility to automatically configure your API key
└── utils/                # Helper utilities and modules
    ├── ai_helper.py      # Core Gemini API wrapper functions (questions, transcribing, grading, TTS)
    ├── css_styles.py     # High-end dark glassmorphic custom CSS injections
    └── resume_parser.py  # PDF text extraction wrapper using pypdf
```

---

## 🛠️ Tech Stack

- **Frontend/UI**: [Streamlit](https://streamlit.io/) (Python-based interactive web framework)
- **AI Core**: [Google Gemini API](https://ai.google.dev/) (`gemini-2.5-flash` for extraction & transcription, `gemini-2.5-pro` for evaluation)
- **Visualizations**: [Plotly](https://plotly.com/) (Interactive polar radar charts)
- **Audio Processing**: [pyttsx3](https://pypi.org/project/pyttsx3/) (Text-to-speech) & native audio browser interfaces
- **PDF Extraction**: [pypdf](https://pypi.org/project/pypdf/)

---

## ⚙️ Getting Started

### 1. Clone or Navigate to the Directory
Ensure you are in the project folder:
```bash
cd "d:\4-1 pdfs\Ai Interview"
```

### 2. Install Dependencies
Ensure you have Python 3.10+ installed. Install the required libraries in your environment:
```bash
pip install -r requirements.txt
```

### 3. Setup API Key
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Open `.env` and fill in your `GEMINI_API_KEY`, or run the helper command to set it automatically:
```bash
python set_api_key.py YOUR_GEMINI_API_KEY
```

### 4. Run the Application
Start the Streamlit application:
```bash
streamlit run app.py
```
This will open the application in your default web browser at `http://localhost:8501`.


