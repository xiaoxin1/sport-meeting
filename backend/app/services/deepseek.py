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
    import logging
    logger = logging.getLogger("deepseek")

    api_key = get_api_key(db)
    if not api_key:
        raise RuntimeError("未配置 DeepSeek API Key，请在系统设置中填写后再使用 AI 生成")
    base = get_base_url(db).rstrip("/")

    try:
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
                "max_tokens": 8192,
            },
            timeout=180,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text
        raise RuntimeError(f"DeepSeek API 调用失败：{error_detail}")
    except Exception as e:
        raise RuntimeError(f"网络请求失败：{e}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    finish_reason = data["choices"][0].get("finish_reason")

    logger.info(f"DeepSeek 响应长度: {len(content)} 字符, finish_reason: {finish_reason}")

    # 检查是否被截断
    if finish_reason == "length":
        raise RuntimeError(
            f"AI 返回内容超出长度限制（{len(content)} 字符）。"
            "当前赛次数量较多，建议：\n"
            "1. 减少优化需求的文字描述\n"
            "2. 或联系管理员调整系统配置"
        )

    # 尝试解析JSON
    try:
        return json.loads(content)
    except json.JSONDecodeError as e:
        # 记录前500和后500字符用于调试
        logger.error(f"JSON解析失败。前500字符: {content[:500]}")
        logger.error(f"后500字符: {content[-500:]}")
        raise RuntimeError(
            f"AI 返回的内容不是有效的 JSON 格式。\n"
            f"解析错误：{e}\n"
            f"返回内容长度：{len(content)} 字符\n"
            f"finish_reason: {finish_reason}\n"
            f"这通常是因为AI输出被截断，请尝试简化优化需求"
        )
