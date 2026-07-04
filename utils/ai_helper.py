import os
import google.generativeai as genai
import json
import logging

def clean_json_string(text: str) -> str:
    """Strips markdown code block wrappers from a JSON string if present."""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

def safe_generate_content(api_key: str, prompt, model_name: str = "gemini-2.5-flash", system_instruction: str = None, generation_config: dict = None):
    """
    Calls generate_content with a model name, and falls back to 'gemini-pro'
    if the model is not found (404) or not supported.
    """
    genai.configure(api_key=api_key)
    
    try:
        if system_instruction:
            model = genai.GenerativeModel(model_name, system_instruction=system_instruction)
        else:
            model = genai.GenerativeModel(model_name)
            
        return model.generate_content(prompt, generation_config=generation_config)
    except Exception as e:
        err_msg = str(e)
        if "404" in err_msg or "not found" in err_msg.lower() or "not supported" in err_msg.lower():
            logging.warning(f"Model {model_name} failed with error. Falling back to gemini-pro. Error: {e}")
            try:
                # If prompt is a list (like in transcription with audio part), gemini-pro cannot process audio.
                if isinstance(prompt, list):
                    for part in prompt:
                        if isinstance(part, dict) and "data" in part:
                            raise e
                
                fallback_prompt = prompt
                if system_instruction:
                    fallback_prompt = f"System Instructions:\n{system_instruction}\n\nUser Prompt:\n{prompt}"
                
                model = genai.GenerativeModel("gemini-pro")
                clean_config = None
                if generation_config:
                    clean_config = generation_config.copy()
                    if "response_mime_type" in clean_config:
                        del clean_config["response_mime_type"]
                        
                return model.generate_content(fallback_prompt, generation_config=clean_config)
            except Exception as fallback_err:
                logging.error(f"Fallback to gemini-pro failed: {fallback_err}")
                raise e
        else:
            raise e

def transcribe_audio(api_key: str, audio_bytes: bytes, mime_type: str = "audio/wav") -> str:
    """
    Transcribes audio bytes using Gemini 1.5's native audio understanding.
    """
    try:
        audio_part = {
            "mime_type": mime_type,
            "data": audio_bytes
        }
        prompt = "Transcribe the spoken audio content accurately. Do not add any conversational text or explanation. Just return the transcript text verbatim."
        response = safe_generate_content(api_key, [prompt, audio_part], model_name="gemini-2.5-flash")
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error in transcription: {e}")
        return f"[Transcription failed: {str(e)}]"

def analyze_resume_ai(api_key: str, resume_text: str, job_description: str = "", demo_mode: bool = False, **kwargs) -> dict:
    """
    Analyzes resume text using Gemini 1.5 Flash to extract skills, experience, and 5 tailored questions.
    """
    if 'demo_mode' in kwargs:
        demo_mode = kwargs.get('demo_mode', demo_mode)

    if demo_mode or api_key == "demo" or not api_key:
        return {
            "success": True,
            "skills": ["Python", "Streamlit", "REST APIs", "Data Analysis", "Git", "SQL"],
            "projects": ["Built interactive Streamlit application", "Integrated LLM APIs", "Developed REST APIs"],
            "education": ["B.S. in Computer Science"],
            "experience": ["Junior Software Developer at TechCorp (1 Year)"],
            "certifications": ["AWS Certified Cloud Practitioner"],
            "soft_skills": ["Problem Solving", "Communication", "Fast Learner"],
            "technical_skills": ["Python", "SQL", "Git", "Streamlit"],
            "candidate_profile": "A motivated Junior Software Developer with hands-on experience in building interactive Streamlit applications and integrating LLM APIs. Strong foundation in Python and backend web architecture.",
            "suggested_questions": [
                "Can you describe a Streamlit application you built and the major challenges you faced?",
                "How do you handle API error responses and rate limits in Python?",
                "Explain the difference between session state and local variables in Streamlit.",
                "How do you structure your code to ensure scalability and reusability?",
                "Describe a time you had to learn a new tool quickly to complete a project."
            ]
        }
    system_instruction = (
        "You are an expert HR Manager and Technical Recruiter. Your task is to perform a deep analysis of the candidate's resume "
        "and extract their complete professional profile, breaking it down into specific categories. Then suggest 5 interview questions."
    )
    
    prompt = f"""
    Resume Text:
    {resume_text}
    
    Job Description (Optional):
    {job_description}
    
    Please parse the resume and extract a comprehensive Candidate Profile.
    Return your output strictly as a JSON object with the following structure:
    {{
        "skills": ["A flat list of all prominent skills"],
        "projects": ["List of key projects built"],
        "education": ["Degrees and universities"],
        "experience": ["List of roles and companies with duration"],
        "certifications": ["List of certifications"],
        "soft_skills": ["List of soft skills"],
        "technical_skills": ["List of purely technical skills"],
        "candidate_profile": "A comprehensive 2-3 sentence executive summary of the candidate's entire profile.",
        "suggested_questions": [
            "Question 1",
            "Question 2",
            "Question 3",
            "Question 4",
            "Question 5"
        ]
    }}
    """
    
    try:
        response = safe_generate_content(
            api_key,
            prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned_text = clean_json_string(response.text)
        data = json.loads(cleaned_text)
        data["success"] = True
        return data
    except Exception as e:
        logging.error(f"Error analyzing resume: {e}")
        return {
            "success": False,
            "error_message": str(e),
            "skills": [],
            "projects": [],
            "education": [],
            "experience": [],
            "certifications": [],
            "soft_skills": [],
            "technical_skills": [],
            "candidate_profile": "",
            "suggested_questions": []
        }

def generate_custom_questions(api_key: str, role: str, level: str, resume_text: str, job_description: str, total_questions: int, demo_mode: bool = False) -> list:
    """
    Generates a list of exactly total_questions tailored questions based on the resume and job description.
    Frames questions drawing inspiration from platforms like LeetCode, Glassdoor, HackerRank, system design prep,
    and behavioral frameworks (STAR methodology, Amazon Leadership Principles), structured into Easy, Medium, and Hard difficulty progression.
    """
    if demo_mode or api_key == "demo" or not api_key:
        mock_questions = [
            f"Walk me through a key project from your resume relevant to this {level} {role} position.",
            f"What are the main responsibilities and technologies mentioned in the job description that you have experience with?",
            f"Design a high-level system architecture for an app that addresses the core requirements of the job description.",
            f"How would you ensure clean coding practices, testing, and continuous integration for a {role} project?",
            "Tell me about a difficult technical challenge you solved. What was your approach and the outcome?",
            "How do you prioritize tasks and collaborate with cross-functional teams under tight deadlines?",
            "If you were asked to integrate a third-party API that you've never used before, how would you go about it?",
            "What are your professional goals, and why are you interested in this specific role and company?"
        ]
        return mock_questions[:total_questions]
    system_instruction = (
        "You are an elite Technical Recruiter and Interview Designer. Your task is to design a set of "
        "extremely relevant, high-quality, and non-repetitive interview questions tailored to the candidate's "
        "resume and the target job description. The questions must challenge the candidate at their specific "
        "experience level and check their alignment with the target role."
    )
    
    # Calculate difficulty counts based on total_questions
    if total_questions <= 3:
        difficulty_spec = "1 Easy question, 1 Medium question, and 1 Hard question."
    elif total_questions <= 5:
        difficulty_spec = "2 Easy questions, 2 Medium questions, and 1 Hard question."
    else:
        difficulty_spec = "2 Easy questions, 3 Medium questions, and 3 Hard questions."

    prompt = f"""
    Target Role: {role}
    Experience Level: {level}
    Number of Questions to Generate: {total_questions}
    
    Candidate Full Resume Text:
    {resume_text}
    
    Target Job Description & Company Profile (MANDATORY):
    {job_description}
    
    You are designing questions for a mock interview for the specific company and role described in the Job Description above.
    Design exactly {total_questions} distinct interview questions following a strict progression of difficulty:
    - Easy: Resume validation (e.g., query details about a specific project, technology, or experience mentioned on their resume), basic domain definitions, or introductory behavioral questions.
    - Medium: Medium LeetCode/HackerRank coding logic, practical coding/operational design challenges related to their resume tech stack, or situational engineering.
    - Hard: System design/architecture trade-offs based on the projects they worked on, scaling questions, or complex leadership dilemmas.
    
    The question list MUST be structured as follows: {difficulty_spec}
    Arrange them in order of increasing difficulty (Easy first, then Medium, and Hard last).
    
    Frame these questions by drawing inspiration from the following platforms and methodologies:
    1. Technical Coding / DSA: LeetCode/HackerRank style problem solving (appropriate to their level).
    2. Role-specific Operational/Domain: Glassdoor/LinkedIn style questions about frameworks, tools, and best practices.
    3. Architecture / Scaling: System Design Primer style questions focusing on how components fit together, trade-offs, and scalability (especially if mid/senior/lead level).
    4. Behavioral / Soft Skills: STAR methodology (Situation, Task, Action, Result) and Amazon Leadership Principles (e.g., Ownership, Customer Obsession, Deep Dive).
    
    Ensure the questions are diverse: cover coding/algorithms, system design, domain/language-specific knowledge, and behavioral aspects. Do not repeat topics.
    
    Return the response strictly as a JSON object with the key "questions", containing a list of strings (the questions).
    Example Output format:
    {{
        "questions": [
            "Question 1 content here...",
            "Question 2 content here...",
            ...
        ]
    }}
    """
    
    # Simple defaults for padding or failure cases
    fallback_qs = [
        f"Walk me through a project from your resume where you used your key technical skills for a {role} role.",
        f"Looking at the job description and your experience, how would you design a scalable system or component to address its key requirements?",
        f"Describe a challenging technical bug or problem you encountered in your previous work and how you diagnosed and resolved it.",
        f"How do you stay up-to-date with the latest tools and best practices relevant to {role} positions?",
        "Tell me about a time you had a conflict or difference of opinion with a team member. How did you handle it?",
        "What is your approach to testing, code review, and ensuring quality in your deliverables?",
        "If you were asked to learn a completely new framework or technology for this job, how would you go about it?",
        "Do you have any questions for us, or is there a specific project on your resume you'd like to highlight further?"
    ]
    
    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned_text = clean_json_string(response.text)
        data = json.loads(cleaned_text)
        questions = data.get("questions", [])
        if not isinstance(questions, list) or len(questions) == 0:
            raise ValueError("No questions or invalid format returned from Gemini.")
            
        # Pad if short, or trim if long
        if len(questions) < total_questions:
            needed = total_questions - len(questions)
            for q in fallback_qs:
                if q not in questions:
                    questions.append(q)
                if len(questions) == total_questions:
                    break
        return questions[:total_questions]
    except Exception as e:
        logging.error(f"Error generating custom questions: {e}")
        # fallback path
        return fallback_qs[:total_questions]

def generate_first_question(api_key: str, role: str, level: str, resume_summary: str = "", customized_questions: list = None, demo_mode: bool = False) -> str:
    """
    Generates the opening greeting and asks the first pre-generated question.
    """
    first_q = "Could you introduce yourself and walk me through your background?"
    if customized_questions and len(customized_questions) > 0:
        first_q = customized_questions[0]
        
    if demo_mode or api_key == "demo" or not api_key:
        return f"Hello! Welcome to your mock interview for the {level} {role} position. Let's start with your background: {first_q}"
        
    system_instruction = (
        f"You are a friendly, professional recruiter conducting a mock interview for a {level} {role} position. "
        "Your task is to welcome the candidate warmly, and ask the first question. Keep it very natural and professional."
    )
    
    prompt = f"""
    Candidate Resume Profile: {resume_summary}
    
    Please greet the candidate warmly (e.g. 'Hello, welcome to your mock interview...'), introduce yourself, and then ask this exact first question:
    "{first_q}"
    
    Do not make up a different question. Keep the response welcoming, natural, and concise (2-3 sentences total).
    """
    
    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating first question: {e}")
        return f"Hello! Welcome to your mock interview for the {role} role. Let's start by walking through your background. Can you summarize your experience?"

def generate_next_question(api_key: str, role: str, level: str, chat_history: list, total_q: int, current_idx: int, resume_summary: str = "", customized_questions: list = None, demo_mode: bool = False) -> str:
    """
    Generates the next question by retrieving it from the pre-generated list,
    briefly acknowledging the candidate's response, and asking the question.
    """
    next_q = "Let's move on to the next question. Can you tell me about your experience with key technologies?"
    if customized_questions and current_idx < len(customized_questions):
        next_q = customized_questions[current_idx]
        
    if demo_mode or api_key == "demo" or not api_key:
        return f"Thank you for sharing that. Let's move on to the next question: {next_q}"

    # Find the candidate's last answer to acknowledge
    last_candidate_answer = ""
    if chat_history:
        for msg in reversed(chat_history):
            if msg["role"] == "user":
                last_candidate_answer = msg["text"]
                break

    system_instruction = (
        f"You are a professional, helpful, but rigorous interviewer conducting a mock interview for a {level} {role} position. "
        f"The interview consists of {total_q} questions. You are now asking question #{current_idx + 1}. "
        "Your task is to transition smoothly to the next question."
    )
    
    prompt = f"""
    Candidate Last Response:
    "{last_candidate_answer}"
    
    Acknowledge the candidate's answer briefly and professionally (e.g., "Thanks for explaining that.", "Great points regarding your architecture choice.").
    Then transition and ask this exact next interview question:
    "{next_q}"
    
    Do not invent a different question or ask multiple questions. Keep your response conversational, natural, and concise (2-3 sentences total).
    """
    
    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating next question: {e}")
        return f"Thank you for your response. Let's move on to the next question. Can you tell me about a time you had to solve a difficult technical problem?"

def evaluate_interview_feedback(api_key: str, role: str, level: str, chat_history: list, resume_profile: str = "", demo_mode: bool = False) -> dict:
    """
    Analyzes the full interview transcript and provides scores and breakdowns.
    Uses Gemini 1.5 Pro (if possible) for high-quality reasoning, fallback to Flash.
    """
    if demo_mode or api_key == "demo" or not api_key:
        breakdown = []
        for idx in range(0, len(chat_history), 2):
            q_text = chat_history[idx]["text"] if idx < len(chat_history) else f"Question {idx//2 + 1}"
            a_text = chat_history[idx+1]["text"] if (idx+1) < len(chat_history) else "No response provided."
            breakdown.append({
                "question": q_text,
                "candidate_answer": a_text,
                "critique": "A good response. Demonstrated clear understanding but could add more specific examples and technical depth.",
                "rating_explanation": "Covered the main aspects of the question but lacked detailed metric-based results.",
                "model_answer": f"An exemplary response would structure the answer using the STAR method (Situation, Task, Action, Result), highlighting specific technical actions you took to address the core problem."
            })
        return {
            "overall_summary": f"In this mock interview for the {level} {role} role, you demonstrated strong communication skills and solid domain knowledge. To improve further, focus on providing more specific, metric-driven examples of your achievements and structuring technical design decisions clearly.",
            "scores": {
                "resume_score": 92,
                "interview_score": 85,
                "communication": 82,
                "technical_knowledge": 87,
                "problem_solving": 76,
                "confidence": 85,
                "hiring_probability": 89
            },
            "recruiter_insights": {
                "recommended_role": role,
                "expected_salary": "$110,000 - $130,000",
                "final_recommendation": "Hire"
            },
            "skill_gap_analysis": {
                "strengths": [f"{role} Concepts", "Communication Skills", "Problem Solving"],
                "weaknesses": ["System Design Architecture", "Advanced Algorithms", "Testing Methodologies"],
                "recommended_learning_path": [f"Deep dive into {role} core frameworks", "Practice System Design fundamentals", "Conduct another mock interview focused on coding"]
            },
            "learning_roadmap": [
                {"week": "Week 1", "topic": f"Deep Dive into Core {role} topics"},
                {"week": "Week 2", "topic": "System Design Architecture & Caching"},
                {"week": "Week 3", "topic": "Data Structures, Algorithms & LeetCode"},
                {"week": "Week 4", "topic": "Complete Mock Interview & Testing Practice"}
            ],
            "breakdown": breakdown
        }
        
    system_instruction = (
        "You are an elite Career Coach and Technical Interview Evaluator. Analyze the transcript of the "
        "mock interview and provide a comprehensive, constructive performance critique. Evaluate "
        "responses based on four core pillars: 1) Technical & Domain Knowledge, 2) Communication Skills, "
        "3) Confidence & Professionalism, and 4) Problem Solving & Analytical Skills. Assign scores from 0 to 100."
    )
    
    # Format the transcript
    transcript = ""
    for msg in chat_history:
        role_label = "Interviewer" if msg["role"] == "ai" else "Candidate"
        transcript += f"{role_label}: {msg['text']}\n"
        
    prompt = f"""
    Role: {level} {role}
    
    Candidate Profile (Resume Context):
    {resume_profile if resume_profile else "No resume provided."}
    
    Interview Transcript:
    {transcript}
    
    Analyze the conversation and resume profile above and return a structured feedback JSON representing a "Recruiter Report". Highlight what was done well,
    what needs improvement, and give a model answer for each question asked. In addition, perform a
    skill gap analysis identifying strengths and weaknesses, and construct a 4-week learning roadmap.
    
    Return your evaluation strictly in the following JSON format:
    {{
        "overall_summary": "A concise paragraph summarizing their overall performance, strengths, and primary areas of growth.",
        "scores": {{
            "resume_score": 92,
            "interview_score": 85,
            "communication": 90,
            "technical_knowledge": 87,
            "problem_solving": 80,
            "confidence": 85,
            "hiring_probability": 89
        }},
        "recruiter_insights": {{
            "recommended_role": "{role}",
            "expected_salary": "$120k - $140k",
            "final_recommendation": "Hire"
        }},
        "skill_gap_analysis": {{
            "strengths": ["Skill A", "Skill B", ...],
            "weaknesses": ["Skill C", "Skill D", ...],
            "recommended_learning_path": ["Recommendation 1", "Recommendation 2", ...]
        }},
        "learning_roadmap": [
            {{"week": "Week 1", "topic": "Focus topic for week 1 based on weaknesses"}},
            {{"week": "Week 2", "topic": "Focus topic for week 2"}},
            {{"week": "Week 3", "topic": "Focus topic for week 3"}},
            {{"week": "Week 4", "topic": "Focus topic for week 4 (e.g. Mock Interview)"}}
        ],
        "breakdown": [
            {{
                "question": "The question asked by the interviewer",
                "candidate_answer": "The answer provided by the candidate",
                "critique": "A balanced, itemized feedback of their response (1-2 sentences).",
                "rating_explanation": "Explanation for how they scored on this specific question (e.g. key details missed or explained well).",
                "model_answer": "An exemplary response to this question showing ideal structure and content."
            }},
            ...
        ]
    }}
    """
    
    try:
        # Using gemini-2.5-pro for better reasoning, fallback to flash on error
        try:
            response = safe_generate_content(
                api_key=api_key,
                prompt=prompt,
                model_name="gemini-2.5-pro",
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json"}
            )
        except Exception:
            response = safe_generate_content(
                api_key=api_key,
                prompt=prompt,
                model_name="gemini-2.5-flash",
                system_instruction=system_instruction,
                generation_config={"response_mime_type": "application/json"}
            )
            
        cleaned_text = clean_json_string(response.text)
        return json.loads(cleaned_text)
    except Exception as e:
        logging.error(f"Error evaluating interview feedback: {e}")
        return {
            "overall_summary": "Could not generate overall feedback summary due to an error.",
            "scores": {
                "technical": 50,
                "communication": 50,
                "confidence": 50,
                "problem_solving": 50,
                "overall_readiness": 50
            },
            "skill_gap_analysis": {
                "strengths": ["Communication"],
                "weaknesses": ["Technical Architecture"],
                "recommended_learning_path": ["Study application fundamentals"]
            },
            "learning_roadmap": [
                {"week": "Week 1", "topic": "Fundamentals Review"},
                {"week": "Week 2", "topic": "Mock Interviews Practice"},
                {"week": "Week 3", "topic": "System Architecture Principles"},
                {"week": "Week 4", "topic": "Final Practice Session"}
            ],
            "breakdown": [
                {
                    "question": "N/A",
                    "candidate_answer": "N/A",
                    "critique": f"Evaluation process encountered an error: {str(e)}",
                    "rating_explanation": "None",
                    "model_answer": "N/A"
                }
            ]
        }

def evaluate_answer_correctness(api_key: str, question: str, answer: str, interview_format: str = "Standard Q&A", demo_mode: bool = False) -> dict:
    """
    Evaluates a single candidate answer against a question to determine correctness rating.
    Returns:
        dict: {"rating": "Correct" | "Incorrect" | "Partially Correct", "reason": "..."}
    """
    if demo_mode or api_key == "demo" or not api_key:
        # Simulate correctness based on response length or content
        words = answer.strip().split()
        if len(words) < 5:
            return {"rating": "Incorrect", "reason": "The answer is too brief or contains no substantial explanation."}
        elif len(words) > 20:
            return {"rating": "Correct", "reason": "Demonstrated good elaboration and relevant detail."}
        else:
            return {"rating": "Partially Correct", "reason": "Answered the question but could have provided more depth."}

    if interview_format == "Technical Coding":
        system_instruction = (
            "You are an elite Senior Staff Engineer conducting a strict code review. "
            "Evaluate the candidate's code submission for Time/Space Complexity, edge cases, best practices, and correctness. "
            "Output a correctness rating ('Correct', 'Incorrect', or 'Partially Correct') and a short, 1-sentence reason focusing on code quality and complexity."
        )
    else:
        system_instruction = (
            "You are an expert technical interviewer. Evaluate the candidate's response to the given question "
            "and output a correctness rating ('Correct', 'Incorrect', or 'Partially Correct') and a short, 1-sentence reason."
        )

    prompt = f"""
    Question: {question}
    Candidate Answer: {answer}

    Evaluate if the answer is:
    1. 'Correct' (candidate answered accurately and demonstrated clear understanding)
    2. 'Partially Correct' (candidate answered some aspects correctly but missed key points or was vague)
    3. 'Incorrect' (candidate answered wrong, showed clear misunderstanding, or gave a non-substantive response)

    Return your output strictly as a JSON object with the following structure:
    {{
        "rating": "Correct" | "Incorrect" | "Partially Correct",
        "reason": "A 1-sentence evaluation detail."
    }}
    """

    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned_text = clean_json_string(response.text)
        data = json.loads(cleaned_text)
        # Validate the format
        if data.get("rating") not in ["Correct", "Incorrect", "Partially Correct"]:
            data["rating"] = "Partially Correct"
        if "reason" not in data:
            data["reason"] = "Processed evaluation."
        return data
    except Exception as e:
        logging.error(f"Error evaluating answer: {e}")
        return {"rating": "Partially Correct", "reason": "System evaluation encountered a transient error."}

def generate_ai_coaching(api_key: str, question: str, answer: str, rating: str, demo_mode: bool = False) -> dict:
    """
    When a candidate answers incorrectly or partially, generate a rich coaching
    breakdown to turn mistakes into learning opportunities.
    Returns a dict with: correct_answer, why, common_mistakes,
                         recruiter_perspective, sample_best_answer
    """
    if demo_mode or api_key == "demo" or not api_key:
        if rating == "Correct":
            return {
                "correct_answer": "Your answer was on point!",
                "why": "You demonstrated a clear understanding of the core concept and communicated it effectively.",
                "common_mistakes": [
                    "Being too vague or generic instead of providing specific examples.",
                    "Forgetting to quantify impact with metrics.",
                ],
                "recruiter_perspective": "Recruiters love answers that combine technical depth with clear communication. You struck that balance well.",
                "sample_best_answer": "A strong answer like yours ties the concept to a concrete scenario from your experience, explains the trade-offs considered, and quantifies the outcome achieved."
            }
        return {
            "correct_answer": "The ideal response combines technical accuracy with structured communication using the STAR framework (Situation, Task, Action, Result).",
            "why": "Interviewers assess not just what you know, but how clearly and confidently you explain it. A structured answer demonstrates both competence and professionalism.",
            "common_mistakes": [
                "Giving a generic answer without concrete examples from real experience.",
                "Skipping the 'Result' ΓÇö always quantify the outcome (e.g., '40% performance improvement').",
                "Answering too briefly ΓÇö elaborate on trade-offs and your reasoning.",
                "Using buzzwords without backing them up with specifics.",
            ],
            "recruiter_perspective": "Recruiters spend under 2 minutes per answer. They're scanning for: clear structure, specific examples, measurable impact, and cultural fit signals. Missing any of these reduces your score significantly.",
            "sample_best_answer": "In my previous role at [Company], I encountered [specific challenge]. I approached it by [specific action], carefully considering [trade-off A] vs [trade-off B]. Ultimately I chose [decision] because [reasoning]. The outcome was [measurable result], which directly improved [business metric] by X%."
        }

    system_instruction = (
        "You are an elite interview coach and hiring expert. A candidate has just answered an interview question. "
        "Your job is to provide a comprehensive coaching breakdown to help them improve. "
        "Be direct, insightful, and educational. Focus on what makes a truly excellent answer."
    )

    prompt = f"""
    Interview Question: {question}
    
    Candidate's Answer: {answer}
    
    AI Evaluation Rating: {rating}
    
    Generate a detailed coaching breakdown in the following JSON format:
    {{
        "correct_answer": "A concise explanation of what the correct/ideal answer approach looks like (2-3 sentences).",
        "why": "Why this is the correct approach ΓÇö explain the underlying principle or concept in simple terms.",
        "common_mistakes": [
            "Common mistake 1 that candidates make on this type of question",
            "Common mistake 2",
            "Common mistake 3"
        ],
        "recruiter_perspective": "A paragraph explaining exactly how a recruiter or hiring manager thinks when they hear this question ΓÇö what they're truly evaluating for.",
        "sample_best_answer": "A complete, exemplary sample answer the candidate can learn from and adapt. Make it realistic, specific, and impressive."
    }}
    """

    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction,
            generation_config={"response_mime_type": "application/json"}
        )
        cleaned = clean_json_string(response.text)
        data = json.loads(cleaned)
        # Ensure all keys exist
        for key in ["correct_answer", "why", "common_mistakes", "recruiter_perspective", "sample_best_answer"]:
            if key not in data:
                data[key] = "N/A"
        if not isinstance(data.get("common_mistakes"), list):
            data["common_mistakes"] = [data["common_mistakes"]]
        return data
    except Exception as e:
        logging.error(f"Error generating AI coaching: {e}")
        return {
            "correct_answer": "Focus on structuring your answer clearly with specific examples.",
            "why": "A well-structured answer signals both competence and communication skills.",
            "common_mistakes": ["Being too vague", "No measurable results", "Skipping context"],
            "recruiter_perspective": "Recruiters evaluate clarity, depth, and cultural fit in every answer.",
            "sample_best_answer": "Use the STAR framework: Situation ΓåÆ Task ΓåÆ Action ΓåÆ Result."
        }

def generate_adaptive_question(api_key: str, role: str, level: str, chat_history: list, current_difficulty: str, resume_text: str, job_description: str, interview_format: str = "Standard Q&A", programming_language: str = "Python", demo_mode: bool = False) -> str:
    """
    Generates a single context-aware question corresponding to the current_difficulty level,
    referencing the candidate's resume/JD and preceding discussion, without repeating topics.
    """
    if demo_mode or api_key == "demo" or not api_key:
        if interview_format == "Technical Coding":
            if current_difficulty == "Beginner":
                return f"Write a {programming_language} function to reverse a string in-place without using built-in reverse methods."
            elif current_difficulty == "Intermediate":
                return f"Write a {programming_language} function that returns the indices of two numbers in an array that add up to a target sum (Two Sum). Aim for O(n) time complexity."
            else:
                return f"Write a {programming_language} class to implement an LRU Cache with `get` and `put` operations in O(1) time complexity."
                
        # Provide representative mock questions based on difficulty
        if current_difficulty == "Beginner":
            questions = [
                f"Can you walk me through a basic programming project that you've built using your core skills in {role}?",
                "Tell me about a time you had to learn a new technology quickly. How did you approach it?",
                "What is a variable, and how do you manage local state in your applications?"
            ]
        elif current_difficulty == "Intermediate":
            questions = [
                "How do you design a database schema for a simple task management or user profiling application?",
                "Describe a situation where you disagreed with a team member on a technical decision. How was it resolved?",
                "Explain how you handle exceptions and log errors in a web service or production environment."
            ]
        else: # Advanced
            questions = [
                "Describe how you would design a highly scalable, distributed caching system for large user bases.",
                "How do you analyze and optimize performance bottlenecks or database queries under high concurrency?",
                "Tell me about the most complex technical challenge you've faced recently. What trade-offs did you make?"
            ]
        
        # Pick one that isn't in chat history yet
        for q in questions:
            if not any(q in msg.get("text", "") for msg in chat_history):
                return q
        return questions[0]

    if interview_format == "Technical Coding":
        system_instruction = (
            f"You are an elite Senior Staff {programming_language} Engineer conducting a technical coding interview. "
            f"Your task is to design a single, crisp algorithmic or system design coding problem tailored to the candidate's resume and job description, matched to the difficulty level: {current_difficulty}. "
            "Review the prior chat history to ensure you build on the conversation dynamically and DO NOT repeat any problem. Return ONLY the coding problem statement."
        )
        format_constraints = f"The problem MUST be a coding challenge strictly for {programming_language}. Give them a LeetCode style problem statement."
    else:
        system_instruction = (
            f"You are an elite Technical Recruiter and Interview Designer. Your task is to design a single "
            f"interview question tailored to the candidate's resume and target job description, matched to the "
            f"difficulty level: {current_difficulty}. "
            "Review the prior chat history to ensure you build on the conversation dynamically and DO NOT repeat any question or topic."
        )
        format_constraints = "Highly varied in QUESTION TYPE compared to previous questions in the conversation."

    # Format history
    history_str = ""
    for msg in chat_history:
        role_label = "Interviewer" if msg["role"] == "ai" else "Candidate"
        history_str += f"{role_label}: {msg['text']}\n"

    prompt = f"""
    Target Role: {role}
    Experience Level: {level}
    Current Difficulty Target: {current_difficulty}
    
    Candidate Full Resume Text:
    {resume_text}
    
    Target Job Description:
    {job_description}

    Prior Interview Conversation:
    {history_str}

    Design EXACTLY ONE distinct interview question matching the difficulty level: {current_difficulty}.
    Ensure the question is:
    - Custom-tailored to the resume and job description.
    - {format_constraints}
    - Specific to the target difficulty level:
      - Beginner: Basic resume validations, simple concept definitions, or starter behavioral prompts.
      - Intermediate: Scenario-based questions, coding design patterns, debugging, or API setup logic.
      - Advanced: Architectural scaling, system design trade-offs, security, or complex engineering design constraints.
    - Contextually progressive, transitioning from previous replies.
    - Unique and doesn't repeat any topics or question types already asked consecutively.
    Return only the question text as your entire response.
    """

    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            system_instruction=system_instruction
        )
        return response.text.strip()
    except Exception as e:
        logging.error(f"Error generating adaptive question: {e}")
        # fallback
        return f"Let's proceed with a question related to {role} development. Can you tell me about the best practices you follow for code review and testing at a {current_difficulty} level?"

def text_to_speech_bytes(text: str) -> bytes:
    """Converts text into audio bytes using local TTS via pyttsx3."""
    import io
    import os
    import re
    import tempfile

    # Disable TTS in cloud environments where audio drivers are unavailable
    if os.getenv("DISABLE_TTS", "false").lower() == "true":
        logging.info("TTS is disabled via DISABLE_TTS env var.")
        return b""

    try:
        import pyttsx3
    except ImportError as e:
        logging.error(f"pyttsx3 is not installed: {e}")
        return b""

    try:
        clean_text = re.sub(r'[\u2700-\u27BF]|[\uE000-\uF8FF]|\uD83C[\uDC00-\uDFFF]|\uD83D[\uDC00-\uDFFF]|[\u2011-\u26FF]|\uD83E[\uDD10-\uDDFF]', '', text)
        clean_text = clean_text.replace('*', '').replace('_', '').replace('`', '').strip()

        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
            tmp_filepath = tmp_file.name

        engine = pyttsx3.init()
        engine.save_to_file(clean_text, tmp_filepath)
        engine.runAndWait()

        with open(tmp_filepath, 'rb') as fp:
            audio_bytes = fp.read()

        os.remove(tmp_filepath)
        return audio_bytes
    except Exception as e:
        logging.error(f"Error in text-to-speech: {e}")
        return b""


def detect_ai_content(api_key: str, question: str, answer: str, demo_mode: bool = False) -> dict:
    """
    Analyses a candidate's answer to detect if it was AI-generated or human-written.
    Returns a dict with:
        verdict       : "Human Written" | "Likely AI-Generated" | "Uncertain"
        confidence    : int (0-100)
        risk_level    : "Low" | "Medium" | "High"
        signals       : list[str]  - observed linguistic signals
        explanation   : str        - short human-readable explanation
    """
    if demo_mode or not api_key or api_key == "demo":
        return {
            "verdict": "Human Written",
            "confidence": 88,
            "risk_level": "Low",
            "signals": ["Natural sentence variation", "Minor grammatical imperfections", "Personalised examples"],
            "explanation": "The response shows natural human writing patterns with personal examples and minor inconsistencies typical of spontaneous speech."
        }

    prompt = f"""You are an expert linguistic analyst specialising in AI-generated text detection.

Carefully analyse the following interview answer and determine whether it was written/spoken naturally by a human candidate or is likely AI-generated (e.g. copied from ChatGPT, Gemini, etc.).

Interview Question:
{question}

Candidate's Answer:
{answer}

Evaluate the following signals:
1. Unnaturally perfect structure (bullet points, numbered steps, flawless grammar)
2. Generic, textbook-style explanations without personal experience
3. Overuse of transitional phrases like "Furthermore", "Moreover", "In conclusion"
4. Lack of hesitation markers, filler words, or personal anecdotes
5. Suspiciously comprehensive and well-balanced coverage of a complex topic
6. Vocabulary and phrasing that is unusually formal for an interview setting

Return a JSON object with EXACTLY these fields:
{{
  "verdict": "<Human Written | Likely AI-Generated | Uncertain>",
  "confidence": <integer 0-100>,
  "risk_level": "<Low | Medium | High>",
  "signals": ["<signal 1>", "<signal 2>", "<signal 3>"],
  "explanation": "<one concise sentence explaining your verdict>"
}}

Rules:
- confidence 0-39  means Low risk
- confidence 40-69 means Medium risk
- confidence 70-100 means High risk (if verdict is AI)
- If verdict is Human Written, risk_level must be Low or Medium
- Return ONLY valid JSON, no markdown fences."""

    try:
        response = safe_generate_content(
            api_key=api_key,
            prompt=prompt,
            model_name="gemini-2.5-flash",
            generation_config={"response_mime_type": "application/json"}
        )
        raw = clean_json_string(response.text)
        result = json.loads(raw)
        result.setdefault("verdict", "Uncertain")
        result.setdefault("confidence", 50)
        result.setdefault("risk_level", "Medium")
        result.setdefault("signals", [])
        result.setdefault("explanation", "Analysis inconclusive.")
        return result
    except Exception as e:
        logging.error(f"AI content detection failed: {e}")
        return {
            "verdict": "Uncertain",
            "confidence": 50,
            "risk_level": "Medium",
            "signals": [],
            "explanation": "Analysis could not be completed."
        }
