"""
Vector search service using Pinecone with built-in embeddings.
No OpenAI key needed — 100% free using Pinecone's native inference.
"""
from __future__ import annotations
from core.config import get_settings

settings = get_settings()
_pinecone_index = None


def _get_index():
    global _pinecone_index
    if _pinecone_index is None:
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        _pinecone_index = pc.Index(settings.PINECONE_INDEX_NAME)
    return _pinecone_index


def upsert_job(job_id: int, title: str, company: str, description: str, skills: list[str]) -> str:
    """
    Upsert a job into Pinecone using built-in embeddings (no OpenAI needed).
    Returns the Pinecone vector ID.
    """
    text = f"{title} at {company}. {description}. Skills: {', '.join(skills)}"
    vector_id = f"job-{job_id}"
    index = _get_index()
    index.upsert_records(
        records=[{
            "id": vector_id,
            "text": text,
            "job_id": job_id,
            "title": title,
            "company": company,
        }]
    )
    return vector_id


def search_jobs(resume_text: str, top_k: int = 5) -> list[dict]:
    """
    Given a resume text, find the top-k semantically similar jobs from Pinecone.
    Returns: [{"job_id": int, "score": float, "title": str, "company": str}, ...]
    """
    index = _get_index()
    results = index.search(
        query={"inputs": {"text": resume_text[:4000]}},
        top_k=top_k,
        include_metadata=True,
    )
    matches = []
    for match in results.get("results", []):
        matches.append({
            "job_id": match.get("fields", {}).get("job_id"),
            "pinecone_score": round(match.get("score", 0) * 100, 1),
            "title": match.get("fields", {}).get("title"),
            "company": match.get("fields", {}).get("company"),
        })
    return matches


def delete_job(job_id: int):
    """Remove a job vector from Pinecone."""
    index = _get_index()
    index.delete(ids=[f"job-{job_id}"])
