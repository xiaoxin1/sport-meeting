from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Gender(str, Enum):
    male = "男"
    female = "女"
    mixed = "混合"


class EventBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    group_name: str = Field(..., min_length=1, max_length=32)
    gender: Gender
    max_teams: int = Field(0, ge=0)
    final_teams: int = Field(0, ge=0)
    is_team: bool = False
    description: str = Field("", max_length=5000)

    @field_validator("name", "group_name")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()

    @model_validator(mode="after")
    def _check_final_le_max(self):
        # max_teams 为 0 视为"不限"，此时不校验
        if self.max_teams and self.final_teams and self.final_teams > self.max_teams:
            raise ValueError("决赛队伍数不能大于上限队伍数")
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(EventBase):
    pass


class EventOut(EventBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    created_at: datetime
