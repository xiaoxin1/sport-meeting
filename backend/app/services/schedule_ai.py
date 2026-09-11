"""AI 优化：把当前日程 + 配置 + 追加消息送 DeepSeek，回填时间/顺序。

DeepSeek 只调整每个赛次的 day_index/period/order_no/start_time/end_time/venue，
不改动分组分道（分组由报名情况确定性生成）。返回的是 entry_id -> 调整字段。
"""
import json

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.schedule import ScheduleConfig, ScheduleEntry
from app.services.deepseek import chat_json

SYSTEM = (
    "你是学校运动会竞赛日程编排专家。你会收到强制规则、优化规则、"
    "追加要求，以及当前所有赛次的清单。请在满足强制规则的前提下，"
    "尽量满足优化规则与追加要求，重新编排每个赛次的：day_index(第几天)、"
    "period(上午/下午)、order_no(全局序号，从1开始且唯一)、"
    "start_time/end_time(HH:MM)、venue(场地)。"
    '只返回 JSON：{"entries":[{"id":1,"day_index":1,"period":"上午",'
    '"order_no":1,"start_time":"08:00","end_time":"08:30","venue":"径赛场"}]}。'
    "不要改动 id、不要新增或删除赛次。"
)


def _entries_payload(db: Session, year_id: int) -> list[dict]:
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )
    ev_cache: dict[int, Event] = {}
    out = []
    for e in entries:
        ev = ev_cache.get(e.event_id) or db.get(Event, e.event_id)
        ev_cache[e.event_id] = ev
        out.append(
            {
                "id": e.id,
                "event": ev.name,
                "group": ev.group_name,
                "gender": ev.gender,
                "type": "团队" if ev.is_team else "个人",
                "round": e.round_type,
                "group_count": e.group_count,
                "day_index": e.day_index,
                "period": e.period,
                "order_no": e.order_no,
                "start_time": e.start_time,
                "end_time": e.end_time,
                "venue": e.venue,
            }
        )
    return out


def optimize_schedule(db: Session, year_id: int, config: ScheduleConfig) -> None:
    history = json.loads(config.ai_history or "[]")
    extra = "\n".join(f"- {m}" for m in history) if history else "（无）"
    user = (
        f"赛程天数：{config.days} 天，径赛分道：{config.lanes} 道。\n\n"
        f"【强制规则】\n{config.hard_rules}\n\n"
        f"【优化规则】\n{config.soft_rules}\n\n"
        f"【追加要求】\n{extra}\n\n"
        f"【当前赛次清单】\n{json.dumps(_entries_payload(db, year_id), ensure_ascii=False)}"
    )
    result = chat_json(db, SYSTEM, user)
    updates = {item["id"]: item for item in result.get("entries", [])}
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .all()
    )
    for e in entries:
        u = updates.get(e.id)
        if not u:
            continue
        e.day_index = int(u.get("day_index", e.day_index))
        e.period = str(u.get("period", e.period))
        e.order_no = int(u.get("order_no", e.order_no))
        e.start_time = str(u.get("start_time", e.start_time))
        e.end_time = str(u.get("end_time", e.end_time))
        e.venue = str(u.get("venue", e.venue))
    db.flush()
