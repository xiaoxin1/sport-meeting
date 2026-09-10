from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.academic_year import AcademicYear
from app.models.user import User
from app.schemas.academic_year import (
    AcademicYearCreate,
    AcademicYearOut,
    AcademicYearUpdate,
)

router = APIRouter(
    prefix="/academic-years",
    tags=["academic-years"],
    dependencies=[Depends(get_current_user)],
)


@router.get("", response_model=list[AcademicYearOut])
def list_years(db: Session = Depends(get_db)):
    return db.query(AcademicYear).order_by(AcademicYear.created_at.desc()).all()


@router.get("/active", response_model=AcademicYearOut | None)
def get_active(db: Session = Depends(get_db)):
    return db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()


@router.post("", response_model=AcademicYearOut, status_code=status.HTTP_201_CREATED)
def create_year(payload: AcademicYearCreate, db: Session = Depends(get_db)):
    exists = db.query(AcademicYear).filter(AcademicYear.name == payload.name).first()
    if exists:
        raise HTTPException(status_code=400, detail="该学年已存在")
    year = AcademicYear(**payload.model_dump())
    # 若是第一个学年，自动设为激活
    if db.query(AcademicYear).count() == 0:
        year.is_active = True
    db.add(year)
    db.commit()
    db.refresh(year)
    return year


@router.put("/{year_id}", response_model=AcademicYearOut)
def update_year(year_id: int, payload: AcademicYearUpdate, db: Session = Depends(get_db)):
    year = db.get(AcademicYear, year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="学年不存在")
    data = payload.model_dump(exclude_unset=True)
    if "name" in data:
        dup = (
            db.query(AcademicYear)
            .filter(AcademicYear.name == data["name"], AcademicYear.id != year_id)
            .first()
        )
        if dup:
            raise HTTPException(status_code=400, detail="该学年名称已存在")
    for key, value in data.items():
        setattr(year, key, value)
    db.commit()
    db.refresh(year)
    return year


@router.post("/{year_id}/activate", response_model=AcademicYearOut)
def activate_year(year_id: int, db: Session = Depends(get_db)):
    year = db.get(AcademicYear, year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="学年不存在")
    db.query(AcademicYear).update({AcademicYear.is_active: False})
    year.is_active = True
    db.commit()
    db.refresh(year)
    return year


@router.delete("/{year_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_year(year_id: int, db: Session = Depends(get_db)):
    year = db.get(AcademicYear, year_id)
    if year is None:
        raise HTTPException(status_code=404, detail="学年不存在")
    was_active = year.is_active
    db.delete(year)
    db.commit()
    # 删掉激活学年后，自动激活最新的一个，避免无激活态
    if was_active:
        latest = (
            db.query(AcademicYear).order_by(AcademicYear.created_at.desc()).first()
        )
        if latest:
            latest.is_active = True
            db.commit()
    return None
