from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------- 配置 ----------
class ScheduleConfigBase(BaseModel):
    days: int = Field(2, ge=2, le=3)
    lanes: int = Field(6, ge=2, le=12)
    hard_rules: str = ""
    soft_rules: str = ""


class ScheduleConfigUpdate(ScheduleConfigBase):
    pass


class EntryUpdate(BaseModel):
    """赛次更新（只允许改开始/结束时间与场地，当天按时间排序）"""

    start_time: str = Field(default="", max_length=5)
    end_time: str = Field(default="", max_length=5)
    venue: str = Field(default="", max_length=100)


class EntryCreate(BaseModel):
    """新增赛次（空赛次，分组分道后续在详情里手动新增）"""

    event_id: int
    day_index: int = Field(ge=1, le=3)
    period: str = Field(pattern="^(上午|下午)$")
    round_type: str = Field(default="决赛", pattern="^(预赛|决赛)$")
    start_time: str = Field(default="", max_length=5)
    end_time: str = Field(default="", max_length=5)
    venue: str = Field(default="", max_length=100)


class LaneCreate(BaseModel):
    """在某组内新增一个分道/席位"""

    group_id: int
    athlete_id: int | None = None
    class_team_id: int | None = None


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
    # 对话框额外要求；可为空。为空时仅按规则+数据生成/优化
    message: str = Field(default="")


class ClearScheduleIn(BaseModel):
    admin_password: str = Field(..., min_length=1)


class AIOptimizeOut(BaseModel):
    """AI 生成/优化后返回的缺陷/优化报告"""

    issues: list[str] = Field(default_factory=list)
    mode: str = "optimize"  # "generate" 或 "optimize"
