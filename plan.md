# 分数统计功能实现方案

## 需求总结

### 两个统计维度
1. **班级维度统计**（最重要）
   - 按年级分组，每个年级内的班级单独排序
   - 班级总分 = 团队项目得分 + 本班所有学生得分之和
   - 点击详情可查看所有得分来源

2. **个人维度统计**
   - 按年级分组，每个年级内的学生单独排序
   - 点击详情可查看具体得分来源

### 得分规则
- 决赛前6名分别获得：7、5、4、3、2、1分
- 打破记录（超过历史记录）：得分双倍
- 只有决赛成绩计分，预赛不计分

### 功能要求
- 页面右上角有"一键统计"按钮
- 点击后重新收录当前学年的所有决赛成绩并计算分数

## 数据模型设计

### 1. `class_scores` 表（班级得分统计）
```python
class ClassScore(Base):
    __tablename__ = "class_scores"
    
    id: int (主键)
    academic_year_id: int (外键)
    class_team_id: int (外键)
    grade: str (冗余，方便按年级分组)
    class_name: str (冗余，方便显示)
    total_score: float (总分)
    rank_in_grade: int (年级内排名)
    updated_at: datetime
```

### 2. `athlete_scores` 表（个人得分统计）
```python
class AthleteScore(Base):
    __tablename__ = "athlete_scores"
    
    id: int (主键)
    academic_year_id: int (外键)
    athlete_id: int (外键)
    class_team_id: int (外键，冗余)
    grade: str (冗余)
    athlete_name: str (冗余)
    total_score: float (总分)
    rank_in_grade: int (年级内排名)
    updated_at: datetime
```

### 3. `score_details` 表（得分明细）
```python
class ScoreDetail(Base):
    __tablename__ = "score_details"
    
    id: int (主键)
    academic_year_id: int (外键)
    schedule_lane_id: int (外键，关联到具体成绩)
    
    # 项目信息
    event_name: str
    group_name: str (年级)
    gender: str
    is_team_event: bool
    
    # 归属信息
    class_team_id: int (班级，个人和团队都有)
    athlete_id: int | None (个人项目才有)
    
    # 得分信息
    rank: int (名次 1-6)
    result: str (成绩)
    base_score: float (基础分 7/5/4/3/2/1)
    is_record_broken: bool (是否打破记录)
    final_score: float (最终得分，打破记录则*2)
    
    created_at: datetime
```

## 计算逻辑

### 一键统计流程
1. 删除当前学年的所有统计数据（`class_scores`、`athlete_scores`、`score_details`）
2. 查询当前学年所有决赛成绩（`ScheduleEntry.round_type == "决赛"`）
3. 遍历每个 `ScheduleLane`：
   - 如果 `rank` 不在 [1,2,3,4,5,6]，跳过
   - 根据 `rank` 映射基础分：`{1:7, 2:5, 3:4, 4:3, 5:2, 6:1}`
   - 检查是否打破记录：
     - 查询对应的 `Record` 表（匹配 `event_name`、`group_name`、`gender`）
     - 比较 `lane.result` 与 `record.historical_result`
     - 使用 `_is_time_event()` 判断项目类型
     - 时间类：成绩 < 历史记录 = 打破
     - 距离类：成绩 > 历史记录 = 打破
   - 计算 `final_score = base_score * 2` if broken else `base_score`
   - 创建 `ScoreDetail` 记录
4. 汇总到 `athlete_scores`：
   - 按 `athlete_id` 分组，sum(`final_score`)
5. 汇总到 `class_scores`：
   - 按 `class_team_id` 分组，sum(`final_score`)（包含个人+团队）
6. 计算排名：
   - 按 `grade` 分组，按 `total_score` 降序排序，设置 `rank_in_grade`

### 判断打破记录的逻辑
复用 `record_update.py` 中的辅助函数：
- `_is_time_event(event_name)` - 判断是时间类还是距离类
- `_parse_time_result(result)` - 解析时间成绩为秒数
- `_parse_distance_result(result)` - 解析距离成绩为浮点数

比较逻辑：
- 如果 `historical_result` 为空，不算打破记录（因为没有历史基准）
- 时间类：`new_time < historical_time` = 打破
- 距离类：`new_distance > historical_distance` = 打破

## API 设计

### 后端路由
```python
# app/api/routes/scores.py

router = APIRouter(prefix="/scores", tags=["scores"])

# 一键统计
POST /api/scores/calculate
-> 触发计算，返回统计摘要

# 班级统计
GET /api/scores/classes
query: grade (可选，按年级筛选)
-> 返回班级得分列表（含排名）

# 班级得分详情
GET /api/scores/classes/{class_team_id}/details
-> 返回该班级的所有得分明细

# 个人统计
GET /api/scores/athletes
query: grade (可选)
-> 返回个人得分列表（含排名）

# 个人得分详情
GET /api/scores/athletes/{athlete_id}/details
-> 返回该学生的所有得分明细
```

### 前端页面
```
ScoresView.vue - 分数统计主页面
  - 顶部：一键统计按钮
  - 两个Tab：班级统计 / 个人统计
  - 班级统计Tab：
    - 年级筛选下拉框
    - 表格列：排名、班级、总分、操作（查看详情）
    - 详情弹窗：显示得分明细表格
  - 个人统计Tab：
    - 年级筛选下拉框
    - 表格列：排名、姓名、班级、总分、操作（查看详情）
    - 详情弹窗：显示得分明细表格
```

## 实现步骤

### 后端
1. 创建数据模型（`app/models/score.py`）
2. 创建数据库迁移文件
3. 创建 Pydantic schemas（`app/schemas/score.py`）
4. 创建计算服务（`app/services/score_calculator.py`）
5. 创建 API 路由（`app/api/routes/scores.py`）
6. 在 `app/api/router.py` 中注册路由

### 前端
1. 创建 API 客户端（`src/api/score.ts`）
2. 创建统计页面（`src/views/ScoresView.vue`）
3. 在 `src/router/index.ts` 中添加路由

### 部署
1. 执行数据库迁移
2. 重新构建后端容器
3. 重新构建前端容器

## 注意事项

1. **打破记录的判断**：只与 `historical_result` 比较，不与当年记录比较
2. **空值处理**：`historical_result` 为空时，不算打破记录
3. **团队项目**：`ScheduleLane.class_team_id` 有值，`athlete_id` 为空
4. **个人项目**：`ScheduleLane.athlete_id` 有值，需要查询运动员所属班级
5. **只统计决赛**：`ScheduleEntry.round_type == "决赛"`
6. **年级分组**：排名是在年级内部的，不是全校排名
