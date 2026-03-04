from datetime import datetime, timezone
from sqlalchemy import String, Text, Integer, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Resume(Base):
    __tablename__ = "resumes"

    id:           Mapped[int]   = mapped_column(primary_key=True, index=True)
    user_id:      Mapped[int]   = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename:     Mapped[str]   = mapped_column(String(255), nullable=False)
    raw_text:     Mapped[str]   = mapped_column(Text, nullable=False)           # extracted plain text
    parsed_name:  Mapped[str]   = mapped_column(String(255), nullable=True)
    parsed_email: Mapped[str]   = mapped_column(String(255), nullable=True)
    parsed_skills:Mapped[list]  = mapped_column(JSON, default=list)
    summary:      Mapped[str]   = mapped_column(Text, nullable=True)            # AI-generated summary
    created_at:   Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class MatchResult(Base):
    __tablename__ = "match_results"

    id:              Mapped[int]   = mapped_column(primary_key=True, index=True)
    resume_id:       Mapped[int]   = mapped_column(Integer, ForeignKey("resumes.id"), nullable=False, index=True)
    job_id:          Mapped[int]   = mapped_column(Integer, ForeignKey("jobs.id"), nullable=False, index=True)
    score:           Mapped[float] = mapped_column(Float, nullable=False)
    verdict:         Mapped[str]   = mapped_column(String(50), nullable=True)
    matched_skills:  Mapped[list]  = mapped_column(JSON, default=list)
    missing_skills:  Mapped[list]  = mapped_column(JSON, default=list)
    gap_analysis:    Mapped[str]   = mapped_column(Text, nullable=True)
    exec_summary:    Mapped[str]   = mapped_column(Text, nullable=True)
    created_at:      Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
