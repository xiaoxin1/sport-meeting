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
    leader_name: str = Field(..., min_length=1, max_length=32)  # 领队姓名必填
    male_count: int = Field(0, ge=0, le=10)
    female_count: int = Field(0, ge=0, le=10)

    @field_validator("grade", "class_name", "leader_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class ClassTeamCreate(ClassTeamBase):
    password: str | None = Field(None, max_length=64)  # 领队登录密码；留空用默认


class ClassTeamUpdate(ClassTeamBase):
    password: str | None = Field(None, max_length=64)  # 留空则保持原密码


class ClassTeamOut(ClassTeamBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    created_at: datetime
    password: str = ""  # 仅管理员可见；领队视图由后端置空


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
    grade: str = ""
    class_name: str = ""


# ---------- 班级详情（含学生 + 团队项目） ----------
class ClassTeamDetail(ClassTeamOut):
    athletes: list[AthleteOut] = Field(default_factory=list)
    team_event_ids: list[int] = Field(default_factory=list)


class TeamEventUpdate(BaseModel):
    """更新班级报名的团队项目集合。"""

    event_ids: list[int] = Field(default_factory=list)


# ---------- 报名整体保存（详情页「保存」按钮） ----------
class RegistrationAthleteInput(BaseModel):
    """保存时的单个运动员。id 为空表示新增。"""

    id: int | None = None
    name: str = Field(..., min_length=1, max_length=32)
    gender: AthleteGender
    event_ids: list[int] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class RegistrationSaveRequest(BaseModel):
    """一次性提交班级报名：人数 + 运动员名单 + 团队项目。"""

    male_count: int = Field(0, ge=0, le=10)
    female_count: int = Field(0, ge=0, le=10)
    athletes: list[RegistrationAthleteInput] = Field(default_factory=list)
    team_event_ids: list[int] = Field(default_factory=list)


# ---------- 项目报名名单 ----------
class EventRegistrationEntry(BaseModel):
    """一条项目报名记录。团队项目仅有班级信息；个人项目附带姓名+号码。"""

    class_id: int
    grade: str
    class_name: str
    athlete_name: str | None = None
    number: int | None = None


class EventRegistrationList(BaseModel):
    event_id: int
    event_name: str
    is_team: bool
    entries: list[EventRegistrationEntry] = Field(default_factory=list)
