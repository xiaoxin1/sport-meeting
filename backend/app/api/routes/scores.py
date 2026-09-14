"""分数统计相关路由。"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_active_year, get_current_user
from app.core.database import get_db
from app.models.academic_year import AcademicYear
from app.models.registration import Athlete, ClassTeam
from app.models.score import AthleteScore, ClassScore, ScoreDetail
from app.schemas.score import (
    AthleteScoreOut,
    CalculateSummary,
    ClassScoreOut,
    ScoreDetailOut,
)
from app.services.score_calculator import calculate_scores

router = APIRouter(
    prefix="/scores",
    tags=["scores"],
    dependencies=[Depends(get_current_user)],
)


@router.post("/calculate", response_model=CalculateSummary)
def calculate(
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """一键统计：重新计算当前学年的所有得分"""
    summary = calculate_scores(year.id, db)
    return summary


@router.get("/classes", response_model=list[ClassScoreOut])
def list_class_scores(
    grade: str | None = Query(None, description="按年级筛选"),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """获取班级得分列表"""
    query = db.query(ClassScore).filter(ClassScore.academic_year_id == year.id)

    if grade:
        query = query.filter(ClassScore.grade == grade)

    scores = query.order_by(ClassScore.grade, ClassScore.rank_in_grade).all()
    return scores


@router.get("/classes/{class_team_id}/details", response_model=list[ScoreDetailOut])
def get_class_details(
    class_team_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """获取某个班级的得分明细"""
    details = (
        db.query(ScoreDetail)
        .filter(
            ScoreDetail.academic_year_id == year.id,
            ScoreDetail.class_team_id == class_team_id,
        )
        .order_by(ScoreDetail.final_score.desc())
        .all()
    )

    # 转换为输出格式，添加运动员姓名
    result = []
    for detail in details:
        athlete_name = None
        if detail.athlete_id:
            athlete = db.get(Athlete, detail.athlete_id)
            if athlete:
                athlete_name = athlete.name

        result.append(
            ScoreDetailOut(
                id=detail.id,
                event_name=detail.event_name,
                group_name=detail.group_name,
                gender=detail.gender,
                is_team_event=detail.is_team_event,
                athlete_name=athlete_name,
                rank=detail.rank,
                result=detail.result,
                base_score=detail.base_score,
                is_record_broken=detail.is_record_broken,
                final_score=detail.final_score,
                created_at=detail.created_at,
            )
        )

    return result


@router.get("/athletes", response_model=list[AthleteScoreOut])
def list_athlete_scores(
    grade: str | None = Query(None, description="按年级筛选"),
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """获取个人得分列表"""
    query = db.query(AthleteScore).filter(AthleteScore.academic_year_id == year.id)

    if grade:
        query = query.filter(AthleteScore.grade == grade)

    scores = query.order_by(AthleteScore.grade, AthleteScore.rank_in_grade).all()

    # 添加班级名称
    result = []
    for score in scores:
        class_team = db.get(ClassTeam, score.class_team_id)
        result.append(
            AthleteScoreOut(
                id=score.id,
                athlete_id=score.athlete_id,
                class_team_id=score.class_team_id,
                grade=score.grade,
                class_name=class_team.class_name if class_team else "",
                athlete_name=score.athlete_name,
                total_score=score.total_score,
                rank_in_grade=score.rank_in_grade,
                updated_at=score.updated_at,
            )
        )

    return result


@router.get("/athletes/{athlete_id}/details", response_model=list[ScoreDetailOut])
def get_athlete_details(
    athlete_id: int,
    year: AcademicYear = Depends(get_active_year),
    db: Session = Depends(get_db),
):
    """获取某个运动员的得分明细"""
    details = (
        db.query(ScoreDetail)
        .filter(
            ScoreDetail.academic_year_id == year.id,
            ScoreDetail.athlete_id == athlete_id,
        )
        .order_by(ScoreDetail.final_score.desc())
        .all()
    )

    # 转换为输出格式
    athlete = db.get(Athlete, athlete_id)
    athlete_name = athlete.name if athlete else ""

    result = []
    for detail in details:
        result.append(
            ScoreDetailOut(
                id=detail.id,
                event_name=detail.event_name,
                group_name=detail.group_name,
                gender=detail.gender,
                is_team_event=detail.is_team_event,
                athlete_name=athlete_name,
                rank=detail.rank,
                result=detail.result,
                base_score=detail.base_score,
                is_record_broken=detail.is_record_broken,
                final_score=detail.final_score,
                created_at=detail.created_at,
            )
        )

    return result
