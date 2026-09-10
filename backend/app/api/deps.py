"""API 通用依赖：当前登录用户校验。"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token
from app.models.academic_year import AcademicYear
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    username = decode_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="登录状态无效或已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在")
    return user


def get_active_year(db: Session = Depends(get_db)) -> AcademicYear:
    """返回当前激活学年；无则报错。所有按学年隔离的业务接口依赖此项。"""
    year = db.query(AcademicYear).filter(AcademicYear.is_active.is_(True)).first()
    if year is None:
        raise HTTPException(status_code=400, detail="尚未设置当前学年，请先在「学年设置」中创建并激活")
    return year
