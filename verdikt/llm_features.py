import json

def get_genai(api_key):
    try:
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        return genai
    except ImportError:
        return None

def generate_jd(prompt, api_key):
    genai = get_genai(api_key)
    if not genai:
        return "Error: google-generativeai is not installed. Please run pip install google-generativeai."
    if not api_key:
        return "Error: No GEMINI_API_KEY configured."
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            f"Write a professional, 5-paragraph job description for the following role: '{prompt}'. "
            f"Include an overview, key responsibilities, required skills, and nice-to-haves. Keep it concise."
        )
        return response.text
    except Exception as e:
        return f"Failed to generate JD: {str(e)}"

def generate_interview_questions(candidate_json, job_title, api_key):
    genai = get_genai(api_key)
    if not genai:
        return ["Error: google-generativeai is not installed."]
    if not api_key:
        return ["Error: No API key configured."]
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        prompt = (
            f"You are an expert technical recruiter hiring a {job_title}. "
            f"Review this candidate's profile:\n{json.dumps(candidate_json)}\n\n"
            f"Identify potential weak spots or areas that need deeper probing based on their experience and the role. "
            f"Generate exactly 3 tailored, challenging interview questions to assess their true capabilities in those areas. "
            f"Format the output as a clean list of 3 questions."
        )
        response = model.generate_content(prompt)
        # Parse output into list
        lines = response.text.strip().split('\n')
        questions = [line.strip().lstrip('1234567890.-* ') for line in lines if line.strip()][:3]
        if not questions:
            return [response.text]
        return questions
    except Exception as e:
        return [f"Failed to generate questions: {str(e)}"]

def chat_with_resume(candidate_json, chat_history, new_question, api_key):
    genai = get_genai(api_key)
    if not genai:
        return "Error: google-generativeai is not installed."
    if not api_key:
        return "Error: No API key configured."
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        
        # Build context
        context = f"You are a helpful AI recruiting assistant. You are analyzing this candidate:\n{json.dumps(candidate_json)}\n\n"
        
        # Build history
        history_text = ""
        for msg in chat_history:
            role = "Recruiter" if msg["role"] == "user" else "AI"
            history_text += f"{role}: {msg['content']}\n"
            
        full_prompt = context + history_text + f"Recruiter: {new_question}\nAI:"
        
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        return f"Failed to chat: {str(e)}"
