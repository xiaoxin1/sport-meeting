"""竞赛日程生成：规则生成（确定性）。

规则生成按以下逻辑产出一份合法日程：
1. 根据比赛天数自动分段：2天则小学排第1天，初高中排第2天；3天则小学排1.5天，初高中排1.5天
2. 分组分道：先预赛后决赛；报名 ≤ 决赛队伍数时直接决赛
3. 分组规则：一般按满跑道数分组；若末组不足一半跑道，则与上一组合并后均分为两组
4. 同项目预赛小组连续，预赛与决赛至少隔半天
5. 同场地同时刻仅一项赛事
6. 短跑、跳跃优先安排
7. 生成后校验运动员时间冲突，有冲突则调整
"""
import math
from collections import defaultdict

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

# 高负荷项目优先级（数字越小越优先）
PRIORITY_EVENTS = {
    "100米": 1,
    "200米": 1,
    "60米": 1,
    "跳远": 1,
    "跳高": 1,
    "三级跳": 1,
    "400米": 2,
    "800米": 3,
    "1500米": 4,
}

# 项目组间隔时间（分钟）。key 已归一到项目实际命名（径赛用 M，如 "100M*4"）。
# 说明：数据库里项目名形如 "60M"/"100M"/"100M*4"/"掷垒球"/"实心球"，
# 而规则文本用 "60米"/"垒球"/"侧向推实心球" 等叫法，二者需对齐。
EVENT_INTERVAL_MINUTES = {
    "60M": 2,
    "100M": 3,
    "800M": 5,
    "1000M": 5,
    "100M*2": 6,
    "100M*4": 4,
    "播种与收割": 15,
    "十人抓杆": 15,
    "跳高": 30,
    "跳远": 30,
    "袋鼠跳": 15,
    "师生同乐": 10,
}

# 按「包含子串」匹配的间隔（应对命名差异，如 掷垒球/实心球）。
_INTERVAL_CONTAINS = [
    ("垒球", 30),
    ("实心球", 30),
]


def event_interval(name: str) -> int:
    """返回项目的组间隔时间（分钟）。兼容 米/M 及垒球/实心球等命名差异。"""
    if not name:
        return 0
    key = name.upper().replace("米", "M").replace("Ｍ", "M")
    if key in EVENT_INTERVAL_MINUTES:
        return EVENT_INTERVAL_MINUTES[key]
    if name in EVENT_INTERVAL_MINUTES:
        return EVENT_INTERVAL_MINUTES[name]
    for sub, mins in _INTERVAL_CONTAINS:
        if sub in name:
            return mins
    return 0


def event_priority(ev: Event) -> int:
    """返回项目优先级，数字越小越优先（高负荷项目优先安排）。"""
    return PRIORITY_EVENTS.get(ev.name, 99)


def grade_segment(group_name: str) -> str:
    """项目组别归入 小学 / 初高中 两大赛段。"""
    return "小学" if group_name in PRIMARY else "初高中"


def half_day_slots(days: int) -> dict[str, list[tuple[int, str]]]:
    """按天数返回各赛段可用的半天槽位。

    2天：小学占第1天上午+下午，初高中占第2天上午+下午
    3天：小学占第1天全天+第2天上午(1.5天)，初高中占第2天下午+第3天全天(1.5天)
    """
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


def split_into_groups(n: int, lanes: int) -> list[int]:
    """把 n 个报名者切成若干组，返回每组人数列表。

    规则：一般按满跑道数(lanes)分组；若末组剩余人数不足半条跑道，
    则与上一组合并后均分为两组，避免出现人数过少的尾组。
    """
    if n <= 0:
        return []
    if n <= lanes:
        return [n]
    full = n // lanes
    rem = n % lanes
    sizes = [lanes] * full
    if rem == 0:
        return sizes
    if rem < math.ceil(lanes / 2):
        # 末组不足一半：与上一组(最后一个满组)合并后均分为两组
        merged = sizes.pop() + rem  # = lanes + rem
        first = math.ceil(merged / 2)
        sizes.extend([first, merged - first])
    else:
        sizes.append(rem)
    return sizes


def _fill_groups(entry: ScheduleEntry, participants: list, is_team: bool, lanes: int, db: Session):
    """把报名者依次填入 entry 的 组/分道（分组规则见 split_into_groups）。"""
    cache: dict = {}
    sizes = split_into_groups(len(participants), lanes)
    entry.group_count = len(sizes) if sizes else 1
    cursor = 0
    for g, size in enumerate(sizes):
        grp = ScheduleGroup(group_no=g + 1)
        entry.groups.append(grp)
        chunk = participants[cursor : cursor + size]
        cursor += size
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
        lanes=6,
        hard_rules=DEFAULT_HARD_RULES,
        soft_rules=DEFAULT_SOFT_RULES,
        ai_history="[]",
    )


def build_skeleton(db: Session, year_id: int, config: ScheduleConfig) -> list[tuple[Event, ScheduleEntry]]:
    """Build schedule skeleton: entries with groups and lanes assigned."""
    db.query(ScheduleEntry).filter(
        ScheduleEntry.academic_year_id == year_id
    ).delete(synchronize_session=False)
    db.flush()

    events = (
        db.query(Event).filter(Event.academic_year_id == year_id).all()
    )
    # 项目排序：优先级 -> 组别 -> 名称 -> 性别(男女连续) -> 类型
    # 修改为同一项目的男女连续完成
    events.sort(
        key=lambda e: (event_priority(e), _grade_key(e.group_name), e.name, e.gender, e.is_team)
    )

    lanes = config.lanes
    result: list[tuple[Event, ScheduleEntry]] = []

    for ev in events:
        parts = _reg_counts(db, ev)
        if not parts:
            continue  # 无报名者不排赛次
        # 组内稳定顺序
        if ev.is_team:
            parts.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))
        else:
            parts.sort(key=lambda a: (a.number or 10**9, a.id))
        count = len(parts)
        # 每组容量：项目配置了 final_teams 则按项目，否则回退全局 lanes
        gsize = ev.final_teams if ev.final_teams > 0 else lanes

        if count > gsize:
            # 预赛 + 决赛（预赛按每组容量分组，取前 gsize 名进决赛）
            prelim = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="预赛",
                advance_count=gsize,
                venue=ev.venue,
            )
            _fill_groups(prelim, parts, ev.is_team, gsize, db)
            final = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="决赛",
                advance_count=gsize,
                group_count=len(split_into_groups(gsize, gsize)) or 1,
                venue=ev.venue,
            )
            db.add(prelim)
            db.add(final)
            result.append((ev, prelim))
            result.append((ev, final))
        else:
            # 直接决赛（全部报名者按每组容量分组）
            final = ScheduleEntry(
                academic_year_id=year_id,
                event_id=ev.id,
                round_type="决赛",
                advance_count=0,
                venue=ev.venue,
            )
            _fill_groups(final, parts, ev.is_team, gsize, db)
            db.add(final)
            result.append((ev, final))

    db.flush()
    return result


def generate_schedule(db: Session, year_id: int, config: ScheduleConfig) -> None:
    """规则骨架 + 规则排期：确定性重建整份日程（清空旧的）。"""
    entries = build_skeleton(db, year_id, config)
    seg_entries: dict[str, list] = {"小学": [], "初高中": []}
    for ev, entry in entries:
        seg_entries[grade_segment(ev.group_name)].append((ev, entry))
    _assign_slots_and_times(db, year_id, config, seg_entries)
    db.flush()


def _assign_slots_and_times(db, year_id, config, seg_entries):
    """把各赛段赛次均匀分配到半天，排序号+估算时间，同时处理预赛决赛间隔和运动员冲突。"""
    slots_map = half_day_slots(config.days)
    order = 0

    # 第一轮：分配所有赛次到半天槽位
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
            entry.venue = ev.venue
            db.add(entry)

    db.flush()

    # 第二轮：检查并调整预赛决赛间隔（至少半天）
    _ensure_prelim_final_gap(db, year_id, seg_entries, slots_map)

    db.flush()

    # 注意：不再做「运动员冲突→整体挪到下个半天」的调整。
    # 那套逻辑会把上午几乎所有赛次都判为冲突并挪到下午，导致上午被掏空、
    # 径赛场上午没项目。运动员同一时刻不重叠，已由下面的时间估算按
    # 「运动员时间线」在半天内顺延保证，无需再跨半天搬运。

    # 最后：估算每个半天内的具体时间（考虑组间隔 + 场地/运动员时间线）
    _estimate_times_with_intervals(db, year_id)


def _entry_duration(e: ScheduleEntry, ev: Event | None) -> int:
    """估算一个赛次占用时长（分钟）。

    径赛按「组数 × 组间隔」估；有间隔配置的田赛/趣味项目同理。
    没有间隔配置的项目给一个保底时长。
    """
    interval = event_interval(ev.name) if ev else 0
    if interval > 0:
        return max(interval, e.group_count * interval)
    return 15


def _entry_groups_athletes(entry: ScheduleEntry) -> list[set[int]]:
    """按组返回运动员 id 集合，顺序 = 组顺序（团队项目各组返回空集）。"""
    groups = sorted(entry.groups, key=lambda g: g.group_no)
    out: list[set[int]] = []
    for grp in groups:
        out.append({ln.athlete_id for ln in grp.lanes if ln.athlete_id})
    return out


def _per_group_minutes(e: ScheduleEntry, ev: Event | None) -> int:
    """一个赛次里「每组」占用的分钟数（组间隔）。"""
    interval = event_interval(ev.name) if ev else 0
    if interval > 0:
        return interval
    gc = max(1, e.group_count)
    return max(5, _entry_duration(e, ev) // gc)


def _estimate_times_with_intervals(db: Session, year_id: int):
    """把每个半天窗口内的赛次排上具体时间。

    三条约束同时满足：
    1. **按场地维护时间线**：同场地赛次串行（一场接一场）；不同场地相互
       独立，可同一时刻并行。
    2. **运动员按「组」占用**：田赛/径赛的运动员只在**自己那一组**的时间段
       内占用（约等于一个组间隔），而非整个赛次。所以一个既扔垒球又跑步的
       学生，扔完自己那组就能去跑步——不会被整个 210 分钟的垒球赛次锁死。
    3. **同一运动员的两组时间不重叠**：安排某赛次时，若其中某组的运动员在
       别处还没空，则整个赛次顺延，直到每一组的运动员都在各自时段内空闲。
    """
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )

    # 先按半天分桶
    buckets: dict[tuple[int, str], list[ScheduleEntry]] = {}
    for e in entries:
        buckets.setdefault((e.day_index, e.period), []).append(e)

    for (day, period), items in buckets.items():
        win_start = 8 * 60 if period == "上午" else 14 * 60
        if not items:
            continue

        # 预取每个赛次的场地/每组时长/各组运动员，避免循环里反复查库
        info: dict[int, dict] = {}
        for e in items:
            ev = db.get(Event, e.event_id)
            info[e.id] = {
                "venue": (e.venue or (ev.venue if ev else "") or "默认场地"),
                "per_group": _per_group_minutes(e, ev),
                "groups_ath": _entry_groups_athletes(e),
            }

        # 每个场地一条独立时间线：{venue: 当前游标(分钟)}
        venue_cursor: dict[str, int] = defaultdict(lambda: win_start)
        # 每个运动员的「忙到几点」：{athlete_id: 结束时间(分钟)}
        athlete_busy: dict[int, int] = {}

        def feasible_start(inf: dict) -> int:
            """该赛次在当前状态下最早能开始的时间：既要本场地空闲，
            也要每一组的运动员在各自时段空闲（逐组迭代收敛）。"""
            venue = inf["venue"]
            per_group = inf["per_group"]
            groups_ath = inf["groups_ath"]
            ngrp = max(1, len(groups_ath))
            start_time = venue_cursor[venue]
            for _ in range(ngrp + 1):
                need = start_time
                for g, ath in enumerate(groups_ath):
                    g_start = start_time + g * per_group
                    for aid in ath:
                        busy = athlete_busy.get(aid)
                        if busy is not None and busy > g_start:
                            need = max(need, busy - g * per_group)
                if need == start_time:
                    break
                start_time = need
            return start_time

        # 贪心：每轮从未排赛次里挑「能最早开始」的先排，让各场地从开赛
        # 起就被有空运动员的赛次填满，不会因某项目运动员没空而整段空等。
        # 同分（如都能 8:00 开赛）按 order_no 决胜，尽量保留项目/男女相邻的原序。
        pending = list(items)
        while pending:
            best = None
            best_key = None
            for e in pending:
                st = feasible_start(info[e.id])
                key = (st, e.order_no, e.id)
                if best_key is None or key < best_key:
                    best_key, best = key, e

            e = best
            inf = info[e.id]
            venue = inf["venue"]
            per_group = inf["per_group"]
            groups_ath = inf["groups_ath"]
            ngrp = max(1, len(groups_ath))
            start_time = best_key[0]
            end_time = start_time + per_group * ngrp
            # 超窗不压回（如实记录容量情况，由用户调报名收敛）。

            e.start_time = f"{start_time // 60:02d}:{start_time % 60:02d}"
            e.end_time = f"{end_time // 60:02d}:{end_time % 60:02d}"

            venue_cursor[venue] = end_time
            for g, ath in enumerate(groups_ath):
                g_end = start_time + (g + 1) * per_group
                for aid in ath:
                    if g_end > athlete_busy.get(aid, 0):
                        athlete_busy[aid] = g_end

            pending.remove(e)

    db.flush()


def _ensure_prelim_final_gap(db, year_id, seg_entries, slots_map):
    """确保同一项目的预赛与决赛至少相隔半天。"""
    for seg, entries in seg_entries.items():
        slots = slots_map[seg]
        event_rounds = defaultdict(list)  # {event_id: [(entry, ev), ...]}

        for ev, entry in entries:
            event_rounds[ev.id].append((entry, ev))

        for event_id, rounds in event_rounds.items():
            if len(rounds) < 2:
                continue

            prelim = next((e for e, _ in rounds if e.round_type == "预赛"), None)
            final = next((e for e, _ in rounds if e.round_type == "决赛"), None)

            if not prelim or not final:
                continue

            prelim_slot = (prelim.day_index, prelim.period)
            final_slot = (final.day_index, final.period)

            # 计算槽位索引
            prelim_idx = slots.index(prelim_slot) if prelim_slot in slots else -1
            final_idx = slots.index(final_slot) if final_slot in slots else -1

            # 如果决赛在预赛之前或同一半天，需要调整
            if final_idx <= prelim_idx:
                # 尝试把决赛移到预赛后至少一个半天
                target_idx = min(prelim_idx + 1, len(slots) - 1)
                if target_idx > prelim_idx:
                    final.day_index, final.period = slots[target_idx]


def _resolve_athlete_conflicts(db, year_id, seg_entries, slots_map):
    """检查并解决运动员在同一时间段参加多个项目的冲突。

    优先级：
    1. 先尝试调整分组避免冲突
    2. 如无法解决再调整项目顺序
    3. 最后才移动到下一个时段
    """
    entries = db.query(ScheduleEntry).filter(
        ScheduleEntry.academic_year_id == year_id
    ).all()

    # 构建运动员时间槽位映射：{athlete_id: [(entry, slot), ...]}
    athlete_slots = defaultdict(list)

    for entry in entries:
        slot = (entry.day_index, entry.period)
        for grp in entry.groups:
            for ln in grp.lanes:
                if ln.athlete_id:
                    athlete_slots[ln.athlete_id].append((entry, slot))

    # 找出冲突的运动员
    conflicts = {aid: slots for aid, slots in athlete_slots.items() if len(set(s for _, s in slots)) < len(slots)}

    if not conflicts:
        return

    # 策略1：尝试通过重新分组解决冲突（此处标记需要重新分组的情况）
    # 由于重新分组涉及复杂的逻辑，我们先记录无法通过简单移动解决的冲突
    unresolved_conflicts = []

    # 策略2 & 3：调整项目顺序或移动到下一个时段
    for aid, conflicted_entries in conflicts.items():
        # 按槽位分组
        slot_groups = defaultdict(list)
        for entry, slot in conflicted_entries:
            slot_groups[slot].append(entry)

        # 找到有多个赛次的槽位
        for slot, slot_entries in slot_groups.items():
            if len(slot_entries) <= 1:
                continue

            # 确定赛段
            entry = slot_entries[0]
            ev = db.get(Event, entry.event_id)
            seg = grade_segment(ev.group_name)
            slots = slots_map[seg]

            current_idx = slots.index(slot) if slot in slots else -1
            if current_idx < 0:
                continue

            # 注意：同一运动员在同一半天参加多个赛次，即使场地不同也算冲突
            # （他无法同一时刻两头跑）。这里把多出来的赛次尽量分散到后续半天，
            # 减轻同半天内的串行压力；最终的时间不重叠由 _estimate_times_with_intervals
            # 的「运动员时间线」保证。

            # 移到下一个时段
            for i, conflicted_entry in enumerate(slot_entries[1:], 1):
                target_idx = min(current_idx + i, len(slots) - 1)
                if target_idx != current_idx:
                    conflicted_entry.day_index, conflicted_entry.period = slots[target_idx]
                else:
                    # 无法移动，记录为未解决冲突
                    unresolved_conflicts.append((aid, conflicted_entry))


def _estimate_times(db: Session, year_id: int):
    """原有的时间估算函数，保留作为备用。"""
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
        win_start = 8 * 60 if period == "上午" else 14 * 60
        win_end = 12 * 60 if period == "上午" else 18 * 60
        n = len(items)
        if not n:
            continue
        span = win_end - win_start
        slot = span // n  # 每场平均时长（分钟）
        for i, e in enumerate(items):
            s = win_start + i * slot
            en = win_end if i == n - 1 else win_start + (i + 1) * slot
            e.start_time = f"{s // 60:02d}:{s % 60:02d}"
            e.end_time = f"{en // 60:02d}:{en % 60:02d}"
    db.flush()
