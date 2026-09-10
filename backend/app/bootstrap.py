"""应用启动初始化：建表 + 播种管理员账号。

当前用 create_all 建表，满足快速迭代。后续引入 Alembic 做迁移时，
将建表职责交给迁移脚本，此处仅保留数据播种。
"""
import logging

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password

# 确保所有模型被导入注册到 Base.metadata
import app.models  # noqa: F401
from app.models.user import User

logger = logging.getLogger("sfls.bootstrap")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _seed_admin()


def _seed_admin() -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == settings.admin_username).first()
        if existing is None:
            admin = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            )
            db.add(admin)
            db.commit()
            logger.info("已创建管理员账号: %s", settings.admin_username)
    finally:
        db.close()
