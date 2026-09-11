"""DeepSeek 客户端。用于竞赛日程的智能生成 / 优化。

Key 优先从 AppSetting('deepseek_api_key') 读取，其次回退到环境变量配置，
便于运行时在系统里配置而无需改 .env。
"""
import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.setting import AppSetting


def _get_setting(db: Session, key: str) -> str | None:
    row = db.query(AppSetting).filter(AppSetting.key == key).first()
    return row.value if row and row.value else None


def get_api_key(db: Session) -> str:
    return _get_setting(db, "deepseek_api_key") or settings.deepseek_api_key


def get_base_url(db: Session) -> str:
    return _get_setting(db, "deepseek_base_url") or settings.deepseek_base_url


def chat_json(db: Session, system_prompt: str, user_prompt: str) -> dict:
    """调用 DeepSeek chat completions，要求返回 JSON。失败抛异常由上层处理。"""
    api_key = get_api_key(db)
    if not api_key:
        raise RuntimeError("未配置 DeepSeek API Key，请在系统设置中填写后再使用 AI 生成")
    base = get_base_url(db).rstrip("/")
    resp = httpx.post(
        f"{base}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": "deepseek-chat",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.3,
        },
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    return json.loads(content)
