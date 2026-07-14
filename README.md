# Smart Resume Screener

AI-powered resume screening tool that parses resumes, extracts structured data, and scores candidates against a job description using Claude AI.

##Demo video link:

Watch the project demo here:
https://drive.google.com/file/d/13s3WuGsdujsHgrVybmoY3caCGO2ntitB/view?usp=drive_link


## Architecture

```
resume_screener/
├── main.py          # FastAPI backend
├── templates/
│   └── index.html   # Frontend UI
├── requirements.txt
└── README.md
```

**Flow:**
1. User uploads PDF/TXT resumes + pastes job description
2. Backend extracts text from PDFs (PyPDF2)
3. Claude extracts structured data (name, skills, experience, education)
4. Claude scores each resume against JD (1–10) with justification
5. Results ranked and displayed with match %, tags, recommendation

## LLM Prompts

### Structured Extraction Prompt
```
Extract structured information from this resume. Return ONLY valid JSON.
Fields: name, email, phone, skills[], experience_years, education, previous_roles[]
```

### Scoring Prompt
```
You are an expert technical recruiter. Compare this resume against the job description.
Rate fit on 1-10 with: match_percentage, strengths[], gaps[], 
matched_skills[], missing_skills[], justification, recommendation (Shortlist/Maybe/Reject)
```

## Setup & Run

```bash
pip install fastapi uvicorn python-multipart pypdf2 anthropic

export ANTHROPIC_API_KEY=your_key_here

uvicorn main:app --reload --port 8000
```

Open `http://localhost:8000`

## Tech Stack
- **Backend:** FastAPI (Python)
- **LLM:** Claude claude-sonnet-4-6 via Anthropic API
- **PDF Parsing:** PyPDF2
- **Frontend:** Vanilla HTML/CSS/JS

## Features
- Multi-resume upload (PDF + TXT)
- Structured data extraction per candidate
- AI match scoring with justification
- Ranked dashboard with skill tags
- Shortlist / Maybe / Reject recommendation
