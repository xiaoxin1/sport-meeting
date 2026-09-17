"""根据预赛成绩生成决赛名单。

取该项目预赛所有分道，按 rank(名次) 升序、无名次者按 result 排后，
取前 advance_count 名，重新分组填入对应决赛赛次的 组/分道。
"""
import math

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.schedule import (
    ScheduleConfig,
    ScheduleEntry,
    ScheduleGroup,
    ScheduleLane,
)


def build_finals(db: Session, prelim: ScheduleEntry) -> ScheduleEntry:
    if prelim.round_type != "预赛":
        raise ValueError("只能对预赛赛次生成决赛名单")
    final = (
        db.query(ScheduleEntry)
        .filter(
            ScheduleEntry.academic_year_id == prelim.academic_year_id,
            ScheduleEntry.event_id == prelim.event_id,
            ScheduleEntry.round_type == "决赛",
        )
        .first()
    )
    if final is None:
        raise ValueError("未找到对应的决赛赛次")

    ev = db.get(Event, prelim.event_id)
    cfg = (
        db.query(ScheduleConfig)
        .filter(ScheduleConfig.academic_year_id == prelim.academic_year_id)
        .first()
    )
    lanes = cfg.lanes if cfg else 6
    # 每组容量：项目配置了 final_teams 则按项目，否则回退全局 lanes
    gsize = ev.final_teams if ev and ev.final_teams > 0 else lanes
    advance = prelim.advance_count or gsize

    # 收集预赛所有分道
    all_lanes: list[ScheduleLane] = []
    for grp in prelim.groups:
        all_lanes.extend(grp.lanes)

    def sort_key(ln: ScheduleLane):
        # 有名次优先按名次；否则按成绩字符串；空成绩排最后
        has_rank = ln.rank is not None
        return (0 if has_rank else 1, ln.rank if has_rank else 0, ln.result or "~")

    all_lanes.sort(key=sort_key)
    qualified = all_lanes[:advance]

    # 重建决赛分组
    for grp in list(final.groups):
        db.delete(grp)
    db.flush()
    final.groups.clear()

    group_count = max(1, math.ceil(len(qualified) / gsize))
    final.group_count = group_count
    for g in range(group_count):
        grp = ScheduleGroup(group_no=g + 1)
        final.groups.append(grp)
        chunk = qualified[g * gsize : (g + 1) * gsize]
        for i, src in enumerate(chunk):
            grp.lanes.append(
                ScheduleLane(
                    lane_no=i + 1,
                    athlete_id=src.athlete_id,
                    class_team_id=src.class_team_id,
                )
            )
    db.flush()
    return final
