"""成绩录入时更新本年最高记录。"""
from sqlalchemy.orm import Session

from app.models.record import Record
from app.models.schedule import ScheduleEntry, ScheduleLane


def _parse_time_result(result: str) -> float:
    """解析时间类成绩（支持 mm:ss.xx 或 ss.xx 格式）返回秒数。"""
    if not result or result == "":
        return float("inf")
    parts = result.split(":")
    try:
        if len(parts) == 2:  # mm:ss.xx
            return float(parts[0]) * 60 + float(parts[1])
        else:  # ss.xx
            return float(parts[0])
    except ValueError:
        return float("inf")


def _parse_distance_result(result: str) -> float:
    """解析距离类成绩，返回浮点数。"""
    if not result or result == "":
        return 0.0
    try:
        return float(result)
    except ValueError:
        return 0.0


def _is_time_event(event_name: str) -> bool:
    """判断是否为时间类项目（越小越好）。"""
    time_keywords = ["米", "接力", "障碍"]
    return any(kw in event_name for kw in time_keywords)


def update_record_if_broken(db: Session, lane: ScheduleLane) -> None:
    """成绩录入后，判断是否打破本年记录并更新。

    逻辑：
    1. 根据 lane.entry_id 查找对应的项目信息
    2. 查询该项目的最高记录
    3. 判断是否打破记录（时间类越小越好，距离类越大越好）
    4. 如果打破记录，更新 holder_name、result 和 updated_year
    """
    if not lane.result or lane.result == "":
        return

    # 获取项目信息
    entry = db.get(ScheduleEntry, lane.entry_id)
    if not entry:
        return

    from app.models.event import Event

    event = db.query(Event).filter(Event.id == entry.event_id).first()
    if not event:
        return

    # 查询该项目的最高记录
    current_record = (
        db.query(Record)
        .filter(
            Record.academic_year_id == entry.academic_year_id,
            Record.event_name == event.name,
            Record.group_name == event.group_name,
            Record.gender == event.gender,
        )
        .first()
    )

    # 判断是否打破记录
    is_time = _is_time_event(event.name)
    should_update = False

    if is_time:
        # 时间类项目：越小越好
        new_time = _parse_time_result(lane.result)
        if current_record:
            old_time = _parse_time_result(current_record.result)
            should_update = new_time < old_time
        else:
            should_update = True
    else:
        # 距离类项目：越大越好
        new_distance = _parse_distance_result(lane.result)
        if current_record:
            old_distance = _parse_distance_result(current_record.result)
            should_update = new_distance > old_distance
        else:
            should_update = True

    if should_update:
        # 获取运动员姓名
        from app.models.athlete import Athlete

        holder_name = ""
        if lane.athlete_id:
            athlete = db.get(Athlete, lane.athlete_id)
            if athlete:
                holder_name = athlete.name

        # 获取学年名称
        from app.models.academic_year import AcademicYear

        year = db.get(AcademicYear, entry.academic_year_id)
        updated_year = year.name if year else ""

        if current_record:
            # 更新现有记录
            current_record.holder_name = holder_name
            current_record.result = lane.result
            current_record.updated_year = updated_year
        else:
            # 创建新记录
            new_record = Record(
                academic_year_id=entry.academic_year_id,
                event_name=event.name,
                group_name=event.group_name,
                gender=event.gender,
                holder_name=holder_name,
                result=lane.result,
                updated_year=updated_year,
            )
            db.add(new_record)
        db.flush()
