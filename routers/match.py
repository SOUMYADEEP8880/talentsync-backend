from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.job import Job
from models.resume import Resume, MatchResult
from services.parser import extract_text, truncate
from services.claude_ai import score_resume_vs_jd
from services import vector_search

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class MatchResponse(BaseModel):
    score: int
    verdict: str
    summary: str
    matched_skills: list[str]
    missing_skills: list[str]
    gap_analysis: str
    match_id: Optional[int] = None


class JobDiscoveryResult(BaseModel):
    job_id: int
    title: str
    company: str
    location: Optional[str]
    salary: Optional[str]
    work_type: Optional[str]
    skills: list[str]
    semantic_score: float
    ai_score: Optional[int] = None
    reason: Optional[str] = None


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/score", response_model=MatchResponse)
async def score_match(
    resume_id: int = Form(...),
    jd_text: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Score a saved resume against a pasted job description."""
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    analysis = score_resume_vs_jd(resume.raw_text, jd_text)

    match = MatchResult(
        resume_id=resume.id,
        job_id=0,  # no DB job in this flow
        score=analysis["score"],
        verdict=analysis["verdict"],
        matched_skills=analysis["matched_skills"],
        missing_skills=analysis["missing_skills"],
        gap_analysis=analysis["gap_analysis"],
        exec_summary=analysis["summary"],
    )
    db.add(match)
    await db.flush()

    return MatchResponse(**analysis, match_id=match.id)


@router.post("/score-upload", response_model=MatchResponse)
async def score_upload(
    jd_text: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Score an uploaded (unauthenticated) resume against a JD — quick demo mode."""
    raw_text = await extract_text(file)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from resume.")

    analysis = score_resume_vs_jd(truncate(raw_text, 3500), jd_text)
    return MatchResponse(**analysis)


@router.post("/discover", response_model=list[JobDiscoveryResult])
async def discover_jobs(
    resume_id: int = Form(...),
    top_k: int = Form(5),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Semantic job discovery via Pinecone.
    Given a saved resume, find the top-k most similar jobs.
    """
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    # Vector search
    matches = vector_search.search_jobs(resume.raw_text, top_k=top_k)
    if not matches:
        return []

    # Fetch full job details from DB
    job_ids = [m["job_id"] for m in matches]
    jobs_result = await db.execute(select(Job).where(Job.id.in_(job_ids)))
    jobs_map = {j.id: j for j in jobs_result.scalars().all()}

    output = []
    for m in matches:
        job = jobs_map.get(m["job_id"])
        if not job:
            continue
        output.append(JobDiscoveryResult(
            job_id=job.id,
            title=job.title,
            company=job.company,
            location=job.location,
            salary=job.salary,
            work_type=job.work_type,
            skills=job.skills,
            semantic_score=m["pinecone_score"],
        ))

    return output
