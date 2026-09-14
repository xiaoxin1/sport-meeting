from datetime import datetime

from pydantic import BaseModel, Field


class RecordOut(BaseModel):
    """最高记录输出"""

    id: int
    academic_year_id: int
    event_name: str
    group_name: str
    gender: str
    sort_order: int
    holder_name: str
    result: str
    current_holder_name: str
    historical_result: str
    created_at: datetime

    class Config:
        from_attributes = True


class RecordCreate(BaseModel):
    """新增项目"""

    event_name: str = Field(max_length=64)
    group_name: str = Field(max_length=32)
    gender: str = Field(max_length=8)


class RecordUpdate(BaseModel):
    """更新记录（姓名/成绩/历史成绩/当前成绩创造者）"""

    holder_name: str = Field(default="", max_length=64)
    result: str = Field(default="", max_length=32)
    current_holder_name: str = Field(default="", max_length=64)
    historical_result: str = Field(default="", max_length=32)


class RecordSortUpdate(BaseModel):
    """批量更新排序"""

    updates: list[dict[str, int]]  # [{"id": 1, "sort_order": 0}, ...]
