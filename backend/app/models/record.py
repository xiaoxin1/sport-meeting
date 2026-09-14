from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Record(Base):
    """项目最高记录。每个学年每个项目组合一条记录。"""

    __tablename__ = "records"
    __table_args__ = (
        UniqueConstraint(
            "academic_year_id",
            "event_name",
            "group_name",
            "gender",
            name="uq_record_key",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), index=True, nullable=False
    )
    event_name: Mapped[str] = mapped_column(String(64), nullable=False)  # 项目名称
    group_name: Mapped[str] = mapped_column(String(32), nullable=False)  # 年级
    gender: Mapped[str] = mapped_column(String(8), nullable=False)  # 男/女
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序

    holder_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 历史记录保持者姓名
    result: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 当前成绩
    current_holder_name: Mapped[str] = mapped_column(String(64), default="", nullable=False)  # 当前成绩创造者

    historical_result: Mapped[str] = mapped_column(String(32), default="", nullable=False)  # 历史成绩

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
