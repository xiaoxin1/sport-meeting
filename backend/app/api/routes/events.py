from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_active_year, get_current_principal, require_admin
from app.core.database import get_db
from app.models.academic_year import AcademicYear
from app.models.event import Event
from app.schemas.event import EventCreate, EventOut, EventUpdate

# 任意登录主体（管理员/领队）均可读取项目列表（领队报名需勾选项目）；写操作各自加 require_admin。
router = APIRouter(
    prefix="/events",
    tags=["events"],
    dependencies=[Depends(get_current_principal)],
)


def _get_owned_event(event_id: int, year: AcademicYear, db: Session) -> Event:
    """取当前学年下的项目，跨学年访问按 404 处理。"""
    event = db.get(Event, event_id)
    if event is None or event.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    return event


@router.get("", response_model=list[EventOut])
def list_events(
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    return (
        db.query(Event)
        .filter(Event.academic_year_id == year.id)
        .order_by(Event.group_name, Event.gender, Event.name)
        .all()
    )


@router.post("", response_model=EventOut, status_code=status.HTTP_201_CREATED)
def create_event(
    payload: EventCreate,
    _: object = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    event = Event(academic_year_id=year.id, **_dump(payload))
    db.add(event)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，项目名称+组别+性别 已存在")
    db.refresh(event)
    return event


@router.put("/{event_id}", response_model=EventOut)
def update_event(
    event_id: int,
    payload: EventUpdate,
    _: object = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    event = _get_owned_event(event_id, year, db)
    for key, value in _dump(payload).items():
        setattr(event, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，项目名称+组别+性别 已存在")
    db.refresh(event)
    return event


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    event_id: int,
    _: object = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    event = _get_owned_event(event_id, year, db)
    db.delete(event)
    db.commit()
    return None


def _dump(payload: EventCreate | EventUpdate) -> dict:
    data = payload.model_dump()
    data["gender"] = data["gender"].value if hasattr(data["gender"], "value") else data["gender"]
    return data
