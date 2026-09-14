from datetime import datetime

from pydantic import BaseModel


class ScoreDetailOut(BaseModel):
    """得分明细输出"""

    id: int
    event_name: str
    group_name: str
    gender: str
    is_team_event: bool
    athlete_name: str | None  # 个人项目才有
    rank: int
    result: str
    base_score: int
    is_record_broken: bool
    final_score: int
    created_at: datetime


class ClassScoreOut(BaseModel):
    """班级得分输出"""

    id: int
    class_team_id: int
    grade: str
    class_name: str
    total_score: int
    rank_in_grade: int
    updated_at: datetime


class AthleteScoreOut(BaseModel):
    """个人得分输出"""

    id: int
    athlete_id: int
    class_team_id: int
    grade: str
    class_name: str  # 额外字段，前端显示用
    athlete_name: str
    total_score: int
    rank_in_grade: int
    updated_at: datetime


class CalculateSummary(BaseModel):
    """统计计算摘要"""

    total_details: int  # 总得分明细数
    total_athletes: int  # 参与得分的运动员数
    total_classes: int  # 参与得分的班级数
    calculated_at: datetime
