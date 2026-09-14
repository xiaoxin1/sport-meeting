"""分数统计计算服务。"""
from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.record import Record
from app.models.registration import Athlete, ClassTeam
from app.models.schedule import ScheduleEntry, ScheduleGroup, ScheduleLane
from app.models.score import AthleteScore, ClassScore, ScoreDetail

# 名次对应的基础分
RANK_SCORES = {1: 7, 2: 5, 3: 4, 4: 3, 5: 2, 6: 1}


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


def _check_record_broken(
    event_name: str, group_name: str, gender: str, result: str, academic_year_id: int, db: Session
) -> bool:
    """检查是否打破历史记录。

    逻辑：
    1. 查询对应的 Record
    2. 如果 historical_result 为空，返回 False（无历史基准）
    3. 时间类：成绩 < 历史记录 = 打破
    4. 距离类：成绩 > 历史记录 = 打破
    """
    record = (
        db.query(Record)
        .filter(
            Record.academic_year_id == academic_year_id,
            Record.event_name == event_name,
            Record.group_name == group_name,
            Record.gender == gender,
        )
        .first()
    )

    if not record or not record.historical_result:
        return False

    is_time = _is_time_event(event_name)

    if is_time:
        new_time = _parse_time_result(result)
        old_time = _parse_time_result(record.historical_result)
        return new_time < old_time
    else:
        new_distance = _parse_distance_result(result)
        old_distance = _parse_distance_result(record.historical_result)
        return new_distance > old_distance


def calculate_scores(academic_year_id: int, db: Session) -> dict:
    """一键统计：计算当前学年的所有得分。

    流程：
    1. 删除该学年的所有统计数据
    2. 查询所有决赛成绩，创建得分明细
    3. 汇总到个人得分和班级得分
    4. 计算年级内排名
    5. 返回统计摘要
    """
    # 1. 清空该学年的统计数据
    db.execute(delete(ScoreDetail).where(ScoreDetail.academic_year_id == academic_year_id))
    db.execute(delete(AthleteScore).where(AthleteScore.academic_year_id == academic_year_id))
    db.execute(delete(ClassScore).where(ClassScore.academic_year_id == academic_year_id))
    db.flush()

    # 2. 查询所有决赛的 ScheduleLane
    finals = (
        db.query(ScheduleLane)
        .join(ScheduleGroup, ScheduleLane.group_id == ScheduleGroup.id)
        .join(ScheduleEntry, ScheduleGroup.entry_id == ScheduleEntry.id)
        .filter(
            ScheduleEntry.academic_year_id == academic_year_id,
            ScheduleEntry.round_type == "决赛",
            ScheduleLane.rank.isnot(None),
            ScheduleLane.rank >= 1,
            ScheduleLane.rank <= 6,
        )
        .all()
    )

    # 3. 创建得分明细
    for lane in finals:
        # 获取项目信息
        group = db.get(ScheduleGroup, lane.group_id)
        entry = db.get(ScheduleEntry, group.entry_id)
        event = db.get(Event, entry.event_id)

        # 获取基础分
        base_score = RANK_SCORES.get(lane.rank, 0)
        if base_score == 0:
            continue

        # 检查是否打破记录
        is_broken = _check_record_broken(
            event.name, event.group_name, event.gender, lane.result, academic_year_id, db
        )
        final_score = base_score * 2 if is_broken else base_score

        # 确定归属信息
        if event.is_team:
            # 团队项目
            class_team_id = lane.class_team_id
            athlete_id = None
        else:
            # 个人项目
            athlete = db.get(Athlete, lane.athlete_id)
            if not athlete:
                continue
            class_team_id = athlete.class_team_id
            athlete_id = athlete.id

        # 创建得分明细
        detail = ScoreDetail(
            academic_year_id=academic_year_id,
            schedule_lane_id=lane.id,
            event_name=event.name,
            group_name=event.group_name,
            gender=event.gender,
            is_team_event=event.is_team,
            class_team_id=class_team_id,
            athlete_id=athlete_id,
            rank=lane.rank,
            result=lane.result,
            base_score=base_score,
            is_record_broken=is_broken,
            final_score=final_score,
        )
        db.add(detail)

    db.flush()

    # 4. 汇总个人得分
    athlete_scores_data = {}
    details = db.query(ScoreDetail).filter(
        ScoreDetail.academic_year_id == academic_year_id,
        ScoreDetail.athlete_id.isnot(None),
    ).all()

    for detail in details:
        if detail.athlete_id not in athlete_scores_data:
            athlete = db.get(Athlete, detail.athlete_id)
            class_team = db.get(ClassTeam, detail.class_team_id)
            athlete_scores_data[detail.athlete_id] = {
                "athlete_id": detail.athlete_id,
                "class_team_id": detail.class_team_id,
                "grade": class_team.grade,
                "athlete_name": athlete.name,
                "total_score": 0.0,
            }
        athlete_scores_data[detail.athlete_id]["total_score"] += detail.final_score

    # 按年级分组并计算排名
    grades_athletes = {}
    for data in athlete_scores_data.values():
        grade = data["grade"]
        if grade not in grades_athletes:
            grades_athletes[grade] = []
        grades_athletes[grade].append(data)

    for grade, athletes in grades_athletes.items():
        athletes.sort(key=lambda x: x["total_score"], reverse=True)
        for rank, athlete_data in enumerate(athletes, 1):
            athlete_score = AthleteScore(
                academic_year_id=academic_year_id,
                athlete_id=athlete_data["athlete_id"],
                class_team_id=athlete_data["class_team_id"],
                grade=athlete_data["grade"],
                athlete_name=athlete_data["athlete_name"],
                total_score=athlete_data["total_score"],
                rank_in_grade=rank,
            )
            db.add(athlete_score)

    # 5. 汇总班级得分
    class_scores_data = {}
    all_details = db.query(ScoreDetail).filter(
        ScoreDetail.academic_year_id == academic_year_id
    ).all()

    for detail in all_details:
        if detail.class_team_id not in class_scores_data:
            class_team = db.get(ClassTeam, detail.class_team_id)
            class_scores_data[detail.class_team_id] = {
                "class_team_id": detail.class_team_id,
                "grade": class_team.grade,
                "class_name": class_team.class_name,
                "total_score": 0.0,
            }
        class_scores_data[detail.class_team_id]["total_score"] += detail.final_score

    # 按年级分组并计算排名
    grades_classes = {}
    for data in class_scores_data.values():
        grade = data["grade"]
        if grade not in grades_classes:
            grades_classes[grade] = []
        grades_classes[grade].append(data)

    for grade, classes in grades_classes.items():
        classes.sort(key=lambda x: x["total_score"], reverse=True)
        for rank, class_data in enumerate(classes, 1):
            class_score = ClassScore(
                academic_year_id=academic_year_id,
                class_team_id=class_data["class_team_id"],
                grade=class_data["grade"],
                class_name=class_data["class_name"],
                total_score=class_data["total_score"],
                rank_in_grade=rank,
            )
            db.add(class_score)

    db.commit()

    # 6. 返回统计摘要
    total_details = db.query(ScoreDetail).filter(
        ScoreDetail.academic_year_id == academic_year_id
    ).count()
    total_athletes = db.query(AthleteScore).filter(
        AthleteScore.academic_year_id == academic_year_id
    ).count()
    total_classes = db.query(ClassScore).filter(
        ClassScore.academic_year_id == academic_year_id
    ).count()

    return {
        "total_details": total_details,
        "total_athletes": total_athletes,
        "total_classes": total_classes,
        "calculated_at": datetime.now(),
    }
