import os
import json
import re
import google.generativeai as genai

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")


def _ask(prompt: str) -> str:
    response = model.generate_content(prompt)
    return response.text


async def score_resume(resume_text: str, jd_text: str) -> dict:
    prompt = f"""
You are an expert HR analyst. Analyze this resume against the job description and return ONLY a JSON object.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Return ONLY this JSON (no markdown, no explanation):
{{
  "score": <integer 0-100>,
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "verdict": "<one sentence summary>",
  "recommendation": "<one sentence advice>"
}}
"""
    raw = _ask(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "score": 50,
            "matched_skills": [],
            "missing_skills": [],
            "verdict": "Unable to parse response.",
            "recommendation": "Please try again."
        }


async def gap_analysis(resume_text: str, jd_text: str, current_score: int) -> dict:
    prompt = f"""
You are a career coach. The candidate scored {current_score}% match.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd_text}

Return ONLY this JSON (no markdown, no explanation):
{{
  "current_score": {current_score},
  "target_score": 90,
  "gaps": [
    {{"skill": "skill name", "importance": "High/Medium/Low", "action": "what to do"}}
  ],
  "quick_wins": ["tip1", "tip2"],
  "timeline": "X weeks/months to reach 90%"
}}
"""
    raw = _ask(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return {
            "current_score": current_score,
            "target_score": 90,
            "gaps": [],
            "quick_wins": [],
            "timeline": "Unknown"
        }


async def rank_candidates(candidates: list, jd_text: str) -> list:
    results = []
    for c in candidates:
        prompt = f"""
Rate this resume against the job description. Return ONLY JSON (no markdown):

RESUME:
{c.get('resume_text', '')}

JOB DESCRIPTION:
{jd_text}

Return ONLY:
{{"score": <0-100>, "summary": "<one sentence>", "top_skills": ["s1","s2","s3"]}}
"""
        raw = _ask(prompt)
        raw = re.sub(r"```json|```", "", raw).strip()
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"score": 50, "summary": "Could not parse.", "top_skills": []}
        results.append({**c, **parsed})
    results.sort(key=lambda x: x.get("score", 0), reverse=True)
    return results


async def executive_summary(resume_text: str) -> str:
    prompt = f"""
Write a 2-sentence executive summary of this candidate for a recruiter.
Be specific about years of experience, key skills, and any notable gaps.

RESUME:
{resume_text}

Return only the summary text, no extra formatting.
"""
    return _ask(prompt)


async def extract_skills(resume_text: str) -> list:
    prompt = f"""
Extract all technical and professional skills from this resume.
Return ONLY a JSON array of skill strings (no markdown, no explanation).
Example: ["Python", "SQL", "React"]

RESUME:
{resume_text}
"""
    raw = _ask(prompt)
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except Exception:
        return []


async def generate_exec_summary(resume_text: str) -> str:
    return await executive_summary(resume_text)


async def generate_jd(role: str, company_type: str, skills: list, location: str) -> str:
    prompt = f"""
Write a professional job description for:
Role: {role}
Company type: {company_type}
Location: {location}
Required skills: {', '.join(skills)}

Include: role summary, 5 responsibilities, requirements, and nice-to-haves.
Keep it under 300 words.
"""
    return _ask(prompt)
