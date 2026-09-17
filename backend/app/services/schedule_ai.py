"""AI 竞赛日程：排期生成 / 优化。

分组分道由服务端按规则确定性完成（见 schedule_gen.build_skeleton），
AI 不再负责分组，只负责把已确定的赛次安排到合适的天次/时段/顺序/时间。

两种模式（由是否已存在日程决定）：
- 无日程：服务端先建赛次+分组+分道骨架，再把【项目/赛次】【每个赛次分组人员】
  【比赛配置】【强规则】【软规则】【本次新增优化】送 DeepSeek 排期。
- 有日程：把【当前日程】（含分组人员）+ 配置 + 规则 + 本次新增优化 送 AI 重排时间/顺序。

生成/优化后，后端做一致性校验，连同 AI 自评的问题，合并成「本次缺陷/待优化项」返回。
"""
import json

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
)
from app.services.deepseek import chat_json
from app.services.numbering import _class_key, _grade_key
from app.services.schedule_gen import build_skeleton

# 场地来源于各项目的 venue 字段，不再在此维护固定枚举
PERIODS = ["上午", "下午"]

# 排期系统提示：分组已由服务端完成，AI 只排 天次/时段/顺序/时间。
ARRANGE_SYSTEM = (
    "你是学校运动会日程编排助手。分组分道和场地已确定，你只需安排每个赛次的天次、时段、顺序和时间。\n\n"
    "输入：entries 数组，每项包含 id(赛次id)、desc(描述)、round_type(预赛/决赛)、venue(场地)、group_count(组数)、members(分组人员，用于判断冲突)。\n\n"
    "输出：纯JSON，格式：\n"
    '{"entries":[{"id":赛次id,"day":天数(1起),"period":"上午"或"下午","order":全局序号,"start":"HH:MM","end":"HH:MM"}],"issues":["问题或建议"]}\n\n'
    "规则：\n"
    "1. 所有赛次必须返回，id不可改\n"
    "2. 时间在08:00-12:00(上午)或14:00-18:00(下午)\n"
    "3. 同场地同时刻不重叠，但不同场地可以同时进行不同项目\n"
    "4. 同运动员(通过members的报名者id判断)不在同一时间参赛\n"
    "5. 同项目的男生和女生要连续完成\n"
    "6. 同项目预赛组连续，预赛与决赛至少隔半天\n"
    "7. 项目组间隔时间：60米2分钟，100米3分钟，800米5分钟，1000米5分钟，100*2米6分钟，100*4米4分钟，播种与收割15分钟，十人抓杆15分钟，垒球30分钟，跳高30分钟，跳远30分钟，袋鼠跳15分钟，师生同乐10分钟，侧向推实心球30分钟。尽可能满足间隔时间，如时间不够可以调整\n"
    "8. 发生冲突时先尝试调整分组避免冲突，如无法解决再调整项目顺序，最后才移动到下一个时段\n"
    "9. 只输出JSON，无其他文字"
)

# AI 检查系统提示：只分析当前日程，不返回新安排，仅提出优化建议。
CHECK_SYSTEM = (
    "你是学校运动会日程检查助手。请分析当前日程安排，找出可以优化的地方。\n\n"
    "输入：当前日程的 entries 数组，每项包含 id、desc(描述)、round_type(预赛/决赛)、venue(场地)、"
    "day(天数)、period(上午/下午)、start/end(时间)、group_count(组数)、members(分组人员)。\n\n"
    "输出：纯JSON，格式：\n"
    '{"suggestions":["具体的优化建议"]}\n\n'
    "检查维度：\n"
    "1. 时间冲突：同场地同时刻是否重叠，同运动员是否在同一时间参加多个项目。注意不同场地可以同时进行不同项目\n"
    "2. 赛程合理性：预赛与决赛是否至少隔半天，同项目预赛组是否连续，同项目的男生和女生是否连续完成\n"
    "3. 组间隔时间：检查是否满足各项目的组间隔时间要求（60米2分钟，100米3分钟，800米5分钟，1000米5分钟，100*2米6分钟，100*4米4分钟，播种与收割15分钟，十人抓杆15分钟，垒球30分钟，跳高30分钟，跳远30分钟，袋鼠跳15分钟，师生同乐10分钟，侧向推实心球30分钟）\n"
    "4. 时间利用：不同场地的赛事是否可以并行，减少总时长\n"
    "5. 运动员体验：高负荷项目（短跑、跳跃）是否过于集中，是否有足够休息时间\n"
    "6. 组织效率：场地切换是否频繁，裁判和设备调度是否合理\n"
    "7. 冲突解决策略：发生冲突时是否优先尝试调整分组，再调整项目顺序，最后才移动时段\n\n"
    "每条建议需具体明确，指出问题所在和改进方向。只输出JSON，无其他文字。"
)

def _reg_map(db: Session, year_id: int, events: list[Event]) -> dict[int, list]:
    """构建 {event_id: [报名者压缩...]}。个人=[aid,号码,姓名,年级班级]；团队=[cid,年级班级]。"""
    regs: dict[int, list] = {}
    for ev in events:
        if ev.is_team:
            rows = (
                db.query(ClassTeam)
                .join(ClassTeamEvent, ClassTeamEvent.class_team_id == ClassTeam.id)
                .filter(ClassTeamEvent.event_id == ev.id)
                .all()
            )
            rows.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))
            regs[ev.id] = [[c.id, f"{c.grade}{c.class_name}"] for c in rows]
        else:
            rows = (
                db.query(Athlete)
                .join(AthleteEvent, AthleteEvent.athlete_id == Athlete.id)
                .filter(AthleteEvent.event_id == ev.id)
                .all()
            )
            rows.sort(key=lambda a: (a.number or 10**9, a.id))
            regs[ev.id] = [
                [a.id, a.number or 0, a.name,
                 f"{a.class_team.grade}{a.class_team.class_name}" if a.class_team else ""]
                for a in rows
            ]
    return regs


def _member_label(db: Session, cache: dict, ev: Event, lane) -> list | None:
    """把一条分道压缩为 [报名者id, 标识]，供 AI 判断冲突参考。"""
    if ev.is_team:
        cid = lane.class_team_id
        if cid is None:
            return None
        c = cache.get(("c", cid)) or db.get(ClassTeam, cid)
        cache[("c", cid)] = c
        return [cid, f"{c.grade}{c.class_name}" if c else str(cid)]
    aid = lane.athlete_id
    if aid is None:
        return None
    a = cache.get(("a", aid)) or db.get(Athlete, aid)
    cache[("a", aid)] = a
    if a is None:
        return [aid, str(aid)]
    who = f"{a.number or ''}{a.name}"
    return [aid, who]


def _entries_payload(db: Session, entries: list[ScheduleEntry],
                     ev_by_id: dict[int, Event]) -> list[dict]:
    """把赛次（含分组人员）压缩成 AI 排期所需的紧凑结构。"""
    cache: dict = {}
    payload: list[dict] = []
    for e in entries:
        ev = ev_by_id.get(e.event_id)
        if ev is None:
            continue
        desc = f"{ev.group_name}{ev.gender}{ev.name}{'团队' if ev.is_team else ''}{e.round_type}"
        members: list[list] = []
        for grp in sorted(e.groups, key=lambda g: g.group_no):
            row = []
            for ln in sorted(grp.lanes, key=lambda x: x.lane_no):
                lbl = _member_label(db, cache, ev, ln)
                if lbl is not None:
                    row.append(lbl)
            members.append(row)
        payload.append({
            "id": e.id, "event_id": e.event_id, "desc": desc,
            "round_type": e.round_type, "venue": e.venue,
            "group_count": e.group_count, "members": members,
        })
    return payload


def _build_arrange_user(config: ScheduleConfig, entries_payload: list[dict],
                        extra: str, has_schedule: bool) -> str:
    head = "当前日程" if has_schedule else "待排赛次"
    return (
        f"比赛天数：{config.days}天\n"
        f"强规则：{config.hard_rules or '无'}\n"
        f"软规则：{config.soft_rules or '无'}\n"
        f"额外要求：{extra or '无'}\n\n"
        f"{head}（{len(entries_payload)}个赛次）：\n"
        f"{json.dumps({'entries': entries_payload}, ensure_ascii=False)}"
    )


def _overlap(s1: str, e1: str, s2: str, e2: str) -> bool:
    def m(t: str):
        try:
            h, mm = t.split(":")
            return int(h) * 60 + int(mm)
        except (ValueError, AttributeError):
            return None
    a1, b1, a2, b2 = m(s1), m(e1), m(s2), m(e2)
    if None in (a1, b1, a2, b2):
        return False
    return a1 < b2 and a2 < b1


def _merge_issues(ai_issues: list[str], backend_issues: list[str]) -> list[str]:
    out: list[str] = []
    if ai_issues:
        out.append("【AI 自评】")
        out.extend(ai_issues)
    if backend_issues:
        out.append("【系统校验】")
        out.extend(backend_issues)
    if not out:
        out.append("未发现明显冲突。")
    return out


def _apply_arrangement(db: Session, entries: list[ScheduleEntry],
                       rows: list) -> None:
    """把 AI 返回的排期(天/时段/顺序/时间)套用到已有赛次上。分组分道不变。"""
    updates: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        try:
            eid = int(row["id"])
        except (ValueError, TypeError, KeyError):
            continue
        updates[eid] = row
    for e in entries:
        u = updates.get(e.id)
        if not u:
            continue
        e.day_index = int(u.get("day", e.day_index) or e.day_index)
        e.period = u.get("period") if u.get("period") in PERIODS else e.period
        e.order_no = int(u.get("order", e.order_no) or e.order_no)
        e.start_time = str(u.get("start", "") or "") or e.start_time
        e.end_time = str(u.get("end", "") or "") or e.end_time
        # 场地来源于项目，不接受 AI 改动
    db.flush()


def _validate(db: Session, year_id: int, events: list[Event],
              regs: dict[int, list]) -> list[str]:
    """后端一致性校验，返回缺陷描述列表。"""
    issues: list[str] = []
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .all()
    )
    ev_by_id = {e.id: e for e in events}
    scheduled_event_ids = {e.event_id for e in entries}

    # 1. 有项目未排入
    for ev in events:
        if ev.id not in scheduled_event_ids and regs.get(ev.id):
            issues.append(f"项目「{ev.group_name}{ev.gender}{ev.name}」有报名但未排入任何赛次")

    # 2. 报名者未分道 / 收集运动员时间槽
    athlete_slots: dict[int, list[tuple]] = {}
    for e in entries:
        ev = ev_by_id.get(e.event_id)
        if ev is None:
            continue
        placed: set[int] = set()
        for grp in e.groups:
            for ln in grp.lanes:
                mid = ln.class_team_id if ev.is_team else ln.athlete_id
                if mid is not None:
                    placed.add(mid)
                if not ev.is_team and ln.athlete_id is not None:
                    athlete_slots.setdefault(ln.athlete_id, []).append(
                        (e.day_index, e.period, e.start_time, e.end_time,
                         f"{ev.name}{e.round_type}", e.venue)
                    )
        expected = {r[0] for r in regs.get(e.event_id, [])}
        if e.round_type != "决赛" or not expected:
            missing = expected - placed
            if missing:
                issues.append(
                    f"项目「{ev.group_name}{ev.gender}{ev.name}」{e.round_type}"
                    f"有 {len(missing)} 名报名者未被分道"
                )

    # 3. 同一运动员时间重叠（只检查同一场地或时间真正重叠的情况）
    for aid, slots in athlete_slots.items():
        hit = False
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                a, b = slots[i], slots[j]
                # 同一天同一时段才需要检查时间重叠
                if a[0] == b[0] and a[1] == b[1]:
                    if _overlap(a[2], a[3], b[2], b[3]):
                        issues.append(
                            f"运动员(id={aid}) 时间冲突：{a[4]} 与 {b[4]} 在第{a[0]}天{a[1]}重叠"
                        )
                        hit = True
                        break
            if hit:
                break

    # 4. 同场地同天同时段时间重叠
    venue_slots: dict[tuple, list[tuple]] = {}
    for e in entries:
        venue_slots.setdefault((e.day_index, e.period, e.venue), []).append(
            (e.start_time, e.end_time, e.id)
        )
    for key, slots in venue_slots.items():
        hit = False
        for i in range(len(slots)):
            for j in range(i + 1, len(slots)):
                if _overlap(slots[i][0], slots[i][1], slots[j][0], slots[j][1]):
                    issues.append(f"场地「{key[2]}」第{key[0]}天{key[1]}存在时间重叠的赛次（赛次id: {slots[i][2]}, {slots[j][2]}）")
                    hit = True
                    break
            if hit:
                break

    return issues


def generate_schedule_ai(db: Session, year_id: int, config: ScheduleConfig,
                         extra: str = "") -> list[str]:
    """无日程时：服务端确定性分组建骨架，AI 只排期。返回缺陷/待优化项列表。"""
    events = db.query(Event).filter(Event.academic_year_id == year_id).all()
    if not events:
        raise ValueError("尚无比赛项目，无法生成日程")

    # 1. 服务端按规则建赛次+分组+分道骨架（会清空旧日程）
    skeleton = build_skeleton(db, year_id, config)
    if not skeleton:
        raise ValueError("没有任何报名，无法生成日程")
    entries = [entry for _, entry in skeleton]
    ev_by_id = {ev.id: ev for ev, _ in skeleton}

    # 2. 只把赛次(含分组人员)、规则、天数/跑道送 AI 排期
    payload = _entries_payload(db, entries, ev_by_id)
    user = _build_arrange_user(config, payload, extra, has_schedule=False)
    result = chat_json(db, ARRANGE_SYSTEM, user)
    rows = result.get("entries", [])
    if not rows:
        raise RuntimeError("AI 未返回任何赛次安排")

    _apply_arrangement(db, entries, rows)

    events_list = list(ev_by_id.values())
    regs = _reg_map(db, year_id, events_list)
    ai_issues = [str(x) for x in (result.get("issues") or [])]
    backend_issues = _validate(db, year_id, events_list, regs)
    merged = _merge_issues(ai_issues, backend_issues)

    db.flush()

    return merged


def optimize_schedule(db: Session, year_id: int, config: ScheduleConfig,
                      extra: str = "") -> list[str]:
    """有日程时：分组分道不变，AI 重排时间/顺序。返回缺陷/待优化项列表。"""
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )
    if not entries:
        raise ValueError("没有可优化的赛次")

    ev_cache: dict[int, Event] = {}
    for e in entries:
        if e.event_id not in ev_cache:
            ev_cache[e.event_id] = db.get(Event, e.event_id)

    payload = _entries_payload(db, entries, ev_cache)
    user = _build_arrange_user(config, payload, extra, has_schedule=True)
    result = chat_json(db, ARRANGE_SYSTEM, user)
    rows = result.get("entries", [])
    if not rows:
        raise RuntimeError("AI 未返回任何赛次安排")

    _apply_arrangement(db, entries, rows)

    events_list = [ev for ev in ev_cache.values() if ev is not None]
    regs = _reg_map(db, year_id, events_list)
    ai_issues = [str(x) for x in (result.get("issues") or [])]
    backend_issues = _validate(db, year_id, events_list, regs)
    merged = _merge_issues(ai_issues, backend_issues)

    db.flush()

    return merged


def check_schedule(db: Session, year_id: int, config: ScheduleConfig,
                   extra: str = "") -> list[str]:
    """AI 检查当前日程：不修改日程，只返回优化建议。"""
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )
    if not entries:
        raise ValueError("没有可检查的赛次")

    ev_cache: dict[int, Event] = {}
    for e in entries:
        if e.event_id not in ev_cache:
            ev_cache[e.event_id] = db.get(Event, e.event_id)

    # 构建当前日程的完整信息（包含时间）
    payload = _entries_payload(db, entries, ev_cache)

    # 为每个赛次添加当前的时间安排
    for item, entry in zip(payload, entries):
        item["day"] = entry.day_index
        item["period"] = entry.period
        item["start"] = entry.start_time
        item["end"] = entry.end_time

    # 构建检查请求
    user_parts = [
        f"比赛天数：{config.days}天",
        f"强规则：{config.hard_rules}",
        f"软规则：{config.soft_rules}",
    ]
    if extra:
        user_parts.append(f"本次关注：{extra}")
    user_parts.append(f"\n当前日程安排：\n{json.dumps(payload, ensure_ascii=False, indent=2)}")
    user = "\n".join(user_parts)

    result = chat_json(db, CHECK_SYSTEM, user)
    suggestions = result.get("suggestions", [])
    if not suggestions:
        return ["未发现明显问题，当前日程安排合理。"]

    return [str(s) for s in suggestions]

