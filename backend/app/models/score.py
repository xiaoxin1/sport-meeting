from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ClassScore(Base):
    """班级得分统计。每个学年每个班级一条记录。"""

    __tablename__ = "class_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    class_team_id: Mapped[int] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grade: Mapped[str] = mapped_column(String(32), nullable=False)  # 冗余，方便分组
    class_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 冗余，方便显示
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank_in_grade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class AthleteScore(Base):
    """个人得分统计。每个学年每个运动员一条记录。"""

    __tablename__ = "athlete_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("athletes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    class_team_id: Mapped[int] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grade: Mapped[str] = mapped_column(String(32), nullable=False)  # 冗余
    athlete_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 冗余
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rank_in_grade: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ScoreDetail(Base):
    """得分明细。记录每一笔得分的来源。"""

    __tablename__ = "score_details"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    schedule_lane_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_lanes.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # 项目信息
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)
    group_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 年级
    gender: Mapped[str] = mapped_column(String(8), nullable=False)
    is_team_event: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # 归属信息
    class_team_id: Mapped[int] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    athlete_id: Mapped[int | None] = mapped_column(
        ForeignKey("athletes.id", ondelete="CASCADE"), index=True, nullable=True
    )

    # 得分信息
    rank: Mapped[int] = mapped_column(Integer, nullable=False)  # 名次 1-6
    result: Mapped[str] = mapped_column(String(32), nullable=False)  # 成绩
    base_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 基础分
    is_record_broken: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    final_score: Mapped[int] = mapped_column(Integer, nullable=False)  # 最终得分

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
