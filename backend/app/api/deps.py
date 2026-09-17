"""API 通用依赖：当前登录用户校验。"""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.academic_year import AcademicYear
from app.models.registration import ClassTeam
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_UNAUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="登录状态无效或已过期",
    headers={"WWW-Authenticate": "Bearer"},
)


@dataclass
class Principal:
    """当前登录主体：管理员或班级领队。"""

    role: str  # "admin" | "leader"
    username: str
    class_team_id: int | None = None

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    """仅管理员。领队 token 会被拒绝（403）。"""
    subject = decode_token(token)
    if subject is None or subject.startswith("leader:"):
        raise _UNAUTH if subject is None else HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问"
        )
    user = db.query(User).filter(User.username == subject).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_current_principal(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Principal:
    """管理员或领队均可。领队 subject 形如 'leader:{class_id}'。"""
    subject = decode_token(token)
    if subject is None:
        raise _UNAUTH
    if subject.startswith("leader:"):
        try:
            cid = int(subject.split(":", 1)[1])
        except (ValueError, IndexError):
            raise _UNAUTH
        cls = db.get(ClassTeam, cid)
        if cls is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="班级不存在或已删除")
        return Principal(role="leader", username=cls.leader_name, class_team_id=cid)
    user = db.query(User).filter(User.username == subject).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return Principal(role="admin", username=user.username)


def require_admin(principal: Principal = Depends(get_current_principal)) -> Principal:
    if not principal.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="仅管理员可访问")
    return principal


def get_active_year(db: Session = Depends(get_db)) -> AcademicYear:
    """返回当前激活学年；无则报错。所有按学年隔离的业务接口依赖此项。"""
    year = db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()
    if year is None:
        raise HTTPException(status_code=400, detail="尚未设置当前学年，请先在「学年设置」中创建并激活")
    return year
