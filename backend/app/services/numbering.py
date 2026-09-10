"""号码生成。

规则：号码从 301 开始，班级按 年级 + 班级 顺序排列，每个班占
连续的 10（男）+ 10（女）= 20 个号码。班内男生依次占前 10 个，
女生依次占后 10 个；没人的号码槽位留白（不分配）。
"""
from sqlalchemy.orm import Session

from app.models.registration import Athlete, ClassTeam

START_NUMBER = 301
SLOTS_PER_GENDER = 10

# 年级规范排序：小学 -> 初中 -> 高中
GRADE_ORDER = [
    "一年级", "二年级", "三年级", "四年级", "五年级", "六年级",
    "初一", "初二", "初三", "高一", "高二", "高三",
]


def _grade_key(grade: str) -> tuple[int, str]:
    try:
        return (GRADE_ORDER.index(grade), "")
    except ValueError:
        # 未知年级排到最后，按名称排
        return (len(GRADE_ORDER), grade)


def generate_numbers(db: Session, academic_year_id: int) -> int:
    """为指定学年的所有班级重新生成号码。返回已分配号码的学生数。"""
    classes = (
        db.query(ClassTeam)
        .filter(ClassTeam.academic_year_id == academic_year_id)
        .all()
    )
    classes.sort(key=lambda c: (_grade_key(c.grade), c.class_name))

    assigned = 0
    cursor = START_NUMBER
    for cls in classes:
        base = cursor  # 该班号码段起点
        males = [a for a in cls.athletes if a.gender == "男"]
        females = [a for a in cls.athletes if a.gender == "女"]
        # 班内保持稳定顺序（按创建先后 / id）
        males.sort(key=lambda a: a.id)
        females.sort(key=lambda a: a.id)

        # 先清空该班所有学生号码
        for a in cls.athletes:
            a.number = None

        for idx, a in enumerate(males[:SLOTS_PER_GENDER]):
            a.number = base + idx
            assigned += 1
        for idx, a in enumerate(females[:SLOTS_PER_GENDER]):
            a.number = base + SLOTS_PER_GENDER + idx
            assigned += 1

        # 每班固定推进 20 个号码槽位（无论是否占满）
        cursor = base + 2 * SLOTS_PER_GENDER

    db.commit()
    return assigned
