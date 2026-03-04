from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional

from core.database import get_db
from core.security import get_current_user
from models.user import User, UserRole
from services.parser import extract_text, extract_name, truncate
from services.claude_ai import rank_candidates, generate_exec_summary, score_resume_vs_jd

router = APIRouter()

MAX_RESUMES = 20


# ── Schemas ───────────────────────────────────────────────────────────────────

class RankedCandidate(BaseModel):
    rank: int
    name: str
    score: int
    verdict: str
    flags: list[str]
    summary: str
    filename: str
    matched_skills: Optional[list[str]] = None
    missing_skills: Optional[list[str]] = None


class BulkRankResponse(BaseModel):
    total: int
    jd_preview: str
    candidates: list[RankedCandidate]


class GenerateJDRequest(BaseModel):
    resume_text: str
    role: str
    company_type: str
    location: str
    focus: Optional[str] = ""


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/rank", response_model=BulkRankResponse)
async def bulk_rank(
    jd_text: str = Form(...),
    files: list[UploadFile] = File(...),
    mask_names: bool = Form(False),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload multiple resumes + a JD.
    Returns candidates ranked highest to lowest match score.
    Optionally mask candidate names for bias-free screening.
    """
    if current_user.role != UserRole.recruiter:
        raise HTTPException(status_code=403, detail="Only recruiters can use bulk ranking.")

    if len(files) > MAX_RESUMES:
        raise HTTPException(status_code=400, detail=f"Max {MAX_RESUMES} resumes per batch.")

    # Parse all uploaded files
    candidates = []
    for i, f in enumerate(files):
        try:
            raw = await extract_text(f)
            name = extract_name(raw) or f"Candidate {i+1}"
            candidates.append({
                "id": i,
                "name": "Candidate" if mask_names else name,
                "headline": "",
                "resume_text": truncate(raw, 1500),
                "filename": f.filename,
                "raw_text": raw,
            })
        except Exception:
            candidates.append({
                "id": i,
                "name": f"Candidate {i+1}",
                "headline": "Parse error",
                "resume_text": "",
                "filename": f.filename,
                "raw_text": "",
            })

    # AI ranking
    ranked = rank_candidates(candidates, jd_text)
    ranked_sorted = sorted(ranked, key=lambda x: x.get("score", 0), reverse=True)

    # Build response
    output = []
    for rank, r in enumerate(ranked_sorted, start=1):
        c = next((x for x in candidates if x["id"] == r["id"]), {})
        output.append(RankedCandidate(
            rank=rank,
            name=c.get("name", "Unknown"),
            score=r.get("score", 0),
            verdict=r.get("verdict", ""),
            flags=r.get("flags", []),
            summary=r.get("summary", ""),
            filename=c.get("filename", ""),
        ))

    return BulkRankResponse(
        total=len(output),
        jd_preview=jd_text[:200] + "...",
        candidates=output,
    )


@router.post("/exec-summary")
async def get_exec_summary(
    resume_id: int = Form(...),
    jd_text: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a detailed executive summary for a specific candidate vs JD."""
    from sqlalchemy import select
    from models.resume import Resume

    result = await db.execute(select(Resume).where(Resume.id == resume_id))
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found.")

    analysis = score_resume_vs_jd(resume.raw_text, jd_text)
    return {
        "name": resume.parsed_name,
        "score": analysis["score"],
        "verdict": analysis["verdict"],
        "summary": analysis["summary"],
        "matched_skills": analysis["matched_skills"],
        "missing_skills": analysis["missing_skills"],
        "gap_analysis": analysis["gap_analysis"],
    }


@router.post("/generate-jd")
async def generate_jd_endpoint(
    body: GenerateJDRequest,
    current_user: User = Depends(get_current_user),
):
    """Generate a tailored job description from a resume and role parameters."""
    from services.claude_ai import generate_jd
    result = generate_jd(
        resume_text=body.resume_text,
        role=body.role,
        company_type=body.company_type,
        location=body.location,
        focus=body.focus,
    )
    return result
