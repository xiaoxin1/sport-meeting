from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ClassTeam(Base):
    """班级报名单位。归属某一学年。

    唯一键：同一学年内，年级 + 班级 唯一。
    """

    __tablename__ = "class_teams"
    __table_args__ = (
        UniqueConstraint("academic_year_id", "grade", "class_name", name="uq_class_identity"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    grade: Mapped[str] = mapped_column(String(32), nullable=False)  # 年级
    class_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 班级
    leader_name: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 领队姓名
    male_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 男生人数
    female_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 女生人数
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    athletes: Mapped[list["Athlete"]] = relationship(
        back_populates="class_team", cascade="all, delete-orphan", passive_deletes=True
    )
    team_events: Mapped[list["ClassTeamEvent"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class Athlete(Base):
    """学生（个人报名者）。归属某个班级。号码由外部一键生成。"""

    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_team_id: Mapped[int] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(32), nullable=False)  # 姓名
    gender: Mapped[str] = mapped_column(String(8), nullable=False)  # 男 / 女
    number: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 号码，留白为 None
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    class_team: Mapped["ClassTeam"] = relationship(back_populates="athletes")
    events: Mapped[list["AthleteEvent"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class AthleteEvent(Base):
    """学生 ↔ 个人项目 的报名关联。"""

    __tablename__ = "athlete_events"
    __table_args__ = (
        UniqueConstraint("athlete_id", "event_id", name="uq_athlete_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    athlete_id: Mapped[int] = mapped_column(
        ForeignKey("athletes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )


class ClassTeamEvent(Base):
    """班级 ↔ 团队项目 的报名关联。"""

    __tablename__ = "class_team_events"
    __table_args__ = (
        UniqueConstraint("class_team_id", "event_id", name="uq_classteam_event"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_team_id: Mapped[int] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
