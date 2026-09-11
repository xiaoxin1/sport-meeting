import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_active_year, get_current_user
from app.core.database import get_db
from app.models.academic_year import AcademicYear
from app.models.event import Event
from app.models.registration import Athlete, ClassTeam
from app.models.schedule import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleGroup,
    ScheduleLane,
)
from app.schemas.schedule import (
    AIOptimizeIn,
    EntryDetail,
    EntryOut,
    EntryUpdate,
    GroupOut,
    LaneOut,
    LaneUpdateIn,
    ResultsUpdate,
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    ScheduleOut,
)
from app.services.schedule_ai import optimize_schedule
from app.services.schedule_finals import build_finals
from app.services.schedule_gen import generate_schedule
from app.services.schedule_rules import DEFAULT_HARD_RULES, DEFAULT_SOFT_RULES

router = APIRouter(
    prefix="/schedule",
    tags=["schedule"],
    dependencies=[Depends(get_current_user)],
)


def _get_or_create_config(year: AcademicYear, db: Session) -> ScheduleConfig:
    cfg = (
        db.query(ScheduleConfig)
        .filter(ScheduleConfig.academic_year_id == year.id)
        .first()
    )
    if cfg is None:
        cfg = ScheduleConfig(
            academic_year_id=year.id,
            days=2,
            lanes=8,
            hard_rules=DEFAULT_HARD_RULES,
            soft_rules=DEFAULT_SOFT_RULES,
            ai_history="[]",
        )
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _config_out(cfg: ScheduleConfig) -> ScheduleConfigOut:
    return ScheduleConfigOut(
        id=cfg.id,
        academic_year_id=cfg.academic_year_id,
        days=cfg.days,
        lanes=cfg.lanes,
        hard_rules=cfg.hard_rules,
        soft_rules=cfg.soft_rules,
        ai_history=json.loads(cfg.ai_history or "[]"),
        generated_at=cfg.generated_at,
    )


# ---------- 配置 ----------
@router.get("/config", response_model=ScheduleConfigOut)
def get_config(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    return _config_out(_get_or_create_config(year, db))


@router.put("/config", response_model=ScheduleConfigOut)
def update_config(
    payload: ScheduleConfigUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cfg = _get_or_create_config(year, db)
    cfg.days = payload.days
    cfg.lanes = payload.lanes
    cfg.hard_rules = payload.hard_rules
    cfg.soft_rules = payload.soft_rules
    db.commit()
    db.refresh(cfg)
    return _config_out(cfg)


# ---------- 生成 / AI优化 ----------
@router.post("/generate", response_model=ScheduleConfigOut)
def regenerate(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    from datetime import datetime

    cfg = _get_or_create_config(year, db)
    cfg.ai_history = "[]"  # 重新生成清空 AI 追加消息
    generate_schedule(db, year.id, cfg)
    cfg.generated_at = datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    return _config_out(cfg)


@router.post("/ai-optimize", response_model=ScheduleConfigOut)
def ai_optimize(
    payload: AIOptimizeIn,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    cfg = _get_or_create_config(year, db)
    has_entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .count()
    )
    if not has_entries:
        raise HTTPException(status_code=400, detail="请先「重新生成」日程，再进行 AI 优化")
    history = json.loads(cfg.ai_history or "[]")
    history.append(payload.message.strip())
    cfg.ai_history = json.dumps(history, ensure_ascii=False)
    db.flush()
    try:
        optimize_schedule(db, year.id, cfg)
    except Exception as e:  # noqa: BLE001
        db.rollback()
        raise HTTPException(status_code=502, detail=f"AI 优化失败：{e}")
    db.commit()
    db.refresh(cfg)
    return _config_out(cfg)


# ---------- 读取整表 ----------
@router.get("", response_model=ScheduleOut)
def get_schedule(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    cfg = _get_or_create_config(year, db)
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .order_by(ScheduleEntry.day_index, ScheduleEntry.order_no)
        .all()
    )
    ev_cache: dict[int, Event] = {}
    out_entries = []
    for e in entries:
        ev = ev_cache.get(e.event_id) or db.get(Event, e.event_id)
        ev_cache[e.event_id] = ev
        out_entries.append(_entry_out(e, ev))
    return ScheduleOut(
        config=_config_out(cfg),
        entries=out_entries,
        day_dates=_day_dates(year, cfg),
    )


def _day_dates(year: AcademicYear, cfg: ScheduleConfig) -> dict[int, str]:
    from datetime import timedelta

    result: dict[int, str] = {}
    start = year.meet_start_date
    for d in range(1, cfg.days + 1):
        if start:
            result[d] = (start + timedelta(days=d - 1)).strftime("%Y-%m-%d")
        else:
            result[d] = f"第 {d} 天"
    return result


def _entry_out(e: ScheduleEntry, ev: Event) -> EntryOut:
    return EntryOut(
        id=e.id,
        event_id=e.event_id,
        event_name=ev.name,
        group_name=ev.group_name,
        gender=ev.gender,
        is_team=ev.is_team,
        day_index=e.day_index,
        period=e.period,
        round_type=e.round_type,
        order_no=e.order_no,
        group_count=e.group_count,
        advance_count=e.advance_count,
        start_time=e.start_time,
        end_time=e.end_time,
        venue=e.venue,
    )


# ---------- 赛次详情（分组分道 + 成绩） ----------
@router.put("/entries/{entry_id}", response_model=EntryOut)
def update_entry(
    entry_id: int,
    payload: EntryUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """手动编辑赛次时间、场地等"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    e.day_index = payload.day_index
    e.period = payload.period
    e.order_no = payload.order_no
    e.start_time = payload.start_time
    e.end_time = payload.end_time
    e.venue = payload.venue
    db.commit()
    db.refresh(e)
    ev = db.get(Event, e.event_id)
    return _entry_out(e, ev)


@router.get("/entries/{entry_id}", response_model=EntryDetail)
def get_entry_detail(
    entry_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    ev = db.get(Event, e.event_id)
    detail = EntryDetail(**_entry_out(e, ev).model_dump(), groups=[])
    ath_cache: dict[int, Athlete] = {}
    cls_cache: dict[int, ClassTeam] = {}
    for grp in sorted(e.groups, key=lambda g: g.group_no):
        g_out = GroupOut(id=grp.id, group_no=grp.group_no, lanes=[])
        for ln in sorted(grp.lanes, key=lambda x: x.lane_no):
            ath = None
            if ln.athlete_id:
                ath = ath_cache.get(ln.athlete_id) or db.get(Athlete, ln.athlete_id)
                ath_cache[ln.athlete_id] = ath
            cls = None
            if ln.class_team_id:
                cls = cls_cache.get(ln.class_team_id) or db.get(ClassTeam, ln.class_team_id)
                cls_cache[ln.class_team_id] = cls
            g_out.lanes.append(
                LaneOut(
                    id=ln.id,
                    lane_no=ln.lane_no,
                    athlete_id=ln.athlete_id,
                    class_team_id=ln.class_team_id,
                    athlete_name=ath.name if ath else None,
                    number=ath.number if ath else None,
                    grade=cls.grade if cls else None,
                    class_name=cls.class_name if cls else None,
                    result=ln.result,
                    rank=ln.rank,
                )
            )
        detail.groups.append(g_out)
    return detail


# ---------- 成绩录入 ----------
@router.put("/entries/{entry_id}/lanes", response_model=EntryDetail)
def update_lanes(
    entry_id: int,
    payload: list[LaneUpdateIn],
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """手动修改分道选手分配"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    valid_lane_ids = {ln.id for grp in e.groups for ln in grp.lanes}
    for item in payload:
        if item.lane_id not in valid_lane_ids:
            continue
        ln = db.get(ScheduleLane, item.lane_id)
        ln.athlete_id = item.athlete_id
        ln.class_team_id = item.class_team_id
    db.commit()
    return get_entry_detail(entry_id, year, db)


@router.put("/entries/{entry_id}/results", response_model=EntryDetail)
def update_results(
    entry_id: int,
    payload: ResultsUpdate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    valid_lane_ids = {ln.id for grp in e.groups for ln in grp.lanes}
    for item in payload.results:
        if item.lane_id not in valid_lane_ids:
            continue
        ln = db.get(ScheduleLane, item.lane_id)
        ln.result = item.result or ""
        ln.rank = item.rank
    db.commit()
    return get_entry_detail(entry_id, year, db)


# ---------- 生成决赛名单 ----------
@router.post("/entries/{entry_id}/build-finals", response_model=EntryDetail)
def build_finals_route(
    entry_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    try:
        final = build_finals(db, e)
    except ValueError as err:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(err))
    db.commit()
    return get_entry_detail(final.id, year, db)
