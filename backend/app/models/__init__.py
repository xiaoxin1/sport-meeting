"""聚合导出所有模型，保证 Base.metadata 能发现全部表。"""
from app.models.user import User
from app.models.academic_year import AcademicYear
from app.models.setting import AppSetting

__all__ = ["User", "AcademicYear", "AppSetting"]
