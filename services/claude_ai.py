import json
import re
import anthropic
from core.config import get_settings

settings = get_settings()
_client = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


def _ask(prompt: str, system: str = "", max_tokens: int = 1000) -> str:
    client = get_client()
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        system=system or "You are a precise AI recruiter. Always return valid JSON only — no markdown, no extra text.",
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in message.content if hasattr(b, "text"))


def _parse_json(raw: str) -> dict | list:
    clean = re.sub(r"```json|```", "", raw).strip()
    return json.loads(clean)


# ── 1. Single resume vs single JD ─────────────────────────────────────────────

def score_resume_vs_jd(resume_text: str, jd_text: str) -> dict:
    prompt = f"""
Resume:
{resume_text[:3500]}

Job Description:
{jd_text[:2000]}

Analyze the match. Return ONLY this JSON:
{{
  "score": <integer 0-100>,
  "verdict": "<Strong Match | Good Fit | Needs Work | Not Aligned>",
  "summary": "<2-sentence executive summary of this candidate for this role>",
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill1", "skill2"],
  "gap_analysis": "<Specific actionable advice to close the gap and reach 90%+ — concrete skills or projects to add>"
}}"""
    raw = _ask(prompt)
    try:
        return _parse_json(raw)
    except Exception:
        return {
            "score": 60, "verdict": "Good Fit",
            "summary": "Candidate shows relevant experience for this role.",
            "matched_skills": [], "missing_skills": [],
            "gap_analysis": "Focus on the core technical skills mentioned in the job description.",
        }


# ── 2. Candidate executive summary ────────────────────────────────────────────

def generate_exec_summary(resume_text: str) -> str:
    prompt = f"""
Resume:
{resume_text[:3000]}

Write a 2-3 sentence recruiter executive summary for this candidate.
Mention years of experience, strongest skills, and one notable gap or concern.
Return plain text only — no JSON.
"""
    return _ask(prompt, system="You are a senior technical recruiter. Be concise and honest.", max_tokens=300)


# ── 3. Parse skills from resume text ──────────────────────────────────────────

def extract_skills(resume_text: str) -> list[str]:
    prompt = f"""
Extract a flat list of technical skills from this resume text.
Include languages, frameworks, tools, databases, and platforms.
Return ONLY a JSON array of strings: ["Python", "SQL", ...]

Resume:
{resume_text[:3000]}"""
    raw = _ask(prompt)
    try:
        result = _parse_json(raw)
        return result if isinstance(result, list) else []
    except Exception:
        return []


# ── 4. Bulk rank candidates against a JD ──────────────────────────────────────

def rank_candidates(candidates: list[dict], jd_text: str) -> list[dict]:
    """
    candidates: [{"id": int, "name": str, "headline": str, "resume_text": str}, ...]
    Returns: [{"id": int, "score": int, "verdict": str, "flags": [...], "summary": str}, ...]
    """
    slim = [{"id": c["id"], "name": c["name"], "headline": c.get("headline", ""), "resume": c.get("resume_text", "")[:800]} for c in candidates]

    prompt = f"""
Job Description:
{jd_text[:2000]}

Candidates:
{json.dumps(slim, indent=2)}

Score each candidate 0-100 against the JD. Use semantic understanding — not just keyword matching.
Return ONLY a JSON array:
[{{"id": <int>, "score": <int>, "verdict": "<Strong Match|Good Fit|Needs Work|Not Aligned>", "flags": ["flag1"], "summary": "<1-sentence summary>"}}]
"""
    raw = _ask(prompt, max_tokens=1500)
    try:
        result = _parse_json(raw)
        return result if isinstance(result, list) else []
    except Exception:
        return [{"id": c["id"], "score": 50, "verdict": "Good Fit", "flags": [], "summary": ""} for c in candidates]


# ── 5. Generate a tailored job description ────────────────────────────────────

def generate_jd(resume_text: str, role: str, company_type: str, location: str, focus: str = "") -> dict:
    prompt = f"""
Candidate Resume:
{resume_text[:2500]}

Role: {role}
Company type: {company_type}
Location: {location}
{f"Special focus: {focus}" if focus else ""}

Write a realistic, compelling JD tailored to this candidate's skills.
Return ONLY this JSON:
{{
  "title": "<job title>",
  "company": "<fictional but realistic company name>",
  "tagline": "<one punchy sentence about the company>",
  "location": "{location}",
  "type": "<Internship | Full-time | Contract>",
  "duration": "<e.g. 6 months>",
  "stipend": "<realistic salary/stipend range>",
  "about": "<2 sentences about the company>",
  "role_summary": "<2 sentences on day-to-day work>",
  "responsibilities": ["item1", "item2", "item3", "item4", "item5"],
  "must_have": ["skill1", "skill2", "skill3"],
  "nice_to_have": ["skill1", "skill2"],
  "bonus": ["skill1", "skill2"],
  "why_you": "<2 sentences referencing candidate's actual projects/achievements>",
  "perks": [{{"emoji": "🏠", "text": "perk1"}}, {{"emoji": "📚", "text": "perk2"}}, {{"emoji": "💻", "text": "perk3"}}, {{"emoji": "🚀", "text": "perk4"}}],
  "apply_note": "<one line on how to apply>"
}}"""
    raw = _ask(prompt, max_tokens=1200)
    try:
        return _parse_json(raw)
    except Exception:
        return {"title": role, "company": "TechCorp", "tagline": "Building great products.", "error": "Generation failed — please retry."}
