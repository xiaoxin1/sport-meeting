"""应用启动初始化：建表 + 播种管理员账号。

当前用 create_all 建表，满足快速迭代。后续引入 Alembic 做迁移时，
将建表职责交给迁移脚本，此处仅保留数据播种。
"""
import logging

from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password

# 确保所有模型被导入注册到 Base.metadata
import app.models  # noqa: F401
from app.models.user import User

logger = logging.getLogger("sfls.bootstrap")


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    _ensure_columns()
    _seed_admin()


def _ensure_columns() -> None:
    """create_all 不会给已存在的表补列。此处为旧库做最小增量迁移。"""
    with engine.begin() as conn:
        # 检查 events.venue
        exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :db AND table_name = 'events' "
                "AND column_name = 'venue'"
            ),
            {"db": settings.mysql_database},
        ).scalar()
        if not exists:
            conn.execute(
                text(
                    "ALTER TABLE events "
                    "ADD COLUMN venue VARCHAR(32) NOT NULL DEFAULT ''"
                )
            )
            logger.info("events 表已补充 venue 列")

        # 检查 class_teams.password（领队登录密码）
        exists = conn.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.columns "
                "WHERE table_schema = :db AND table_name = 'class_teams' "
                "AND column_name = 'password'"
            ),
            {"db": settings.mysql_database},
        ).scalar()
        if not exists:
            safe_pwd = settings.leader_default_password.replace("'", "''")
            conn.execute(
                text(
                    "ALTER TABLE class_teams "
                    f"ADD COLUMN password VARCHAR(64) NOT NULL DEFAULT '{safe_pwd}'"
                )
            )
            logger.info("class_teams 表已补充 password 列")

        # 清理 schedule_configs 已废弃的 AI 交互字段（模型已移除，旧库遗留则删除）
        for col in (
            "last_ai_request",
            "last_ai_response",
            "last_ai_report",
            "last_ai_mode",
            "last_ai_time",
        ):
            exists = conn.execute(
                text(
                    "SELECT COUNT(*) FROM information_schema.columns "
                    "WHERE table_schema = :db AND table_name = 'schedule_configs' "
                    "AND column_name = :col"
                ),
                {"db": settings.mysql_database, "col": col},
            ).scalar()
            if exists:
                conn.execute(text(f"ALTER TABLE schedule_configs DROP COLUMN {col}"))
                logger.info(f"schedule_configs 表已移除废弃列 {col}")


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
