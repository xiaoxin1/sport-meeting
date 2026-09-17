# 竞赛日程规则修改总结

## 修改日期
2026-09-17

## 修改内容

### 1. 规则2：同项目男女连续完成

**修改位置：**
- `app/services/schedule_gen.py` 第196行
- `app/services/schedule_rules.py` 第4行
- `app/services/schedule_ai.py` 第46、62行

**实现方式：**
- 在项目排序中添加 `e.gender` 作为排序键
- 排序优先级：`(event_priority(e), _grade_key(e.group_name), e.name, e.gender, e.is_team)`
- 确保同一项目名称下，男生和女生按性别分组并连续排列

### 2. 规则5：项目组间隔时间

**修改位置：**
- `app/services/schedule_gen.py` 第48-63行（新增 `EVENT_INTERVAL_MINUTES` 字典）
- `app/services/schedule_gen.py` 第330-333行（应用间隔时间）
- `app/services/schedule_rules.py` 第7行
- `app/services/schedule_ai.py` 第48、63行

**间隔时间配置：**
```python
EVENT_INTERVAL_MINUTES = {
    "60米": 2,
    "100米": 3,
    "800米": 5,
    "1000米": 5,
    "100*2米": 6,
    "100*4米": 4,
    "播种与收割": 15,
    "十人抓杆": 15,
    "垒球": 30,
    "跳高": 30,
    "跳远": 30,
    "袋鼠跳": 15,
    "师生同乐": 10,
    "侧向推实心球": 30,
}
```

**应用逻辑：**
- 在时间估算时，根据项目名称获取对应的间隔时间
- 计算赛次持续时间：`max(5, group_count * interval)`
- 尽可能满足间隔要求，时间不够时自动调整

### 3. 规则7：冲突解决策略优化

**修改位置：**
- `app/services/schedule_gen.py` 第402-470行（`_resolve_athlete_conflicts` 函数）
- `app/services/schedule_rules.py` 第9行
- `app/services/schedule_ai.py` 第49、67行

**解决策略：**
1. **策略1**：先尝试调整分组避免冲突（标记需要重新分组的情况）
2. **策略2**：不同场地可以并行进行
   - 检查冲突项目的场地
   - 如果所有项目在不同场地，则可以并行，不算冲突
3. **策略3**：调整项目顺序或移动到下一个时段
   - 只有在无法通过场地并行解决时才移动时段
   - 移动时优先选择临近的时段

**关键实现：**
```python
# 检查场地并行
venues = [db.get(Event, e.event_id).venue for e in slot_entries]
if len(set(venues)) == len(venues):
    # 所有项目在不同场地，可以并行，不算冲突
    continue
```

## AI服务更新

### AI优化服务 (`schedule_ai.py` - `ai_optimize_schedule`)
- ✅ 规则2：要求同项目男女连续完成
- ✅ 规则5：列出所有项目的组间隔时间要求
- ✅ 规则7：冲突时先调整分组，再调整顺序，最后移动时段
- ✅ 规则7：明确不同场地可以同时进行不同项目

### AI检查服务 (`schedule_ai.py` - `ai_check_schedule`)
- ✅ 检查维度2：同项目男女是否连续完成
- ✅ 检查维度3：验证组间隔时间要求
- ✅ 检查维度4：检查不同场地赛事是否可以并行
- ✅ 检查维度7：验证冲突解决策略是否正确

## 文件变更列表

1. `app/services/schedule_gen.py` - 核心生成逻辑
2. `app/services/schedule_rules.py` - 规则文本定义
3. `app/services/schedule_ai.py` - AI检查和优化提示

## 测试建议

1. 测试同项目男女连续性
2. 测试各项目的组间隔时间是否符合要求
3. 测试不同场地项目的并行处理
4. 测试冲突解决策略的优先级顺序
5. 验证AI检查能否正确识别违反规则的情况
6. 验证AI优化能否提出合理的优化建议
