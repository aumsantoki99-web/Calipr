import io
import PyPDF2
import docx

def parse_pdf(file_bytes) -> str:
    """Extract text from a PDF file."""
    text = ""
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    except Exception as e:
        print(f"Error parsing PDF: {e}")
    return text

def parse_docx(file_bytes) -> str:
    """Extract text from a DOCX file."""
    text = ""
    try:
        doc = docx.Document(io.BytesIO(file_bytes))
        for para in doc.paragraphs:
            text += para.text + "\n"
    except Exception as e:
        print(f"Error parsing DOCX: {e}")
    return text

def parse_resume(file_name: str, file_bytes: bytes) -> str:
    """Route to correct parser based on extension."""
    ext = file_name.lower().split('.')[-1]
    if ext == 'pdf':
        return parse_pdf(file_bytes)
    elif ext == 'docx':
        return parse_docx(file_bytes)
    elif ext == 'txt':
        return file_bytes.decode('utf-8', errors='ignore')
    return ""

def generate_mock_profile_from_text(raw_text: str, filename: str) -> dict:
    """
    Since we are using the 'old mock scoring logic' (no LLM generation),
    we generate a structured profile just from the filename/randomness 
    so it matches the jsonl candidate structure, but inject the raw_text 
    into it so local embeddings (SentenceTransformers) can still read it.
    """
    import random
    
    # We create a dummy structure that Calipr expects
    base_name = filename.split('.')[0].replace('_', ' ').title()
    
    return {
        "candidate_id": f"UPLOAD_{random.randint(1000, 9999)}",
        "profile": {
            "anonymized_name": base_name,
            "current_title": "Applicant",
            "years_of_experience": random.randint(2, 10),
            "location": "Remote"
        },
        "career_history": [
            {
                "title": "Professional Experience",
                "company": "Various",
                "description": raw_text[:500] + "..." # Snippet for UI display
            }
        ],
        "education": [],
        "skills": ["python", "communication"], # Fallback mock skills
        "redrob_signals": {
            "skill_assessment_scores": {"python": 80},
            "recruiter_response_rate": 0.9,
            "open_to_work_flag": True,
            "notice_period_days": 30
        },
        # We inject a special field so build_candidate_text in app.py can grab the raw resume text for the semantic search
        "_raw_resume_text": raw_text 
    }
