import os
import sqlite3
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from groq import Groq
import PyPDF2
import io
import json
import re
from typing import List

app = FastAPI(title="Smart Resume Screener")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = Groq()

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resumes.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS screened_resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            candidate_name TEXT,
            email TEXT,
            education TEXT,
            experience_years INTEGER,
            skills TEXT,
            score INTEGER,
            match_percentage INTEGER,
            recommendation TEXT,
            justification TEXT,
            job_description TEXT,
            screened_at TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_to_db(filename, candidate, scoring, job_description):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO screened_resumes
        (filename, candidate_name, email, education, experience_years, skills,
         score, match_percentage, recommendation, justification, job_description, screened_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename,
        candidate.get("name", "Unknown"),
        candidate.get("email", ""),
        candidate.get("education", ""),
        candidate.get("experience_years", 0),
        json.dumps(candidate.get("skills", [])),
        scoring.get("score", 0),
        scoring.get("match_percentage", 0),
        scoring.get("recommendation", ""),
        scoring.get("justification", ""),
        job_description[:500],
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

init_db()

def call_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
        temperature=0.1
    )
    return response.choices[0].message.content.strip()

def extract_text_from_pdf(file_bytes: bytes) -> str:
    try:
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text.strip()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not parse PDF: {str(e)}")

def extract_structured_data(resume_text: str) -> dict:
    prompt = f"""Extract structured information from this resume. Return ONLY valid JSON, no explanation, no markdown.

Resume:
{resume_text[:3000]}

Return this exact JSON structure:
{{
  "name": "candidate full name or Unknown",
  "email": "email or null",
  "phone": "phone or null",
  "skills": ["skill1", "skill2"],
  "experience_years": 0,
  "education": "highest degree and field",
  "previous_roles": ["role1", "role2"]
}}"""
    raw = call_llm(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except:
        return {"name": "Unknown", "email": None, "phone": None, "skills": [], "experience_years": 0, "education": "Not extracted", "previous_roles": []}

def score_resume(resume_text: str, job_description: str) -> dict:
    prompt = f"""You are an expert technical recruiter. Compare this resume against the job description.

JOB DESCRIPTION:
{job_description[:2000]}

RESUME:
{resume_text[:3000]}

Return ONLY valid JSON, no explanation, no markdown:
{{
  "score": 7,
  "match_percentage": 70,
  "strengths": ["strength1", "strength2", "strength3"],
  "gaps": ["gap1", "gap2"],
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "justification": "2-3 sentence overall assessment",
  "recommendation": "Shortlist"
}}

recommendation must be exactly one of: Shortlist, Maybe, Reject"""
    raw = call_llm(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except:
        return {"score": 5, "match_percentage": 50, "strengths": [], "gaps": [], "matched_skills": [], "missing_skills": [], "justification": raw[:300], "recommendation": "Maybe"}

@app.get("/", response_class=HTMLResponse)
async def root():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    html_path = os.path.join(base_dir, "templates", "index.html")
    with open(html_path, encoding="utf-8") as f:
        return f.read()

@app.post("/api/screen")
async def screen_resumes(
    job_description: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    if not job_description.strip():
        raise HTTPException(status_code=400, detail="Job description is required")
    if not resumes:
        raise HTTPException(status_code=400, detail="At least one resume is required")
    results = []
    for resume_file in resumes:
        file_bytes = await resume_file.read()
        if resume_file.filename.endswith(".pdf"):
            resume_text = extract_text_from_pdf(file_bytes)
        else:
            resume_text = file_bytes.decode("utf-8", errors="ignore")
        structured = extract_structured_data(resume_text)
        scoring = score_resume(resume_text, job_description)
        save_to_db(resume_file.filename, structured, scoring, job_description)
        results.append({"filename": resume_file.filename, "candidate": structured, "scoring": scoring})
    results.sort(key=lambda x: x["scoring"]["score"], reverse=True)
    return JSONResponse(content={"candidates": results, "total": len(results)})

@app.get("/api/history")
async def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM screened_resumes ORDER BY screened_at DESC LIMIT 50").fetchall()
    conn.close()
    return JSONResponse(content={"history": [dict(r) for r in rows]})