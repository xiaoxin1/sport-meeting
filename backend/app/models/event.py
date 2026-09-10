from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Event(Base):
    """比赛项目。归属某一学年。

    唯一键：同一学年内，项目名称 + 组别 + 性别 唯一。
    """

    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint(
            "academic_year_id", "name", "group_name", "gender", name="uq_event_identity"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )

    name: Mapped[str] = mapped_column(String(64), nullable=False)  # 项目名称
    group_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 组别(年级)
    gender: Mapped[str] = mapped_column(String(8), nullable=False)  # 男 / 女 / 混合

    # 决赛队伍数：报名人数(队伍数)低于该值则直接决赛，否则需增加预赛
    final_teams: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    is_team: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 团队/个人
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 项目介绍

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
