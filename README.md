# AI Interview Preparation Platform

An interactive, AI-powered mock interview preparation web application built with Streamlit, Python, and Google Gemini API. Candidates can practice resume-focused or role-specific interviews using text or voice recording, and receive comprehensive evaluations and performance analytics.

## Features
- **Mock Interviews**: Interactive flow mimicking a real interview.
- **Speech-to-Text**: Record responses directly in the browser using the Gemini multimodal engine.
- **AI Feedback**: Question-by-question critiques, score explanations, and model answers.
- **Resume Parsing**: Generates questions tailored to your actual skills and experience.
- **Performance Scoring**: Interactive charts displaying progress across key dimensions (Technical Depth, Problem Solving, Communication).

## Tech Stack
- **Python**
- **Streamlit** (UI development)
- **Google Gemini API** (`gemini-2.5-flash` / `gemini-2.5-pro`)
- **Plotly** (Interactive scoring charts)

## Getting Started

### 1. Clone or Navigate to the Directory
Ensure you are in the project folder:
```bash
cd "d:\4-1 pdfs\Ai Interview"
```

### 2. Install Dependencies
Make sure Python is installed. Run:
```bash
pip install -r requirements.txt
```

### 3. Setup API Key
Create a `.env` file from the example:
```bash
cp .env.example .env
```
Open `.env` and fill in your `GEMINI_API_KEY`, or run the following command to set it automatically:
```bash
python set_api_key.py YOUR_GEMINI_API_KEY
```

### 4. Run the Application
Start the Streamlit application:
```bash
streamlit run app.py
```
This will open the application in your default web browser at `http://localhost:8501`.

