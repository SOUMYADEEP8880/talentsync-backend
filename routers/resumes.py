from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User
from models.resume import Resume
from services.parser import extract_text, extract_email, extract_name, truncate
from services.claude_ai import extract_skills, generate_exec_summary

router = APIRouter()

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


# ── Schemas ───────────────────────────────────────────────────────────────────

class ResumeResponse(BaseModel):
    id: int
    filename: str
    parsed_name: Optional[str]
    parsed_email: Optional[str]
    parsed_skills: list[str]
    summary: Optional[str]

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/upload", response_model=ResumeResponse, status_code=201)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Validate size
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 5 MB.")
    await file.seek(0)

    # Parse text
    raw_text = await extract_text(file)
    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract text from file.")

    # AI enrichment
    skills = extract_skills(raw_text)
    summary = generate_exec_summary(raw_text)

    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        raw_text=truncate(raw_text, 8000),
        parsed_name=extract_name(raw_text),
        parsed_email=extract_email(raw_text),
        parsed_skills=skills,
        summary=summary,
    )
    db.add(resume)
    await db.flush()
    return resume


@router.get("/", response_model=list[ResumeResponse])
async def list_my_resumes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.user_id == current_user.id).order_by(Resume.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    return resume


@router.delete("/{resume_id}", status_code=204)
async def delete_resume(
    resume_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Resume).where(Resume.id == resume_id, Resume.user_id == current_user.id)
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")
    await db.delete(resume)
