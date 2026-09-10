from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_active_year, get_current_user
from app.core.database import get_db
from app.models.academic_year import AcademicYear
from app.models.event import Event
from app.models.registration import (
    Athlete,
    AthleteEvent,
    ClassTeam,
    ClassTeamEvent,
)
from app.schemas.registration import (
    AthleteCreate,
    AthleteOut,
    AthleteUpdate,
    ClassTeamCreate,
    ClassTeamDetail,
    ClassTeamOut,
    ClassTeamUpdate,
    TeamEventUpdate,
)
from app.services.numbering import generate_numbers

router = APIRouter(
    prefix="/registration",
    tags=["registration"],
    dependencies=[Depends(get_current_user)],
)


# ---------- 班级 ----------
def _get_class(class_id: int, year: AcademicYear, db: Session) -> ClassTeam:
    cls = db.get(ClassTeam, class_id)
    if cls is None or cls.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="班级不存在")
    return cls


@router.get("/classes", response_model=list[ClassTeamOut])
def list_classes(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    return (
        db.query(ClassTeam)
        .filter(ClassTeam.academic_year_id == year.id)
        .order_by(ClassTeam.grade, ClassTeam.class_name)
        .all()
    )


@router.post("/classes", response_model=ClassTeamOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassTeamCreate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = ClassTeam(academic_year_id=year.id, **payload.model_dump())
    db.add(cls)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，该年级+班级已存在")
    db.refresh(cls)
    return cls


@router.put("/classes/{class_id}", response_model=ClassTeamOut)
def update_class(
    class_id: int,
    payload: ClassTeamUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = _get_class(class_id, year, db)
    for key, value in payload.model_dump().items():
        setattr(cls, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，该年级+班级已存在")
    db.refresh(cls)
    return cls


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = _get_class(class_id, year, db)
    db.delete(cls)
    db.commit()
    return None


@router.get("/classes/{class_id}", response_model=ClassTeamDetail)
def get_class_detail(
    class_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = _get_class(class_id, year, db)
    return _serialize_detail(cls, db)


# ---------- 号码生成 ----------
@router.post("/generate-numbers")
def generate(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    assigned = generate_numbers(db, year.id)
    return {"assigned": assigned}


# ---------- 学生（个人报名） ----------
def _validate_person_events(event_ids: list[int], year: AcademicYear, db: Session) -> None:
    if not event_ids:
        return
    events = db.query(Event).filter(Event.id.in_(event_ids)).all()
    found = {e.id: e for e in events}
    for eid in event_ids:
        e = found.get(eid)
        if e is None or e.academic_year_id != year.id:
            raise HTTPException(status_code=400, detail="所选项目不存在")
        if e.is_team:
            raise HTTPException(status_code=400, detail=f"「{e.name}」是团队项目，不能作为个人项目报名")


@router.post(
    "/classes/{class_id}/athletes",
    response_model=AthleteOut,
    status_code=status.HTTP_201_CREATED,
)
def add_athlete(
    class_id: int,
    payload: AthleteCreate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = _get_class(class_id, year, db)
    _validate_person_events(payload.event_ids, year, db)
    athlete = Athlete(class_team_id=cls.id, name=payload.name, gender=payload.gender.value)
    db.add(athlete)
    db.flush()
    for eid in payload.event_ids:
        db.add(AthleteEvent(athlete_id=athlete.id, event_id=eid))
    db.commit()
    db.refresh(athlete)
    return _serialize_athlete(athlete, db)


@router.put("/athletes/{athlete_id}", response_model=AthleteOut)
def update_athlete(
    athlete_id: int,
    payload: AthleteUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    athlete = _get_owned_athlete(athlete_id, year, db)
    _validate_person_events(payload.event_ids, year, db)
    athlete.name = payload.name
    athlete.gender = payload.gender.value
    # 重置项目关联
    db.query(AthleteEvent).filter(AthleteEvent.athlete_id == athlete.id).delete()
    for eid in payload.event_ids:
        db.add(AthleteEvent(athlete_id=athlete.id, event_id=eid))
    db.commit()
    db.refresh(athlete)
    return _serialize_athlete(athlete, db)


@router.delete("/athletes/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(
    athlete_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    athlete = _get_owned_athlete(athlete_id, year, db)
    db.delete(athlete)
    db.commit()
    return None


# ---------- 团队项目报名 ----------
@router.put("/classes/{class_id}/team-events", response_model=ClassTeamDetail)
def update_team_events(
    class_id: int,
    payload: TeamEventUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cls = _get_class(class_id, year, db)
    if payload.event_ids:
        events = db.query(Event).filter(Event.id.in_(payload.event_ids)).all()
        found = {e.id: e for e in events}
        for eid in payload.event_ids:
            e = found.get(eid)
            if e is None or e.academic_year_id != year.id:
                raise HTTPException(status_code=400, detail="所选项目不存在")
            if not e.is_team:
                raise HTTPException(status_code=400, detail=f"「{e.name}」不是团队项目")
    db.query(ClassTeamEvent).filter(ClassTeamEvent.class_team_id == cls.id).delete()
    for eid in payload.event_ids:
        db.add(ClassTeamEvent(class_team_id=cls.id, event_id=eid))
    db.commit()
    db.refresh(cls)
    return _serialize_detail(cls, db)


# ---------- 辅助 ----------
def _get_owned_athlete(athlete_id: int, year: AcademicYear, db: Session) -> Athlete:
    athlete = db.get(Athlete, athlete_id)
    if athlete is None:
        raise HTTPException(status_code=404, detail="学生不存在")
    cls = db.get(ClassTeam, athlete.class_team_id)
    if cls is None or cls.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="学生不存在")
    return athlete


def _athlete_event_ids(athlete_id: int, db: Session) -> list[int]:
    rows = db.query(AthleteEvent.event_id).filter(AthleteEvent.athlete_id == athlete_id).all()
    return [r[0] for r in rows]


def _serialize_athlete(athlete: Athlete, db: Session) -> AthleteOut:
    return AthleteOut(
        id=athlete.id,
        class_team_id=athlete.class_team_id,
        name=athlete.name,
        gender=athlete.gender,
        number=athlete.number,
        event_ids=_athlete_event_ids(athlete.id, db),
    )


def _serialize_detail(cls: ClassTeam, db: Session) -> ClassTeamDetail:
    athletes = sorted(cls.athletes, key=lambda a: a.id)
    team_ids = [
        r[0]
        for r in db.query(ClassTeamEvent.event_id)
        .filter(ClassTeamEvent.class_team_id == cls.id)
        .all()
    ]
    return ClassTeamDetail(
        id=cls.id,
        academic_year_id=cls.academic_year_id,
        grade=cls.grade,
        class_name=cls.class_name,
        leader_name=cls.leader_name,
        male_count=cls.male_count,
        female_count=cls.female_count,
        created_at=cls.created_at,
        athletes=[_serialize_athlete(a, db) for a in athletes],
        team_event_ids=team_ids,
    )
