# 苏州外国语学校运动会系统 (SFLS Sports Meeting System)

面向校运动会全流程的管理系统：学年数据隔离、项目与报名管理、AI 竞赛日程编排、分组、记录、秩序册生成、成绩与分数统计。

## 技术栈

| 层 | 选型 |
| --- | --- |
| 前端 | Vue 3 + TypeScript + Vite + Element Plus + Pinia + Vue Router |
| 后端 | Python + FastAPI + SQLAlchemy 2.0 |
| 数据库 | MySQL 8.0（Docker 容器内置） |
| 部署 | Docker Compose 三服务；前端 Nginx 反代后端，对外单端口 |

## 架构总览

```
sport-meeting/
├── docker-compose.yml        # mysql + backend + frontend 三服务编排
├── .env.example              # 配置样例（复制为 .env 使用）
├── backend/                  # FastAPI 应用
│   ├── app/
│   │   ├── core/             # 配置、数据库、安全(JWT/密码)
│   │   ├── models/           # SQLAlchemy ORM 模型
│   │   ├── schemas/          # Pydantic 请求/响应模型
│   │   ├── api/
│   │   │   ├── deps.py       # 通用依赖(当前用户校验)
│   │   │   ├── router.py     # 路由聚合
│   │   │   └── routes/       # 各业务模块路由
│   │   ├── bootstrap.py      # 启动初始化(建表 + 播种管理员)
│   │   └── main.py           # 应用入口
│   └── Dockerfile
└── frontend/                 # Vue 应用
    ├── src/
    │   ├── api/              # 后端接口封装(axios)
    │   ├── stores/           # Pinia 状态(auth / 当前学年)
    │   ├── router/           # 路由 + 登录守卫
    │   ├── layouts/          # 主框架布局(侧边栏 + 顶栏)
    │   ├── views/            # 各页面
    │   ├── config/nav.ts     # 侧边栏导航配置
    │   └── styles/theme.css  # 设计系统(主题变量)
    ├── nginx.conf            # 静态托管 + /api 反代
    └── Dockerfile
```

### 设计原则
- **学年为数据根**：绝大多数业务数据归属某一学年，切换学年即切换全站数据上下文。
- **分层清晰**：后端 models / schemas / services / routes 分离；前端 api / stores / views 分离。新增功能模块时按既有结构扩展即可。
- **同源部署**：对外只暴露一个端口，前端 Nginx 将 `/api` 反代到后端，无跨域问题，贴近正式产品形态。
- **配置即环境变量**：数据库、管理员、JWT、DeepSeek 等全部通过 `.env` 注入。

## 快速开始

```bash
# 1. 准备配置
cp .env.example .env      # Windows: Copy-Item .env.example .env
# 按需修改 .env 中的密码、端口等

# 2. 一键启动
docker compose up -d --build

# 3. 访问
# 前端: http://localhost:8687   (端口由 .env 的 APP_PORT 决定)
# 默认管理员: admin / admin123
```

> **端口说明**：需求约定端口 8686，但本机 8686 已被其它容器占用，故默认改用 **8687**（见 `.env` 的 `APP_PORT`）。释放 8686 后可改回。

## 已实现功能

### 基础设施与骨架
- Docker Compose 三服务编排（MySQL / 后端 / 前端），MySQL 健康检查后后端才启动，后端启动时重试等待数据库就绪。
- 后端分层骨架、启动自动建表、自动播种唯一管理员账号。
- 前端整体框架：登录页、主布局（侧边栏导航 + 顶栏当前学年展示 + 退出登录）、统一设计系统主题、axios 拦截器（自动注入 token、401 自动跳登录）。

### 1. 登录
- 单管理员账号密码登录，JWT 鉴权。账号密码由 `.env` 配置，首次启动自动创建。
- 前端路由守卫：未登录自动跳转登录页；已登录访问登录页自动跳首页。

### 3. 学年设置
- 学年增删改查；名称唯一（格式如 `2026~2027`）。
- 可为每个学年设置运动会起止日期。
- 「设为当前」切换激活学年（同一时刻仅一个激活），顶栏实时展示当前学年。
- 删除学年有二次危险确认；删除激活学年后自动激活最近的一个。

### 4. 项目
- 维护本学年的比赛项目：项目名称、组别(年级)、性别(男/女/混合)、上限队伍、决赛队伍、团队/个人、项目介绍。
- **唯一键**：同一学年内「项目名称 + 组别 + 性别」唯一，重复创建返回明确错误。
- 列表支持按名称搜索、按组别筛选；组别下拉可自定义输入（filterable + allow-create）。
- 表格支持列头排序，默认按项目名称升序；各列等宽、内容超长自动换行。
- 所有项目按当前激活学年自动隔离（后端 `get_active_year` 依赖），切换学年即切换项目集。

## 变更记录

### v0.2.1 — 项目管理调整
- 移除「上限队伍」字段（前后端 + 数据库列 `max_teams` 一并删除，不做兼容）。
- 表格支持点击列头排序，默认按项目名称升序（中文按 localeCompare 排序）。
- 表格各列宽度统一（min-width 160），内容过长自动换行而非截断。

### v0.2.0 — 项目管理 (需求 4)
- 后端：新增 `Event` 模型（学年外键 + 唯一约束 `uq_event_identity`）、`event` schema（Gender 枚举、非负校验、决赛≤上限校验）、`events` 路由（增删改查，按激活学年隔离，唯一键冲突/跨学年访问处理）。
- 新增通用依赖 `get_active_year`：无激活学年时返回明确提示。
- 前端：新增 `EventView`（表格 + 搜索/筛选 + 新建/编辑对话框）、`events` API、`constants.ts`（性别/年级选项），启用侧边栏「项目」入口。
- 验证：Docker 实跑，创建/列表/更新/删除均通过；唯一键重复返回 400；决赛>上限返回 422；中文 UTF-8 存取往返正确。

### v0.1.0 — 架构搭建 + 登录 + 学年设置
- 搭建全栈架构与 Docker 编排，跑通「MySQL + 后端 + 前端 + 登录 + 学年设置」主线。
- 后端：`core`(config/database/security)、`models`(user/academic_year/setting)、`schemas`、`api`(auth/academic_years) 分层；启动建表与管理员播种。
- 前端：登录页、主布局、学年设置页（完整 CRUD + 激活切换）、设计系统主题、导航配置（其余 8 个功能 tab 已在侧边栏占位，标记「待开发」）。
- 验证：Docker 三服务启动成功；`/api/health` 正常；管理员登录返回 token、错误密码返回 401；未带 token 访问受保护接口返回 401；前端页面正常托管。
- 端口：因宿主机 8686 被占用，对外端口默认调整为 8687。

## 待开发功能（按需求编号）
2. ~~登录~~ ✅ ｜ 3. ~~学年设置~~ ✅ ｜ 4. ~~项目管理~~ ✅
5. 报名（Excel 导入 + 号码生成）｜ 6. 竞赛日程（DeepSeek AI 生成）｜ 7. 项目分组 ｜ 8. 最高记录 ｜ 9. 秩序册生成 ｜ 10. 成绩统计 ｜ 11. 分数统计

> 报名 Excel 模板列格式待用户提供样例后适配。
