from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class AcademicYearBase(BaseModel):
    name: str
    meet_start_date: date | None = None
    meet_end_date: date | None = None


class AcademicYearCreate(AcademicYearBase):
    pass


class AcademicYearUpdate(BaseModel):
    name: str | None = None
    meet_start_date: date | None = None
    meet_end_date: date | None = None


class AcademicYearOut(AcademicYearBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
