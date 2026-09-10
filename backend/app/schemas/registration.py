from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AthleteGender(str, Enum):
    male = "男"
    female = "女"


# ---------- 班级 ----------
class ClassTeamBase(BaseModel):
    grade: str = Field(..., min_length=1, max_length=32)
    class_name: str = Field(..., min_length=1, max_length=32)
    leader_name: str = Field("", max_length=32)
    male_count: int = Field(0, ge=0, le=10)
    female_count: int = Field(0, ge=0, le=10)

    @field_validator("grade", "class_name", "leader_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ClassTeamCreate(ClassTeamBase):
    pass


class ClassTeamUpdate(ClassTeamBase):
    pass


class ClassTeamOut(ClassTeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    created_at: datetime


# ---------- 学生（个人报名） ----------
class AthleteBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=32)
    gender: AthleteGender
    event_ids: list[int] = Field(default_factory=list)  # 报名的个人项目

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class AthleteCreate(AthleteBase):
    pass


class AthleteUpdate(AthleteBase):
    pass


class AthleteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    class_team_id: int
    name: str
    gender: str
    number: int | None
    event_ids: list[int] = Field(default_factory=list)


# ---------- 班级详情（含学生 + 团队项目） ----------
class ClassTeamDetail(ClassTeamOut):
    athletes: list[AthleteOut] = Field(default_factory=list)
    team_event_ids: list[int] = Field(default_factory=list)


class TeamEventUpdate(BaseModel):
    """更新班级报名的团队项目集合。"""

    event_ids: list[int] = Field(default_factory=list)
