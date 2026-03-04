from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User, UserRole
from models.job import Job
from services import vector_search

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    work_type: Optional[str] = None
    salary: Optional[str] = None
    description: str
    skills: list[str] = []


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: Optional[str]
    work_type: Optional[str]
    salary: Optional[str]
    description: str
    skills: list[str]

    class Config:
        from_attributes = True


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/", response_model=list[JobResponse])
async def list_jobs(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return job


@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.recruiter:
        raise HTTPException(status_code=403, detail="Only recruiters can create jobs.")

    job = Job(**body.model_dump())
    db.add(job)
    await db.flush()

    # Embed and store in Pinecone in the background (non-blocking)
    background_tasks.add_task(
        _upsert_to_pinecone, job.id, job.title, job.company, job.description, job.skills
    )
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.recruiter:
        raise HTTPException(status_code=403, detail="Only recruiters can delete jobs.")

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    await db.delete(job)
    vector_search.delete_job(job_id)


@router.post("/seed", status_code=201)
async def seed_jobs(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Seed the DB with 12 sample jobs and index them in Pinecone."""
    from services.seed_data import SEED_JOBS
    created = []
    for data in SEED_JOBS:
        job = Job(**data)
        db.add(job)
        await db.flush()
        background_tasks.add_task(
            _upsert_to_pinecone, job.id, job.title, job.company, job.description, job.skills
        )
        created.append(job.title)
    return {"seeded": len(created), "jobs": created}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _upsert_to_pinecone(job_id, title, company, description, skills):
    try:
        vector_search.upsert_job(job_id, title, company, description, skills)
    except Exception as e:
        print(f"[Pinecone] Failed to upsert job {job_id}: {e}")
