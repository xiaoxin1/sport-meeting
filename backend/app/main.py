"""FastAPI 应用入口。"""
import logging
import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.api.router import api_router
from app.bootstrap import init_db
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sfls")

app = FastAPI(title="SFLS 运动会系统", version="0.1.0")

# 开发环境允许本地前端直连；生产走 nginx 同源反代，无需 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8686"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _wait_for_db(max_retries: int = 30, delay: float = 2.0) -> None:
    """容器启动时 MySQL 可能未就绪，重试等待。"""
    for attempt in range(1, max_retries + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("数据库连接成功")
            return
        except OperationalError:
            logger.warning("等待数据库就绪 (%d/%d)...", attempt, max_retries)
            time.sleep(delay)
    raise RuntimeError("数据库连接失败，超过最大重试次数")


@app.on_event("startup")
def on_startup() -> None:
    _wait_for_db()
    init_db()


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(api_router)
