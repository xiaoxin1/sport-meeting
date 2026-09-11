from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ScheduleConfig(Base):
    """竞赛日程配置。每个学年一条。"""

    __tablename__ = "schedule_configs"
    __table_args__ = (
        UniqueConstraint("academic_year_id", name="uq_schedule_config_year"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    days: Mapped[int] = mapped_column(Integer, default=2, nullable=False)  # 2 或 3 天
    lanes: Mapped[int] = mapped_column(Integer, default=8, nullable=False)  # 径赛分道数
    hard_rules: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 强规则
    soft_rules: Mapped[str] = mapped_column(Text, default="", nullable=False)  # 优化规则 a-i
    ai_history: Mapped[str] = mapped_column(Text, default="[]", nullable=False)  # AI追加消息(JSON数组)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class ScheduleEntry(Base):
    """竞赛日程中的一个赛次（某项目的预赛或决赛）。"""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_id: Mapped[int] = mapped_column(
        ForeignKey("events.id", ondelete="CASCADE"), index=True, nullable=False
    )
    day_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 第几天(1..3)
    period: Mapped[str] = mapped_column(String(8), default="上午", nullable=False)  # 上午/下午
    round_type: Mapped[str] = mapped_column(String(8), default="决赛", nullable=False)  # 预赛/决赛
    order_no: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 全局序号
    group_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 组数
    advance_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 取几名进决赛
    start_time: Mapped[str] = mapped_column(String(8), default="", nullable=False)  # HH:MM
    end_time: Mapped[str] = mapped_column(String(8), default="", nullable=False)  # HH:MM
    venue: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 场地

    groups: Mapped[list["ScheduleGroup"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", passive_deletes=True
    )


class ScheduleGroup(Base):
    """一个赛次下的一个小组。"""

    __tablename__ = "schedule_groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), index=True, nullable=False
    )
    group_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 第几组

    entry: Mapped["ScheduleEntry"] = relationship(back_populates="groups")
    lanes: Mapped[list["ScheduleLane"]] = relationship(
        back_populates="group", cascade="all, delete-orphan", passive_deletes=True
    )


class ScheduleLane(Base):
    """小组内的一个分道/席位。个人项目关联运动员，团队项目仅班级。"""

    __tablename__ = "schedule_lanes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_groups.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lane_no: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 分道号
    athlete_id: Mapped[int | None] = mapped_column(
        ForeignKey("athletes.id", ondelete="CASCADE"), nullable=True
    )
    class_team_id: Mapped[int | None] = mapped_column(
        ForeignKey("class_teams.id", ondelete="CASCADE"), nullable=True
    )
    result: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 成绩
    rank: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 名次

    group: Mapped["ScheduleGroup"] = relationship(back_populates="lanes")
