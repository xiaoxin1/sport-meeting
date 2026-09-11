"""竞赛日程生成。

规则骨架（确定性）负责产出一份合法日程：分天/半天、预赛决赛、分组分道。
若启用 AI，则把配置+项目+报名情况送 DeepSeek 做排序/时间优化，
再把结果套用到骨架上。AI 不可用或失败时回退到规则骨架。
"""
import math

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.registration import (
    Athlete,
    AthleteEvent,
    ClassTeam,
    ClassTeamEvent,
)
from app.models.schedule import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleGroup,
    ScheduleLane,
)
from app.services.numbering import _class_key, _grade_key

PRIMARY = {"一年级", "二年级", "三年级", "四年级", "五年级", "六年级"}


def grade_segment(group_name: str) -> str:
    """项目组别归入 小学 / 初高中 两大赛段。"""
    return "小学" if group_name in PRIMARY else "初高中"


def half_day_slots(days: int) -> dict[str, list[tuple[int, str]]]:
    """按天数返回各赛段可用的半天槽位。"""
    if days >= 3:
        return {
            "小学": [(1, "上午"), (1, "下午"), (2, "上午")],
            "初高中": [(2, "下午"), (3, "上午"), (3, "下午")],
        }
    return {
        "小学": [(1, "上午"), (1, "下午")],
        "初高中": [(2, "上午"), (2, "下午")],
    }


def _reg_counts(db: Session, event: Event) -> list:
    """返回该项目的报名者列表：个人项目为 Athlete，团队项目为 ClassTeam。"""
    if event.is_team:
        rows = (
            db.query(ClassTeam)
            .join(ClassTeamEvent, ClassTeamEvent.class_team_id == ClassTeam.id)
            .filter(ClassTeamEvent.event_id == event.id)
            .all()
        )
    else:
        rows = (
            db.query(Athlete)
            .join(AthleteEvent, AthleteEvent.athlete_id == Athlete.id)
            .filter(AthleteEvent.event_id == event.id)
            .all()
        )
    return rows


def _class_of(db: Session, cache: dict, cid: int) -> ClassTeam | None:
    if cid not in cache:
        cache[cid] = db.get(ClassTeam, cid)
    return cache[cid]


def _fill_groups(entry: ScheduleEntry, participants: list, is_team: bool, lanes: int, db: Session):
    """把报名者依次填入 entry 的 组/分道。"""
    cache: dict = {}
    n = len(participants)
    group_count = max(1, math.ceil(n / lanes)) if n else 1
    entry.group_count = group_count
    for g in range(group_count):
        grp = ScheduleGroup(group_no=g + 1)
        entry.groups.append(grp)
        chunk = participants[g * lanes : (g + 1) * lanes]
        for i, p in enumerate(chunk):
            if is_team:
                grp.lanes.append(
                    ScheduleLane(lane_no=i + 1, class_team_id=p.id)
                )
            else:
                cls = _class_of(db, cache, p.class_team_id)
                grp.lanes.append(
                    ScheduleLane(
                        lane_no=i + 1,
                        athlete_id=p.id,
                        class_team_id=p.class_team_id,
                    )
                )


def _blank_config(year_id: int) -> ScheduleConfig:
    from app.services.schedule_rules import DEFAULT_HARD_RULES, DEFAULT_SOFT_RULES

    return ScheduleConfig(
        academic_year_id=year_id,
        days=2,
        lanes=8,
        hard_rules=DEFAULT_HARD_RULES,
        soft_rules=DEFAULT_SOFT_RULES,
        ai_history="[]",
    )


def generate_schedule(db: Session, year_id: int, config: ScheduleConfig) -> None:
    """按规则骨架重建整份日程（清空旧的）。"""
    db.query(ScheduleEntry).filter(
        ScheduleEntry.academic_year_id == year_id
    ).delete(synchronize_session=False)
    db.flush()

    events = (
        db.query(Event).filter(Event.academic_year_id == year_id).all()
    )
    # 项目排序：组别 -> 性别 -> 类型 -> 名称（与项目表默认一致）
    events.sort(
        key=lambda e: (_grade_key(e.group_name), e.gender, e.is_team, e.name)
    )

    lanes = config.lanes
    # 按赛段收集赛次，稍后分配到半天
    seg_entries: dict[str, list] = {"小学": [], "初高中": []}

    for ev in events:
        parts = _reg_counts(db, ev)
        # 组内稳定顺序
        if ev.is_team:
            parts.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))
        else:
            parts.sort(key=lambda a: (a.number or 10**9, a.id))
        count = len(parts)
        threshold = ev.final_teams if ev.final_teams > 0 else lanes
        seg = grade_segment(ev.group_name)

        if count > threshold and count > lanes:
            # 预赛 + 决赛
            prelim = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="预赛",
                advance_count=threshold,
            )
            _fill_groups(prelim, parts, ev.is_team, lanes, db)
            final = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="决赛",
                advance_count=threshold,
                group_count=max(1, math.ceil(threshold / lanes)),
            )
            seg_entries[seg].append((ev, prelim))
            seg_entries[seg].append((ev, final))
        else:
            # 直接决赛
            final = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="决赛",
                advance_count=0,
            )
            _fill_groups(final, parts, ev.is_team, lanes, db)
            seg_entries[seg].append((ev, final))

    _assign_slots_and_times(db, year_id, config, seg_entries)
    db.flush()


def _assign_slots_and_times(db, year_id, config, seg_entries):
    """把各赛段赛次均匀分配到半天，并排序号+估算时间。"""
    slots_map = half_day_slots(config.days)
    order = 0
    for seg, entries in seg_entries.items():
        slots = slots_map[seg]
        if not entries:
            continue
        per_slot = max(1, math.ceil(len(entries) / len(slots)))
        for idx, (ev, entry) in enumerate(entries):
            slot_i = min(idx // per_slot, len(slots) - 1)
            day_index, period = slots[slot_i]
            entry.day_index = day_index
            entry.period = period
            order += 1
            entry.order_no = order
            entry.venue = "田赛区" if _is_field(ev.name) else "径赛场"
            db.add(entry)

    db.flush()
    # 每个半天内按 order_no 顺序估算时间
    _estimate_times(db, year_id)


def _is_field(name: str) -> bool:
    keys = ["跳", "投", "掷", "铅球", "标枪", "铁饼"]
    return any(k in name for k in keys)


def _estimate_times(db: Session, year_id: int):
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )
    buckets: dict[tuple[int, str], list[ScheduleEntry]] = {}
    for e in entries:
        buckets.setdefault((e.day_index, e.period), []).append(e)
    for (day, period), items in buckets.items():
        cur = 8 * 60 if period == "上午" else 14 * 60  # 起始分钟
        for e in items:
            dur = 15 + e.group_count * 10  # 粗略：每组约10分钟 + 换项
            e.start_time = f"{cur // 60:02d}:{cur % 60:02d}"
            end = cur + dur
            e.end_time = f"{end // 60:02d}:{end % 60:02d}"
            cur = end + 5  # 换项间隔
    db.flush()
