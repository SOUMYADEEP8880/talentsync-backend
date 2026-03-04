from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Job(Base):
    __tablename__ = "jobs"

    id:          Mapped[int]      = mapped_column(primary_key=True, index=True)
    title:       Mapped[str]      = mapped_column(String(255), nullable=False)
    company:     Mapped[str]      = mapped_column(String(255), nullable=False)
    location:    Mapped[str]      = mapped_column(String(255), nullable=True)
    work_type:   Mapped[str]      = mapped_column(String(50), nullable=True)   # Remote / Hybrid / On-site
    salary:      Mapped[str]      = mapped_column(String(100), nullable=True)
    description: Mapped[str]      = mapped_column(Text, nullable=False)
    skills:      Mapped[list]     = mapped_column(JSON, default=list)          # ["Python", "SQL", ...]
    pinecone_id: Mapped[str]      = mapped_column(String(100), nullable=True)  # vector store reference
    created_at:  Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
