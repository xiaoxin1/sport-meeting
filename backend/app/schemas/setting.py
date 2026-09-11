"""系统设置相关 schema"""
from datetime import datetime

from pydantic import BaseModel


class SettingOut(BaseModel):
    id: int
    key: str
    value: str
    updated_at: datetime

    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    value: str
