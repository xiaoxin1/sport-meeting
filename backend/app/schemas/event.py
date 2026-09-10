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
    final_teams: int = Field(0, ge=0)
    is_team: bool = False
    description: str = Field("", max_length=5000)

    @field_validator("name", "group_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()



class EventCreate(EventBase):
    pass


class EventUpdate(EventBase):
    pass


class EventOut(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    created_at: datetime
