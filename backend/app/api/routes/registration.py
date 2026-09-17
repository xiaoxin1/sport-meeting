from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import (
    Principal,
    get_active_year,
    get_current_principal,
    require_admin,
)
from app.core.config import settings
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
    EventRegistrationEntry,
    EventRegistrationList,
    RegistrationSaveRequest,
    TeamEventUpdate,
)
from app.services.numbering import _class_key, _grade_key, generate_numbers

router = APIRouter(prefix="/registration", tags=["registration"])


# ---------- 权限辅助 ----------
def _ensure_class_access(principal: Principal, class_id: int) -> None:
    """领队只能访问自己的班级；管理员不限。"""
    if not principal.is_admin and principal.class_team_id != class_id:
        raise HTTPException(status_code=403, detail="无权访问其他班级的报名数据")


def _is_relay(name: str) -> bool:
    """接力项目（可兼报，不计入个人限报数与每项限报数）。"""
    return "*" in name or "接力" in name


# ---------- 报名规则配置 ----------
@router.get("/config")
def registration_config(_: Principal = Depends(get_current_principal)):
    return {
        "hint": settings.reg_hint,
        "max_per_event": settings.reg_max_per_event,
        "max_events_per_person": settings.reg_max_events_per_person,
    }


# ---------- 班级 ----------
def _get_class(class_id: int, year: AcademicYear, db: Session) -> ClassTeam:
    cls = db.get(ClassTeam, class_id)
    if cls is None or cls.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="班级不存在")
    return cls


def _serialize_class(cls: ClassTeam, show_password: bool) -> ClassTeamOut:
    return ClassTeamOut(
        id=cls.id,
        academic_year_id=cls.academic_year_id,
        grade=cls.grade,
        class_name=cls.class_name,
        leader_name=cls.leader_name,
        male_count=cls.male_count,
        female_count=cls.female_count,
        created_at=cls.created_at,
        password=cls.password if show_password else "",
    )


@router.get("/classes", response_model=list[ClassTeamOut])
def list_classes(
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    q = db.query(ClassTeam).filter(ClassTeam.academic_year_id == year.id)
    if not principal.is_admin:
        # 领队只能看到自己班级这一行
        q = q.filter(ClassTeam.id == principal.class_team_id)
    rows = q.all()
    rows.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))
    return [_serialize_class(c, principal.is_admin) for c in rows]


@router.post("/classes", response_model=ClassTeamOut, status_code=status.HTTP_201_CREATED)
def create_class(
    payload: ClassTeamCreate,
    _: Principal = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    data = payload.model_dump()
    pwd = (data.pop("password", None) or "").strip() or settings.leader_default_password
    cls = ClassTeam(academic_year_id=year.id, password=pwd, **data)
    db.add(cls)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，该年级+班级已存在")
    db.refresh(cls)
    return _serialize_class(cls, True)


@router.put("/classes/{class_id}", response_model=ClassTeamOut)
def update_class(
    class_id: int,
    payload: ClassTeamUpdate,
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    _ensure_class_access(principal, class_id)
    cls = _get_class(class_id, year, db)
    data = payload.model_dump()
    pwd = data.pop("password", None)
    if principal.is_admin:
        # 管理员可改全部字段；密码留空则保持原值
        for key, value in data.items():
            setattr(cls, key, value)
        if pwd is not None and pwd.strip():
            cls.password = pwd.strip()
    else:
        # 领队只能改男生/女生人数，不能改年级/班级/领队姓名/密码
        cls.male_count = data["male_count"]
        cls.female_count = data["female_count"]
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="同一学年下，该年级+班级已存在")
    db.refresh(cls)
    return _serialize_class(cls, principal.is_admin)


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    _: Principal = Depends(require_admin),
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
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    _ensure_class_access(principal, class_id)
    cls = _get_class(class_id, year, db)
    return _serialize_detail(cls, db)


# ---------- 号码生成（仅管理员） ----------
@router.post("/generate-numbers")
def generate(
    _: Principal = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
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


@router.get("/athletes", response_model=list[AthleteOut])
def list_athletes(
    _: Principal = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """获取本学年所有选手（用于日程分组编辑，仅管理员）"""
    cls_ids = [
        c.id for c in db.query(ClassTeam).filter(ClassTeam.academic_year_id == year.id).all()
    ]
    athletes = db.query(Athlete).filter(Athlete.class_team_id.in_(cls_ids)).all()
    return [_serialize_athlete(a, db) for a in athletes]


# ---------- 报名整体保存（详情页「保存」按钮） ----------
def _validate_registration(
    req: RegistrationSaveRequest, year: AcademicYear, db: Session
) -> dict[int, Event]:
    """按配置强制校验：每项限报人数、每人限报个人项目数。接力项目豁免。"""
    max_per_event = settings.reg_max_per_event
    max_events = settings.reg_max_events_per_person

    # 运动员名单中的男/女人数必须与填写的男/女生人数一致
    male_in_list = sum(1 for a in req.athletes if a.gender.value == "男")
    female_in_list = sum(1 for a in req.athletes if a.gender.value == "女")
    if male_in_list != req.male_count:
        raise HTTPException(
            status_code=400,
            detail=f"运动员名单中男生 {male_in_list} 人，与填写的男生人数 {req.male_count} 不一致",
        )
    if female_in_list != req.female_count:
        raise HTTPException(
            status_code=400,
            detail=f"运动员名单中女生 {female_in_list} 人，与填写的女生人数 {req.female_count} 不一致",
        )

    all_ids = {eid for a in req.athletes for eid in a.event_ids}
    all_ids |= set(req.team_event_ids)
    events: dict[int, Event] = {}
    if all_ids:
        for e in db.query(Event).filter(Event.id.in_(all_ids)).all():
            events[e.id] = e
    for eid in all_ids:
        e = events.get(eid)
        if e is None or e.academic_year_id != year.id:
            raise HTTPException(status_code=400, detail="所选项目不存在")

    # 个人项目 event_ids 不能是团队项目；团队项目 id 必须是团队项目
    per_event_count: Counter[int] = Counter()
    for a in req.athletes:
        non_relay = 0
        for eid in a.event_ids:
            e = events[eid]
            if e.is_team:
                raise HTTPException(
                    status_code=400,
                    detail=f"「{a.name}」报名了团队项目「{e.name}」，请在团队项目中选择",
                )
            per_event_count[eid] += 1
            if not _is_relay(e.name):
                non_relay += 1
        if non_relay > max_events:
            raise HTTPException(
                status_code=400,
                detail=f"「{a.name}」报名了 {non_relay} 个个人项目，每位运动员限报 {max_events} 项（接力除外）",
            )

    for eid, cnt in per_event_count.items():
        e = events[eid]
        if _is_relay(e.name):
            continue
        if cnt > max_per_event:
            raise HTTPException(
                status_code=400,
                detail=f"项目「{e.name}」报名了 {cnt} 人，每个项目限报 {max_per_event} 人",
            )

    for eid in req.team_event_ids:
        if not events[eid].is_team:
            raise HTTPException(status_code=400, detail=f"「{events[eid].name}」不是团队项目")
    return events


@router.put("/classes/{class_id}/registration", response_model=ClassTeamDetail)
def save_registration(
    class_id: int,
    payload: RegistrationSaveRequest,
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """整体保存一个班级的报名：人数 + 运动员名单 + 团队项目。点击「保存」才生效。"""
    _ensure_class_access(principal, class_id)
    cls = _get_class(class_id, year, db)
    _validate_registration(payload, year, db)

    # 人数
    cls.male_count = payload.male_count
    cls.female_count = payload.female_count

    # 运动员：按 id 合并（更新已有、删除缺失、新增无 id 的），保留已生成号码
    existing = {a.id: a for a in cls.athletes}
    keep_ids: set[int] = set()
    for item in payload.athletes:
        if item.id is not None and item.id in existing:
            ath = existing[item.id]
            ath.name = item.name
            ath.gender = item.gender.value
            keep_ids.add(ath.id)
        else:
            ath = Athlete(class_team_id=cls.id, name=item.name, gender=item.gender.value)
            db.add(ath)
            db.flush()
            keep_ids.add(ath.id)
        db.query(AthleteEvent).filter(AthleteEvent.athlete_id == ath.id).delete()
        for eid in item.event_ids:
            db.add(AthleteEvent(athlete_id=ath.id, event_id=eid))
    for aid, ath in existing.items():
        if aid not in keep_ids:
            db.delete(ath)

    # 团队项目
    db.query(ClassTeamEvent).filter(ClassTeamEvent.class_team_id == cls.id).delete()
    for eid in payload.team_event_ids:
        db.add(ClassTeamEvent(class_team_id=cls.id, event_id=eid))

    db.commit()
    db.refresh(cls)
    return _serialize_detail(cls, db)


@router.post(
    "/classes/{class_id}/athletes",
    response_model=AthleteOut,
    status_code=status.HTTP_201_CREATED,
)
def add_athlete(
    class_id: int,
    payload: AthleteCreate,
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    _ensure_class_access(principal, class_id)
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
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    athlete = _get_owned_athlete(athlete_id, year, db)
    _ensure_class_access(principal, athlete.class_team_id)
    _validate_person_events(payload.event_ids, year, db)
    athlete.name = payload.name
    athlete.gender = payload.gender.value
    db.query(AthleteEvent).filter(AthleteEvent.athlete_id == athlete.id).delete()
    for eid in payload.event_ids:
        db.add(AthleteEvent(athlete_id=athlete.id, event_id=eid))
    db.commit()
    db.refresh(athlete)
    return _serialize_athlete(athlete, db)


@router.delete("/athletes/{athlete_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_athlete(
    athlete_id: int,
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    athlete = _get_owned_athlete(athlete_id, year, db)
    _ensure_class_access(principal, athlete.class_team_id)
    db.delete(athlete)
    db.commit()
    return None


# ---------- 团队项目报名 ----------
@router.put("/classes/{class_id}/team-events", response_model=ClassTeamDetail)
def update_team_events(
    class_id: int,
    payload: TeamEventUpdate,
    principal: Principal = Depends(get_current_principal),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    _ensure_class_access(principal, class_id)
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


# ---------- 项目报名名单（仅管理员） ----------
@router.get("/events/{event_id}/registrations", response_model=EventRegistrationList)
def event_registrations(
    event_id: int,
    _: Principal = Depends(require_admin),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    event = db.get(Event, event_id)
    if event is None or event.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="项目不存在")

    entries: list[EventRegistrationEntry] = []
    if event.is_team:
        rows = (
            db.query(ClassTeam)
            .join(ClassTeamEvent, ClassTeamEvent.class_team_id == ClassTeam.id)
            .filter(ClassTeamEvent.event_id == event_id)
            .all()
        )
        entries = [
            EventRegistrationEntry(class_id=c.id, grade=c.grade, class_name=c.class_name)
            for c in rows
        ]
    else:
        rows = (
            db.query(Athlete, ClassTeam)
            .join(AthleteEvent, AthleteEvent.athlete_id == Athlete.id)
            .join(ClassTeam, ClassTeam.id == Athlete.class_team_id)
            .filter(AthleteEvent.event_id == event_id)
            .all()
        )
        entries = [
            EventRegistrationEntry(
                class_id=c.id,
                grade=c.grade,
                class_name=c.class_name,
                athlete_name=a.name,
                number=a.number,
            )
            for a, c in rows
        ]

    entries.sort(
        key=lambda e: (_grade_key(e.grade), _class_key(e.class_name), e.athlete_name or "")
    )
    return EventRegistrationList(
        event_id=event.id,
        event_name=event.name,
        is_team=event.is_team,
        entries=entries,
    )


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
    cls = db.get(ClassTeam, athlete.class_team_id)
    return AthleteOut(
        id=athlete.id,
        class_team_id=athlete.class_team_id,
        name=athlete.name,
        gender=athlete.gender,
        number=athlete.number,
        event_ids=_athlete_event_ids(athlete.id, db),
        grade=cls.grade if cls else "",
        class_name=cls.class_name if cls else "",
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
        password="",
        athletes=[_serialize_athlete(a, db) for a in athletes],
        team_event_ids=team_ids,
    )
