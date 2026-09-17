from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Gender(str, Enum):
    male = "男"
    female = "女"
    mixed = "混合"


class EventBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    group_name: str = Field(..., min_length=1, max_length=32)
    gender: Gender
    # 输出宽松（旧数据可能为空）；输入必填由 EventCreate/EventUpdate 收紧
    venue: str = Field("", max_length=32)
    final_teams: int = Field(0, ge=0)
    is_team: bool = False
    description: str = Field("", max_length=5000)

    @field_validator("name", "group_name", "venue")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


class EventCreate(EventBase):
    venue: str = Field(..., min_length=1, max_length=32)


class EventUpdate(EventBase):
    venue: str = Field(..., min_length=1, max_length=32)


class EventOut(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    created_at: datetime
