"""秩序册生成 API"""
import random
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.registration import ClassTeam, Athlete
from app.models.event import Event
from app.models.schedule import ScheduleEntry, ScheduleGroup, ScheduleLane
from app.models.record import Record
from app.api.deps import get_active_year, require_admin

router = APIRouter(
    prefix="/program",
    tags=["program"],
    dependencies=[Depends(require_admin)],
)


def _infer_unit(event_name: str) -> str:
    """根据项目名称推断成绩单位：秒 / 米 / 个"""
    if any(x in event_name for x in ["跳远", "跳高", "实心球", "掷垒球"]):
        return "米"
    if any(x in event_name for x in ["拍皮球", "沙包"]):
        return "个"
    return "秒"


def _generate_result_value(event_name: str, gender: str, unit: str) -> float:
    """为某项目生成一个合理的随机成绩数值"""
    if unit == "秒":
        if "60M" in event_name:
            return round(random.uniform(7.5, 9.5), 2)
        elif "100M*4" in event_name:
            return round(random.uniform(45, 55), 2)
        elif "100M*2" in event_name:
            return round(random.uniform(25, 35), 2)
        elif "100M" in event_name:
            return round(random.uniform(11.5, 14.5), 2)
        elif "1000M" in event_name:
            return round(random.uniform(180, 240), 2)
        elif "800M" in event_name:
            return round(random.uniform(150, 210), 2)
        elif "30M" in event_name:
            return round(random.uniform(20, 30), 2)
        else:
            return round(random.uniform(30, 60), 2)
    elif unit == "米":
        if "跳远" in event_name:
            return round(random.uniform(4.5, 6.5) if gender == "男" else random.uniform(3.5, 5.5), 2)
        elif "跳高" in event_name:
            return round(random.uniform(1.4, 1.8) if gender == "男" else random.uniform(1.2, 1.6), 2)
        elif "实心球" in event_name:
            return round(random.uniform(8, 12) if gender == "男" else random.uniform(6, 10), 2)
        elif "掷垒球" in event_name:
            return round(random.uniform(25, 45) if gender == "男" else random.uniform(20, 35), 2)
        return round(random.uniform(1, 10), 2)
    else:  # 个
        return float(random.randint(50, 100))


@router.get("/preview")
def get_program_preview(
    db: Session = Depends(get_db),
    year: int = Depends(get_active_year)
):
    """获取秩序册预览数据"""
    year_id = year.id

    result = {
        "team_stats": get_team_stats(db, year_id),
        "team_rosters": get_team_rosters(db, year_id),
        "schedule": get_schedule_summary(db, year_id),
        "grouping": get_event_grouping(db, year_id),
        "records": get_records_matrix(db),
    }

    return result


def get_team_stats(db: Session, year_id: int):
    """1. 参赛队统计"""
    from app.services.numbering import _grade_key, _class_key

    classes = (
        db.query(ClassTeam)
        .filter(ClassTeam.academic_year_id == year_id)
        .all()
    )
    classes.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))

    # 获取每个班级的号码范围
    teams = []
    grade_summary = {}

    for idx, cls in enumerate(classes, 1):
        # 获取该班级的运动员号码
        athletes = (
            db.query(Athlete)
            .filter(Athlete.class_team_id == cls.id)
            .order_by(Athlete.number)
            .all()
        )

        male_athletes = [a for a in athletes if a.gender == "男"]
        female_athletes = [a for a in athletes if a.gender == "女"]

        male_range = ""
        if male_athletes:
            male_nums = [a.number for a in male_athletes if a.number]
            if male_nums:
                male_range = f"{min(male_nums)}-{max(male_nums)}"

        female_range = ""
        if female_athletes:
            female_nums = [a.number for a in female_athletes if a.number]
            if female_nums:
                female_range = f"{min(female_nums)}-{max(female_nums)}"

        teams.append({
            "index": idx,
            "grade": cls.grade,
            "class_name": cls.class_name,
            "male_range": male_range,
            "female_range": female_range,
            "male_count": cls.male_count,
            "female_count": cls.female_count,
        })

        # 年级汇总
        if cls.grade not in grade_summary:
            grade_summary[cls.grade] = {"male": 0, "female": 0}
        grade_summary[cls.grade]["male"] += cls.male_count
        grade_summary[cls.grade]["female"] += cls.female_count

    return {
        "teams": teams,
        "grade_summary": grade_summary,
    }


def get_team_rosters(db: Session, year_id: int):
    """2. 代表队名单"""
    from app.services.numbering import _grade_key, _class_key

    classes = (
        db.query(ClassTeam)
        .filter(ClassTeam.academic_year_id == year_id)
        .all()
    )
    classes.sort(key=lambda c: (_grade_key(c.grade), _class_key(c.class_name)))

    rosters = []
    for idx, cls in enumerate(classes, 1):
        # 获取该班级的运动员
        athletes = (
            db.query(Athlete)
            .filter(Athlete.class_team_id == cls.id)
            .order_by(Athlete.gender.desc(), Athlete.number)
            .all()
        )

        male_athletes = [
            {"number": a.number, "name": a.name}
            for a in athletes if a.gender == "男"
        ]
        female_athletes = [
            {"number": a.number, "name": a.name}
            for a in athletes if a.gender == "女"
        ]

        rosters.append({
            "index": idx,
            "grade": cls.grade,
            "class_name": cls.class_name,
            "leader_name": cls.leader_name or "",
            "male_athletes": male_athletes,
            "female_athletes": female_athletes,
        })

    return rosters


def get_schedule_summary(db: Session, year_id: int):
    """3. 竞赛日程"""
    entries = (
        db.query(ScheduleEntry, Event)
        .join(Event, ScheduleEntry.event_id == Event.id)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(
            ScheduleEntry.day_index,
            ScheduleEntry.period,
            ScheduleEntry.order_no
        )
        .all()
    )

    # 按半天分组
    periods = {}
    for entry, event in entries:
        key = f"{entry.day_index}-{entry.period}"
        if key not in periods:
            periods[key] = {
                "day": entry.day_index,
                "period": entry.period,
                "events": []
            }

        # 计算参赛人数
        participant_count = 0
        from app.models.registration import AthleteEvent, ClassTeamEvent
        if event.is_team:
            participant_count = db.query(ClassTeamEvent).filter(ClassTeamEvent.event_id == event.id).count()
        else:
            participant_count = db.query(AthleteEvent).filter(AthleteEvent.event_id == event.id).count()

        periods[key]["events"].append({
            "index": len(periods[key]["events"]) + 1,
            "group_name": event.group_name,
            "gender": event.gender,
            "event_name": event.name,
            "round_type": entry.round_type,
            "participant_count": participant_count,
            "group_count": entry.group_count,
            "advance_count": entry.advance_count,
            "time": f"{entry.start_time or ''}-{entry.end_time or ''}".strip("-"),
        })

    return list(periods.values())


def get_event_grouping(db: Session, year_id: int):
    """4. 项目分组表"""
    entries = (
        db.query(ScheduleEntry, Event)
        .join(Event, ScheduleEntry.event_id == Event.id)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(
            ScheduleEntry.day_index,
            ScheduleEntry.period,
            ScheduleEntry.order_no
        )
        .all()
    )

    periods = {}
    for entry, event in entries:
        key = f"{entry.day_index}-{entry.period}"
        if key not in periods:
            periods[key] = {
                "day": entry.day_index,
                "period": entry.period,
                "events": []
            }

        # 获取该项目的详细分组信息
        from app.models.schedule import ScheduleGroup, ScheduleLane
        groups_data = (
            db.query(ScheduleGroup)
            .filter(ScheduleGroup.entry_id == entry.id)
            .order_by(ScheduleGroup.group_no)
            .all()
        )

        detailed_groups = []
        for group in groups_data:
            lanes_data = (
                db.query(ScheduleLane, Athlete, ClassTeam)
                .outerjoin(Athlete, ScheduleLane.athlete_id == Athlete.id)
                .outerjoin(ClassTeam, ScheduleLane.class_team_id == ClassTeam.id)
                .filter(ScheduleLane.group_id == group.id)
                .order_by(ScheduleLane.lane_no)
                .all()
            )

            lanes = []
            for lane, athlete, class_team in lanes_data:
                lane_data = {
                    "lane": lane.lane_no,
                }

                if event.is_team:
                    lane_data["class_name"] = f"{class_team.grade} {class_team.class_name}" if class_team else ""
                else:
                    lane_data["bib_number"] = athlete.number if athlete else ""
                    lane_data["athlete_name"] = athlete.name if athlete else ""
                    if athlete:
                        athlete_class = db.query(ClassTeam).filter(ClassTeam.id == athlete.class_team_id).first()
                        lane_data["class_name"] = f"{athlete_class.grade} {athlete_class.class_name}" if athlete_class else ""
                    else:
                        lane_data["class_name"] = ""

                lanes.append(lane_data)

            detailed_groups.append({
                "group_index": group.group_no,
                "lanes": lanes
            })

        # 计算参赛人数
        participant_count = 0
        from app.models.registration import AthleteEvent, ClassTeamEvent
        if event.is_team:
            participant_count = db.query(ClassTeamEvent).filter(ClassTeamEvent.event_id == event.id).count()
        else:
            participant_count = db.query(AthleteEvent).filter(AthleteEvent.event_id == event.id).count()

        periods[key]["events"].append({
            "index": len(periods[key]["events"]) + 1,
            "group_name": event.group_name,
            "gender": event.gender,
            "event_name": event.name,
            "round_type": entry.round_type,
            "is_team": event.is_team,
            "participant_count": participant_count,
            "group_count": entry.group_count,
            "advance_count": entry.advance_count,
            "time": f"{entry.start_time or ''}-{entry.end_time or ''}".strip("-"),
            "groups": detailed_groups,
        })

    return list(periods.values())


def get_records_matrix(db: Session):
    """5. 最高记录"""
    records = db.query(Record).order_by(Record.event_name, Record.group_name, Record.gender).all()

    # 构建矩阵：行是项目+性别，列是年级
    matrix = {}
    grades = set()

    for record in records:
        event_key = record.event_name
        if event_key not in matrix:
            matrix[event_key] = {}

        gender = record.gender
        if gender not in matrix[event_key]:
            matrix[event_key][gender] = {}

        grade = record.group_name
        grades.add(grade)

        matrix[event_key][gender][grade] = {
            "holder_name": record.holder_name or "",
            "result": record.historical_result or "",
        }

    # 年级列：固定包含 三年级 ~ 高三 的所有年级，从小到大排序；
    # 记录中出现的其它未知年级按规范顺序追加到末尾。
    from app.services.numbering import GRADE_ORDER, _grade_key

    fixed_grades = GRADE_ORDER[GRADE_ORDER.index("三年级"):]
    extra_grades = sorted(
        (g for g in grades if g not in fixed_grades), key=_grade_key
    )
    grades_list = fixed_grades + extra_grades
    rows = []

    for event_name, genders in matrix.items():
        for gender in ["男", "女"]:
            if gender in genders:
                row = {
                    "event_name": event_name,
                    "gender": gender,
                    "records": {}
                }
                for grade in grades_list:
                    row["records"][grade] = genders[gender].get(grade, {"holder_name": "", "result": ""})
                rows.append(row)

    return {
        "grades": grades_list,
        "rows": rows,
    }


@router.post("/generate-results")
def generate_results(
    db: Session = Depends(get_db),
    year=Depends(get_active_year)
):
    """【开发者工具】为所有预赛，以及不需要预赛的决赛生成随机成绩。

    生成规则：
    - 预赛(round_type=预赛)：全部生成成绩
    - 决赛(round_type=决赛)：仅当该项目没有对应预赛时才生成
    - 每个赛次内按成绩排名(径赛升序、田赛降序)
    """
    year_id = year.id

    # 获取所有日程赛次及其项目
    entries = (
        db.query(ScheduleEntry, Event)
        .join(Event, ScheduleEntry.event_id == Event.id)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .all()
    )

    if not entries:
        raise HTTPException(status_code=400, detail="尚未生成竞赛日程，无法生成成绩")

    # 统计每个项目有哪些赛次类型，判断决赛是否有预赛
    event_rounds: Dict[int, set] = {}
    for entry, event in entries:
        event_rounds.setdefault(event.id, set()).add(entry.round_type)

    results_count = 0

    for entry, event in entries:
        # 决赛且该项目存在预赛 → 跳过（决赛成绩应由预赛晋级后产生）
        if entry.round_type == "决赛" and "预赛" in event_rounds.get(event.id, set()):
            continue

        unit = _infer_unit(event.name)
        is_time_based = unit == "秒"  # 径赛：成绩越小越好

        # 收集该赛次下所有分道（有选手/班级的）
        lanes = (
            db.query(ScheduleLane)
            .join(ScheduleGroup, ScheduleLane.group_id == ScheduleGroup.id)
            .filter(ScheduleGroup.entry_id == entry.id)
            .all()
        )

        # 过滤出实际有归属的分道
        valid_lanes = [
            lane for lane in lanes
            if lane.athlete_id is not None or lane.class_team_id is not None
        ]

        if not valid_lanes:
            continue

        # 为每个分道生成成绩
        lane_results = []
        for lane in valid_lanes:
            value = _generate_result_value(event.name, event.gender, unit)
            lane.result = f"{value:.2f}" if unit != "个" else f"{int(value)}"
            lane_results.append((lane, value))
            results_count += 1

        # 排名：径赛升序(小的好)，田赛降序(大的好)
        lane_results.sort(key=lambda x: x[1], reverse=not is_time_based)
        for rank, (lane, _) in enumerate(lane_results, 1):
            lane.rank = rank

    db.commit()

    return {
        "message": "成绩生成成功",
        "results_count": results_count,
    }
