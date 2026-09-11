"""AI 优化：把当前日程 + 配置 + 追加消息一次性送 DeepSeek，回填时间/顺序。

DeepSeek 只调整每个赛次的 day_index/period/order_no/start_time/end_time/venue，
不改动分组分道（分组由报名情况确定性生成）。

为了让全部赛次能在 DeepSeek 单次输出上限（约 8192 tokens）内一次返回，
采用极度压缩的定长数组格式，避免分批导致的跨批次冲突（场地/时间/序号）。
"""
import json

from sqlalchemy.orm import Session

from app.models.event import Event
from app.models.schedule import ScheduleConfig, ScheduleEntry

from app.services.deepseek import chat_json

# 编码表：period 与 venue 都是有限枚举，用整数编码大幅压缩输出体积
PERIOD_CODES = {"上午": 0, "下午": 1}
PERIOD_DECODE = {0: "上午", 1: "下午"}
VENUE_CODES = {"径赛场": 0, "田赛区": 1}
VENUE_DECODE = {0: "径赛场", 1: "田赛区"}

SYSTEM = (
    "你是学校运动会竞赛日程编排专家。你会收到全部赛次的清单和优化要求，"
    "需要通盘考虑所有赛次，重新编排每个赛次的时间和场地，避免冲突。\n\n"
    "**输入格式说明**：\n"
    "每个赛次是一个数组 [id, day, period, order, start, end, venue, 描述]：\n"
    "- id: 赛次唯一编号（原样返回，不可改）\n"
    "- day: 第几天（整数，从1开始）\n"
    "- period: 时段，0=上午，1=下午\n"
    "- order: 全局顺序号（整数）\n"
    "- start/end: 起止时间，4位字符串如\"0800\"表示08:00\n"
    "- venue: 场地，0=径赛场，1=田赛区\n"
    "- 描述: 仅供你理解赛次内容，不需要返回\n\n"
    "**输出要求**：\n"
    "1. 只返回JSON对象，格式：{\"e\":[[id,day,period,order,start,end,venue],...]}\n"
    "2. 每个内层数组7个元素，顺序严格为 id,day,period,order,start,end,venue\n"
    "3. period 只能是0或1；venue 只能是0或1；start/end 是4位数字字符串\n"
    "4. 必须返回收到的全部赛次，一个都不能少，id 原样保留\n"
    "5. order 在全局范围内唯一且连续；同一场地同一时间不得重叠\n"
    "6. 不要输出任何解释文字，只输出JSON"
)


def _fmt_time(t: str) -> str:
    """把 'HH:MM' 压成 'HHMM'；空值给占位。"""
    return (t or "").replace(":", "").zfill(4)[:4] if t else "0000"


def _parse_time(s: str) -> str:
    """把 'HHMM' 解回 'HH:MM'。容错处理带冒号或异常输入。"""
    s = str(s).replace(":", "").strip()
    if len(s) < 3:
        return ""
    s = s.zfill(4)
    return f"{s[:2]}:{s[2:4]}"


def optimize_schedule(db: Session, year_id: int, config: ScheduleConfig) -> None:
    """单次调用AI优化全部赛次，保留全局视角以避免跨批次冲突。"""
    entries = (
        db.query(ScheduleEntry)
        .filter(ScheduleEntry.academic_year_id == year_id)
        .order_by(ScheduleEntry.order_no)
        .all()
    )

    if not entries:
        raise ValueError("没有可优化的赛次")

    history = json.loads(config.ai_history or "[]")
    extra = "\n".join(f"- {m}" for m in history) if history else "（无）"

    # 构建压缩后的赛次清单
    ev_cache: dict[int, Event] = {}
    compact = []
    for e in entries:
        ev = ev_cache.get(e.event_id) or db.get(Event, e.event_id)
        ev_cache[e.event_id] = ev
        desc = (
            f"{ev.group_name}{ev.gender}{ev.name}"
            f"{'团队' if ev.is_team else ''}{e.round_type}"
        )
        compact.append(
            [
                e.id,
                e.day_index,
                PERIOD_CODES.get(e.period, 0),
                e.order_no,
                _fmt_time(e.start_time),
                _fmt_time(e.end_time),
                VENUE_CODES.get(e.venue, 0),
                desc,
            ]
        )

    user = (
        f"赛程天数：{config.days} 天，径赛分道：{config.lanes} 道。\n\n"
        f"【强制规则】\n{config.hard_rules}\n\n"
        f"【优化规则】\n{config.soft_rules}\n\n"
        f"【追加要求】\n{extra}\n\n"
        f"【全部赛次清单（共{len(compact)}个，格式见system说明）】\n"
        f"{json.dumps(compact, ensure_ascii=False)}"
    )

    result = chat_json(db, SYSTEM, user)
    rows = result.get("e", [])
    if not rows:
        raise RuntimeError("AI 未返回任何赛次安排")

    # 解码回填
    updates: dict[int, dict] = {}
    for row in rows:
        if not isinstance(row, list) or len(row) < 7:
            continue
        try:
            eid = int(row[0])
        except (ValueError, TypeError):
            continue
        updates[eid] = {
            "day_index": int(row[1]),
            "period": PERIOD_DECODE.get(int(row[2]), "上午"),
            "order_no": int(row[3]),
            "start_time": _parse_time(row[4]),
            "end_time": _parse_time(row[5]),
            "venue": VENUE_DECODE.get(int(row[6]), "径赛场"),
        }

    for e in entries:
        u = updates.get(e.id)
        if not u:
            continue
        e.day_index = u["day_index"]
        e.period = u["period"]
        e.order_no = u["order_no"]
        e.start_time = u["start_time"] or e.start_time
        e.end_time = u["end_time"] or e.end_time
        e.venue = u["venue"]

    db.flush()
