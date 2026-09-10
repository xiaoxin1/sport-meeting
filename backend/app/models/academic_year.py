from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AcademicYear(Base):
    """学年。系统的数据根：绝大多数业务数据都归属某个学年。"""

    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 展示名，如 "2026~2027"
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    # 运动会起止日期
    meet_start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    meet_end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    # 是否为当前激活学年（同一时刻仅一个为 True）
    is_active: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
