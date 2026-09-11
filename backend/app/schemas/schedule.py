from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 配置 ----------
class ScheduleConfigBase(BaseModel):
    days: int = Field(2, ge=2, le=3)
    lanes: int = Field(8, ge=2, le=12)
    hard_rules: str = ""
    soft_rules: str = ""


class ScheduleConfigUpdate(ScheduleConfigBase):
    pass


class EntryUpdate(BaseModel):
    """赛次更新（手动编辑时间、场地等）"""

    day_index: int = Field(ge=1, le=3)
    period: str = Field(pattern="^(上午|下午)$")
    order_no: int = Field(ge=1)
    start_time: str = Field(max_length=5)
    end_time: str = Field(max_length=5)
    venue: str = Field(max_length=100)


class ScheduleConfigOut(ScheduleConfigBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    ai_history: list[str] = Field(default_factory=list)
    generated_at: datetime | None = None


# ---------- 分道/席位 ----------
class LaneOut(BaseModel):
    id: int
    lane_no: int
    athlete_id: int | None = None
    class_team_id: int | None = None
    athlete_name: str | None = None
    number: int | None = None
    grade: str | None = None
    class_name: str | None = None
    result: str = ""
    rank: int | None = None


class GroupOut(BaseModel):
    id: int
    group_no: int
    lanes: list[LaneOut] = Field(default_factory=list)


# ---------- 赛次 ----------
class EntryOut(BaseModel):
    id: int
    event_id: int
    event_name: str
    group_name: str  # 组别(年级)
    gender: str
    is_team: bool
    day_index: int
    period: str
    round_type: str
    order_no: int
    group_count: int
    advance_count: int
    start_time: str
    end_time: str
    venue: str


class EntryDetail(EntryOut):
    groups: list[GroupOut] = Field(default_factory=list)


class ScheduleOut(BaseModel):
    """整表：配置 + 各半天分段的赛次列表。"""

    config: ScheduleConfigOut | None = None
    entries: list[EntryOut] = Field(default_factory=list)
    day_dates: dict[int, str] = Field(default_factory=dict)  # day_index -> 日期文案


# ---------- 成绩录入 ----------
class LaneResultIn(BaseModel):
    lane_id: int
    result: str = ""
    rank: int | None = None


class LaneUpdateIn(BaseModel):
    """手动修改分道选手"""

    lane_id: int
    athlete_id: int | None = None
    class_team_id: int | None = None


class ResultsUpdate(BaseModel):
    results: list[LaneResultIn] = Field(default_factory=list)


class AIOptimizeIn(BaseModel):
    message: str = Field(..., min_length=1)
