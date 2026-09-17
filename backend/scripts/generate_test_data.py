"""
测试数据生成脚本
生成2026-2027学年的完整测试数据，包括项目、报名和最高记录
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import random
from sqlalchemy import text
from app.core.config import settings
from app.core.database import SessionLocal
from app.models.academic_year import AcademicYear
from app.models.event import Event
from app.models.registration import ClassTeam, Athlete, AthleteEvent, ClassTeamEvent
from app.models.record import Record

# 姓氏和名字库
SURNAMES = ["王", "李", "张", "刘", "陈", "杨", "黄", "赵", "周", "吴", "徐", "孙", "马", "朱", "胡", "郭", "何", "林", "高", "罗"]
MALE_NAMES = ["浩", "宇", "轩", "杰", "涛", "明", "强", "磊", "军", "勇", "峰", "超", "波", "辉", "刚", "鹏", "伟", "凯", "博", "文"]
FEMALE_NAMES = ["芳", "娜", "秀", "英", "敏", "静", "丽", "强", "洁", "华", "慧", "巧", "美", "娟", "婷", "玲", "梅", "琳", "素", "云"]

def generate_name(gender: str) -> str:
    """生成随机姓名"""
    surname = random.choice(SURNAMES)
    if gender == "男":
        name = random.choice(MALE_NAMES) + random.choice(MALE_NAMES)
    else:
        name = random.choice(FEMALE_NAMES) + random.choice(FEMALE_NAMES)
    return surname + name

# 项目配置
EVENTS_CONFIG = {
    "二年级": [
        {"name": "30M迎面接力", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "拍皮球", "is_team": True, "gender": "混合", "unit": "个"},
        {"name": "沙包投准", "is_team": True, "gender": "混合", "unit": "个"},
        {"name": "夹球接力", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "播种与收割", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "袋鼠跳", "is_team": True, "gender": "混合", "unit": "秒"},
    ],
    "三年级": [
        {"name": "60M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "60M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M*2", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M*2", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "跳远", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳远", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "播种与收割", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "袋鼠跳", "is_team": True, "gender": "混合", "unit": "秒"},
    ],
    "四年级": [
        {"name": "60M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "60M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M*2", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M*2", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "跳远", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳远", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "播种与收割", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "袋鼠跳", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "十人抓杆", "is_team": True, "gender": "混合", "unit": "秒"},
    ],
    "五年级": [
        {"name": "60M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "60M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M*4", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M*4", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "800M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "800M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "跳远", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳远", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "跳高", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳高", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "播种与收割", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "袋鼠跳", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "十人抓杆", "is_team": True, "gender": "混合", "unit": "秒"},
    ],
    "六年级": [
        {"name": "60M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "60M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "100M*4", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "100M*4", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "800M", "is_team": False, "gender": "男", "unit": "秒"},
        {"name": "800M", "is_team": False, "gender": "女", "unit": "秒"},
        {"name": "跳远", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳远", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "跳高", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "跳高", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "男", "unit": "米"},
        {"name": "掷垒球", "is_team": False, "gender": "女", "unit": "米"},
        {"name": "播种与收割", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "袋鼠跳", "is_team": True, "gender": "混合", "unit": "秒"},
        {"name": "十人抓杆", "is_team": True, "gender": "混合", "unit": "秒"},
    ],
}

# 初中和高中项目相同
MIDDLE_HIGH_EVENTS = [
    {"name": "100M", "is_team": False, "gender": "男", "unit": "秒"},
    {"name": "100M", "is_team": False, "gender": "女", "unit": "秒"},
    {"name": "1000M", "is_team": False, "gender": "男", "unit": "秒"},
    {"name": "800M", "is_team": False, "gender": "女", "unit": "秒"},
    {"name": "跳远", "is_team": False, "gender": "男", "unit": "米"},
    {"name": "跳远", "is_team": False, "gender": "女", "unit": "米"},
    {"name": "跳高", "is_team": False, "gender": "男", "unit": "米"},
    {"name": "跳高", "is_team": False, "gender": "女", "unit": "米"},
    {"name": "实心球", "is_team": False, "gender": "男", "unit": "米"},
    {"name": "实心球", "is_team": False, "gender": "女", "unit": "米"},
    {"name": "地龙舟", "is_team": True, "gender": "混合", "unit": "秒"},
    {"name": "高山流水", "is_team": True, "gender": "混合", "unit": "秒"},
    {"name": "十人抓杆", "is_team": True, "gender": "混合", "unit": "秒"},
]

for grade in ["初一", "初二", "初三", "高一", "高二", "高三"]:
    EVENTS_CONFIG[grade] = MIDDLE_HIGH_EVENTS.copy()

# 班级配置
CLASSES = {}
for grade in ["二年级", "三年级", "四年级", "五年级", "六年级"]:
    CLASSES[grade] = [f"{i}班" for i in range(1, 11)]
for grade in ["初一", "初二", "初三", "高一", "高二", "高三"]:
    CLASSES[grade] = [f"{i}班" for i in range(1, 9)]

# 每组决赛队伍/人数（每组容量）。键匹配项目名称，未列出的项目按全局 lanes 分组。
EVENT_GROUP_SIZE = {
    "60M": 6,
    "100M": 6,
    "100M*2": 6,
    "100M*4": 6,
    "800M": 50,
    "1000M": 50,
    "播种与收割": 50,
    "十人抓杆": 50,
    "掷垒球": 50,   # 垒球
    "实心球": 50,   # 侧向推实心球
    "跳高": 50,
    "跳远": 50,
    "袋鼠跳": 50,
    "师生同乐": 50,
}


def infer_group_size(config: dict) -> int:
    """按项目名称返回每组容量；未配置返回 0（生成日程时回退到全局 lanes）。"""
    return EVENT_GROUP_SIZE.get(config["name"], 0)


def infer_venue(config: dict) -> str:
    """按项目类型推断场地：跑道 / 跳高场 / 跳远场 / 操场（对应前端 VENUES）。

    规则：所有径赛(含 M 距离项目、接力)→ 跑道；跳高 → 跳高场；
    跳远 → 跳远场；其余(投掷、趣味团队等)→ 操场。
    """
    name = config["name"]
    if "跳高" in name:
        return "跳高场"
    if "跳远" in name:
        return "跳远场"
    # 径赛：含 M(米)距离项目，以及各类跑步接力
    if "M" in name.upper() or "接力" in name:
        return "跑道"
    # 其余：投掷、趣味团队项目等
    return "操场"


def generate_historical_result(event_name: str, gender: str, unit: str) -> str:
    """生成历史记录成绩"""
    if unit == "秒":
        if "60M" in event_name:
            return f"{random.uniform(7.5, 9.5):.2f}"
        elif "100M*4" in event_name:
            return f"{random.uniform(45, 55):.2f}"
        elif "100M*2" in event_name:
            return f"{random.uniform(25, 35):.2f}"
        elif "100M" in event_name:
            return f"{random.uniform(11.5, 14.5):.2f}"
        elif "1000M" in event_name:
            return f"{random.uniform(180, 240):.2f}"
        elif "800M" in event_name:
            return f"{random.uniform(150, 210):.2f}"
        elif "30M" in event_name:
            return f"{random.uniform(20, 30):.2f}"
        else:
            return f"{random.uniform(30, 60):.2f}"
    elif unit == "米":
        if "跳远" in event_name:
            if gender == "男":
                return f"{random.uniform(4.5, 6.5):.2f}"
            else:
                return f"{random.uniform(3.5, 5.5):.2f}"
        elif "跳高" in event_name:
            if gender == "男":
                return f"{random.uniform(1.4, 1.8):.2f}"
            else:
                return f"{random.uniform(1.2, 1.6):.2f}"
        elif "实心球" in event_name:
            if gender == "男":
                return f"{random.uniform(8, 12):.2f}"
            else:
                return f"{random.uniform(6, 10):.2f}"
        elif "掷垒球" in event_name:
            if gender == "男":
                return f"{random.uniform(25, 45):.2f}"
            else:
                return f"{random.uniform(20, 35):.2f}"
    elif unit == "个":
        return f"{random.randint(50, 100)}"
    return "0"

def clear_all_data(db):
    """清除所有测试数据"""
    print("清除现有测试数据...")
    db.execute(text("DELETE FROM athlete_events"))
    db.execute(text("DELETE FROM class_team_events"))
    db.execute(text("DELETE FROM athletes"))
    db.execute(text("DELETE FROM class_teams"))
    db.execute(text("DELETE FROM records"))
    db.execute(text("DELETE FROM events"))
    db.execute(text("DELETE FROM academic_years"))
    db.commit()
    print("数据清除完成")

def create_academic_year(db):
    """创建学年"""
    print("创建2026-2027学年...")
    year = AcademicYear(name="2026-2027", is_active=True)
    db.add(year)
    db.commit()
    db.refresh(year)
    print(f"学年创建完成，ID: {year.id}")
    return year

def create_events(db, year_id: int):
    """创建所有项目"""
    print("创建项目...")
    events = []
    for grade, event_configs in EVENTS_CONFIG.items():
        for config in event_configs:
            event = Event(
                academic_year_id=year_id,
                name=config["name"],
                group_name=grade,
                gender=config["gender"],
                venue=infer_venue(config),
                is_team=config["is_team"],
                final_teams=infer_group_size(config)
            )
            db.add(event)
            events.append((grade, config))
    db.commit()
    print(f"创建了 {len(events)} 个项目")
    return events

def create_registrations(db, year_id: int):
    """创建报名数据"""
    print("创建报名数据...")

    events = db.query(Event).filter_by(academic_year_id=year_id).all()
    events_by_grade = {}
    for event in events:
        if event.group_name not in events_by_grade:
            events_by_grade[event.group_name] = []
        events_by_grade[event.group_name].append(event)

    class_team_count = 0
    athlete_count = 0
    registration_count = 0

    for grade, classes in CLASSES.items():
        for class_name in classes:
            class_team = ClassTeam(
                academic_year_id=year_id,
                grade=grade,
                class_name=class_name,
                leader_name=generate_name(random.choice(["男", "女"])),
                password=settings.leader_default_password,
                male_count=0,
                female_count=0
            )
            db.add(class_team)
            db.flush()
            class_team_count += 1

            male_count = random.randint(8, 10)
            female_count = random.randint(8, 10)

            class_team.male_count = male_count
            class_team.female_count = female_count

            grade_events = events_by_grade.get(grade, [])
            individual_events_male = [e for e in grade_events if not e.is_team and e.gender == "男"]
            individual_events_female = [e for e in grade_events if not e.is_team and e.gender == "女"]
            team_events = [e for e in grade_events if e.is_team]

            # 每班同一项目最多 2 人报名：按 event.id 统计已报人数
            MAX_PER_EVENT = 2
            event_reg_count = {}

            def register_athlete(gender: str, candidate_events):
                """为一名运动员选 1~2 个项目，遵守每班每项目≤2人的限制。"""
                nonlocal athlete_count, registration_count
                student_name = generate_name(gender)
                athlete = Athlete(
                    class_team_id=class_team.id,
                    name=student_name,
                    gender=gender,
                    number=None
                )
                db.add(athlete)
                db.flush()
                athlete_count += 1

                # 只在未报满的项目里选
                available = [e for e in candidate_events
                             if event_reg_count.get(e.id, 0) < MAX_PER_EVENT]
                if not available:
                    return
                num_events = random.randint(1, 2)
                selected_events = random.sample(available, min(num_events, len(available)))
                for event in selected_events:
                    athlete_event = AthleteEvent(
                        athlete_id=athlete.id,
                        event_id=event.id
                    )
                    db.add(athlete_event)
                    event_reg_count[event.id] = event_reg_count.get(event.id, 0) + 1
                    registration_count += 1

            for i in range(male_count):
                register_athlete("男", individual_events_male)

            for i in range(female_count):
                register_athlete("女", individual_events_female)

            if team_events:
                num_team_events = random.randint(2, min(3, len(team_events)))
                selected_team_events = random.sample(team_events, num_team_events)

                for event in selected_team_events:
                    class_team_event = ClassTeamEvent(
                        class_team_id=class_team.id,
                        event_id=event.id
                    )
                    db.add(class_team_event)
                    registration_count += 1

    db.commit()
    print(f"创建了 {class_team_count} 个班级")
    print(f"创建了 {athlete_count} 名运动员")
    print(f"创建了 {registration_count} 条报名记录")

def create_records(db, year_id: int):
    """创建最高记录"""
    print("创建最高记录...")

    events = db.query(Event).filter_by(academic_year_id=year_id).all()

    for event in events:
        historical_result = generate_historical_result(event.name, event.gender, "秒" if event.name.endswith("M") or "龙舟" in event.name or "流水" in event.name else "米" if any(x in event.name for x in ["跳", "球"]) else "个")
        holder_name = generate_name(event.gender if event.gender != "混合" else random.choice(["男", "女"]))

        record = Record(
            academic_year_id=year_id,
            event_name=event.name,
            group_name=event.group_name,
            gender=event.gender,
            sort_order=0,
            historical_result=historical_result,
            holder_name=holder_name,
            result="",
            current_holder_name=""
        )
        db.add(record)

    db.commit()
    print(f"创建了 {len(events)} 条最高记录")

def main():
    """主函数"""
    print("=" * 50)
    print("开始生成测试数据")
    print("=" * 50)

    db = SessionLocal()

    try:
        clear_all_data(db)
        year = create_academic_year(db)
        create_events(db, year.id)
        create_registrations(db, year.id)
        create_records(db, year.id)

        print("=" * 50)
        print("测试数据生成完成！")
        print("=" * 50)

    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
