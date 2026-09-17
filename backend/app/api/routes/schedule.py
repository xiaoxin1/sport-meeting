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
    AIOptimizeOut,
    ClearScheduleIn,
    EntryCreate,
    EntryDetail,
    EntryOut,
    EntryUpdate,
    GroupOut,
    LaneCreate,
    LaneOut,
    LaneUpdateIn,
    ResultsUpdate,
    ScheduleConfigOut,
    ScheduleConfigUpdate,
    ScheduleOut,
)
from app.core.security import verify_password
from app.models.user import User
from app.services.schedule_ai import optimize_schedule, check_schedule
from app.services.schedule_gen import generate_schedule
from app.services.record_update import update_record_if_broken
from app.services.schedule_finals import build_finals
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
            lanes=6,
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
    """更新配置（仅跑道数）"""
    if payload.lanes < 2 or payload.lanes > 12:
        raise HTTPException(status_code=400, detail="跑道数必须在 2-12 之间")
    cfg = _get_or_create_config(year, db)
    cfg.lanes = payload.lanes
    db.commit()
    db.refresh(cfg)
    return _config_out(cfg)


# ---------- 清除日程 / AI 生成·优化 ----------
@router.post("/clear", response_model=ScheduleConfigOut)
def clear_schedule(
    payload: ClearScheduleIn,
    year: AcademicYear = Depends(get_active_year),
    current: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """清除当前学年全部日程，需管理员密码确认。"""
    if not verify_password(payload.admin_password, current.password_hash):
        raise HTTPException(status_code=403, detail="管理员密码错误")
    cfg = _get_or_create_config(year, db)
    db.query(ScheduleEntry).filter(
        ScheduleEntry.academic_year_id == year.id
    ).delete(synchronize_session=False)
    cfg.ai_history = "[]"
    cfg.generated_at = None
    db.commit()
    db.refresh(cfg)
    return _config_out(cfg)


@router.post("/generate", response_model=ScheduleOut)
def generate_by_rules(
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """规则生成日程：清空旧日程，按规则确定性重建。"""
    from datetime import datetime

    cfg = _get_or_create_config(year, db)
    try:
        generate_schedule(db, year.id, cfg)
        cfg.generated_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"规则生成失败：{e}")

    return get_schedule(year, db)


@router.post("/ai-optimize", response_model=AIOptimizeOut)
def ai_optimize(
    payload: AIOptimizeIn,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """AI 优化已有日程。需要先有日程才能使用。"""
    from datetime import datetime

    cfg = _get_or_create_config(year, db)
    has_entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .count()
    )

    if not has_entries:
        raise HTTPException(status_code=400, detail="请先使用规则生成日程，再进行 AI 优化")

    extra = (payload.message or "").strip()
    if extra:
        history = json.loads(cfg.ai_history or "[]")
        history.append(extra)
        cfg.ai_history = json.dumps(history, ensure_ascii=False)
        db.flush()

    try:
        issues = optimize_schedule(db, year.id, cfg, extra=extra)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"AI 优化失败：{e}")

    cfg.generated_at = datetime.utcnow()
    db.commit()
    return AIOptimizeOut(issues=issues, mode="optimize")


@router.post("/ai-check", response_model=AIOptimizeOut)
def ai_check(
    payload: AIOptimizeIn,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """AI 检查已有日程，返回优化建议，但不修改日程。"""
    cfg = _get_or_create_config(year, db)
    has_entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .count()
    )

    if not has_entries:
        raise HTTPException(status_code=400, detail="请先使用规则生成日程，再进行 AI 检查")

    extra = (payload.message or "").strip()

    try:
        suggestions = check_schedule(db, year.id, cfg, extra=extra)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=502, detail=f"AI 检查失败：{e}")

    db.commit()
    return AIOptimizeOut(issues=suggestions, mode="check")


# ---------- 读取整表 ----------
@router.get("", response_model=ScheduleOut)
def get_schedule(
    year: AcademicYear = Depends(get_active_year), db: Session = Depends(get_db)
):
    cfg = _get_or_create_config(year, db)
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .order_by(
            ScheduleEntry.day_index,
            ScheduleEntry.period,
            ScheduleEntry.start_time,
            ScheduleEntry.order_no,
        )
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
    """手动编辑赛次：只允许改开始/结束时间与场地，当天始终按时间排序"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    e.start_time = payload.start_time
    e.end_time = payload.end_time
    e.venue = payload.venue
    db.commit()
    db.refresh(e)
    ev = db.get(Event, e.event_id)
    return _entry_out(e, ev)


@router.post("/entries", response_model=EntryOut, status_code=status.HTTP_201_CREATED)
def create_entry(
    payload: EntryCreate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """新增一个空赛次（分组分道稍后在详情里手动添加）"""
    ev = db.get(Event, payload.event_id)
    if ev is None or ev.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="项目不存在")
    # order_no 追加到末尾
    max_order = (
        db.query(ScheduleEntry.order_no)
        .filter(ScheduleEntry.academic_year_id == year.id)
        .order_by(ScheduleEntry.order_no.desc())
        .first()
    )
    e = ScheduleEntry(
        academic_year_id=year.id,
        event_id=payload.event_id,
        day_index=payload.day_index,
        period=payload.period,
        round_type=payload.round_type,
        order_no=(max_order[0] if max_order else 0) + 1,
        group_count=0,
        advance_count=0,
        start_time=payload.start_time,
        end_time=payload.end_time,
        venue=payload.venue,
    )
    db.add(e)
    db.commit()
    db.refresh(e)
    return _entry_out(e, ev)


@router.delete("/entries/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    db.delete(e)
    db.commit()


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


@router.post("/entries/{entry_id}/groups", response_model=EntryDetail)
def add_group(
    entry_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """在赛次末尾新增一个空的小组"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    max_no = max([g.group_no for g in e.groups], default=0)
    grp = ScheduleGroup(entry_id=e.id, group_no=max_no + 1)
    db.add(grp)
    e.group_count = len(e.groups) + 1
    db.commit()
    return get_entry_detail(entry_id, year, db)


@router.delete("/entries/{entry_id}/groups/{group_id}", response_model=EntryDetail)
def delete_group(
    entry_id: int,
    group_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """删除赛次下的一个小组（含其分道），并重排剩余小组编号"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    grp = db.get(ScheduleGroup, group_id)
    if grp is None or grp.entry_id != e.id:
        raise HTTPException(status_code=404, detail="小组不存在")
    db.delete(grp)
    db.flush()
    # 重排剩余小组编号，保持连续
    remaining = sorted(
        [g for g in e.groups if g.id != group_id], key=lambda g: g.group_no
    )
    for i, g in enumerate(remaining, start=1):
        g.group_no = i
    e.group_count = len(remaining)
    db.commit()
    return get_entry_detail(entry_id, year, db)


@router.post("/entries/{entry_id}/lanes/add", response_model=EntryDetail)
def add_lane(
    entry_id: int,
    payload: LaneCreate,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """在指定小组内新增一个分道/席位"""
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    grp = db.get(ScheduleGroup, payload.group_id)
    if grp is None or grp.entry_id != e.id:
        raise HTTPException(status_code=404, detail="小组不存在")
    max_lane = max([ln.lane_no for ln in grp.lanes], default=0)
    ln = ScheduleLane(
        group_id=grp.id,
        lane_no=max_lane + 1,
        athlete_id=payload.athlete_id,
        class_team_id=payload.class_team_id,
    )
    db.add(ln)
    db.commit()
    return get_entry_detail(entry_id, year, db)


@router.delete("/entries/{entry_id}/lanes/{lane_id}", response_model=EntryDetail)
def delete_lane(
    entry_id: int,
    lane_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    e = db.get(ScheduleEntry, entry_id)
    if e is None or e.academic_year_id != year.id:
        raise HTTPException(status_code=404, detail="赛次不存在")
    valid_lane_ids = {ln.id for grp in e.groups for ln in grp.lanes}
    if lane_id not in valid_lane_ids:
        raise HTTPException(status_code=404, detail="分道不存在")
    ln = db.get(ScheduleLane, lane_id)
    db.delete(ln)
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

    ev = db.get(Event, e.event_id)
    valid_lane_ids = {ln.id for grp in e.groups for ln in grp.lanes}

    for item in payload.results:
        if item.lane_id not in valid_lane_ids:
            continue
        ln = db.get(ScheduleLane, item.lane_id)
        ln.result = item.result or ""
        ln.rank = item.rank

        # 自动更新本年记录
        if ln.result and ln.result.strip():
            update_record_if_broken(db, ln)

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
