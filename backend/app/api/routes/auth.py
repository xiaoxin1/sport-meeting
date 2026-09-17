from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import Principal, get_current_principal
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models.academic_year import AcademicYear
from app.models.registration import ClassTeam
from app.models.user import User
from app.schemas.auth import LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])

_BAD_CRED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误"
)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    grade = (payload.grade or "").strip()
    class_name = (payload.class_name or "").strip()

    # 领队登录：填写了年级/班级 → 按当前学年匹配班级 + 领队姓名 + 密码
    if grade or class_name:
        if not (grade and class_name):
            raise HTTPException(status_code=400, detail="领队登录需同时填写年级和班级")
        year = db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()
        if year is None:
            raise HTTPException(status_code=400, detail="尚未设置当前学年")
        cls = (
            db.query(ClassTeam)
            .filter(
                ClassTeam.academic_year_id == year.id,
                ClassTeam.grade == grade,
                ClassTeam.class_name == class_name,
            )
            .first()
        )
        if cls is None or cls.leader_name != payload.username or cls.password != payload.password:
            raise _BAD_CRED
        token = create_access_token(f"leader:{cls.id}")
        return TokenResponse(
            access_token=token,
            username=cls.leader_name,
            role="leader",
            class_team_id=cls.id,
            grade=cls.grade,
            class_name=cls.class_name,
        )

    # 管理员登录
    user = db.query(User).filter(User.username == payload.username).first()
    if user is None or not verify_password(payload.password, user.password_hash):
        raise _BAD_CRED
    token = create_access_token(user.username)
    return TokenResponse(access_token=token, username=user.username, role="admin")


@router.get("/me")
def me(current: Principal = Depends(get_current_principal)):
    return {
        "username": current.username,
        "role": current.role,
        "class_team_id": current.class_team_id,
    }
