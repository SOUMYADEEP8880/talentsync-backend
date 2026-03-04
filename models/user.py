from datetime import datetime, timezone
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
import enum

from core.database import Base


class UserRole(str, enum.Enum):
    candidate = "candidate"
    recruiter = "recruiter"


class User(Base):
    __tablename__ = "users"

    id:         Mapped[int]      = mapped_column(primary_key=True, index=True)
    email:      Mapped[str]      = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name:  Mapped[str]      = mapped_column(String(255), nullable=False)
    hashed_pw:  Mapped[str]      = mapped_column(String(255), nullable=False)
    role:       Mapped[UserRole] = mapped_column(SAEnum(UserRole), default=UserRole.candidate)
    is_active:  Mapped[bool]     = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
