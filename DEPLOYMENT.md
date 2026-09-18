# 离线部署与运维文档

面向**离线空服务器**（仅装了 Docker，无法访问外网）的部署说明，以及日常运维的三种重启方式。

## 目录

- [架构与前提](#架构与前提)
- [一、离线部署（首次上线）](#一离线部署首次上线)
- [二、运维：三种重启方式](#二运维三种重启方式)
  - [2.1 纯重启（不动数据、不重构）](#21-纯重启不动数据不重构)
  - [2.2 重新 build 前后端后重启](#22-重新-build-前后端后重启)
  - [2.3 清除数据后重启（清库）](#23-清除数据后重启清库)
- [三、数据备份与恢复](#三数据备份与恢复)
- [四、常见问题](#四常见问题)

## 架构与前提

三个容器由 `docker-compose.yml` 编排，对外只暴露一个端口（默认 `8687`，见 `.env` 的 `APP_PORT`）：

| 服务 | 镜像来源 | 说明 |
| --- | --- | --- |
| `mysql` | `mysql:8.0`（官方镜像） | 数据存于命名卷 `sport-meeting_mysql-data`，容器重建不丢 |
| `backend` | 由 `backend/Dockerfile` 构建 → `sport-meeting-backend` | FastAPI，启动时自动建表 + 播种管理员 |
| `frontend` | 由 `frontend/Dockerfile` 构建 → `sport-meeting-frontend` | Nginx 托管静态页 + 反代 `/api` 到 backend |

**关键点（离线的核心难题）**：`backend` / `frontend` 的 Dockerfile 在构建时要联网拉取基础镜像（python、node、nginx）并安装 pip / npm 依赖。空服务器没有外网，**无法在服务器上 `--build`**。因此必须：在一台联网机器上先构建镜像 → `docker save` 导出为 tar → 拷到服务器 → `docker load` 载入 → 直接启动（不带 `--build`）。

**服务器前提**：已安装 Docker Engine 与 Docker Compose 插件（`docker compose version` 能正常输出）。若服务器连 Docker 都没有，需另行离线安装 Docker，超出本文范围。

## 一、离线部署（首次上线）

整个流程分两段：**联网机器打包** → **离线服务器载入启动**。

### 🚀 快速打包（推荐）

项目根目录提供了一键打包脚本，自动完成镜像构建和文件打包：

```bash
# Linux/Mac（推荐，UTF-8 原生）
bash deploy-package.sh

# Windows PowerShell（已修复编码问题）
.\deploy-package.ps1
```

> **注意**：Windows 脚本使用英文输出以避免 PowerShell 编码问题，但生成的 `README.txt` 使用 UTF-8 编码，在 Linux 服务器上显示正常。

执行后会在 `deploy-package/` 目录生成：
- `sfls-images.tar` — Docker 镜像（~500MB-1GB）
- `sfls-runtime.tar.gz` — 运行配置文件（仅 3 个文件：`docker-compose.yml` + `.env.example` + `DEPLOYMENT.md`，<10KB）
- `README.txt` — 部署说明（UTF-8 编码）

**把整个 `deploy-package/` 目录拷贝到服务器即可。**

---

### 📦 手动打包（详细步骤）

如需了解打包原理或自定义流程，参考以下手动步骤。

### 阶段 A：在联网机器上打包（构建 + 导出）

> 在一台能上网、且**架构与服务器一致**（都为 x86_64 / amd64）的机器上操作。若联网机器是 Mac M 系列(arm64)，构建时须加 `--platform linux/amd64`，否则镜像在服务器上跑不起来。

```bash
# 1. 拿到源码，进入项目根目录
cd sport-meeting

# 2. 构建三个镜像（mysql 会被一起拉到本地）
docker compose build                 # 构建 backend、frontend
docker compose pull mysql            # 拉取 mysql:8.0 官方镜像

# 3. 确认镜像名（默认以目录名 sport-meeting 为前缀）
docker images | grep -E "sport-meeting|mysql"
#   sport-meeting-backend    latest
#   sport-meeting-frontend   latest
#   mysql                    8.0

# 4. 导出镜像
docker save -o sfls-images.tar \
  sport-meeting-backend:latest \
  sport-meeting-frontend:latest \
  mysql:8.0

# 5. 打包最小运行文件（仅需 3 个文件）
tar -czf sfls-runtime.tar.gz \
  docker-compose.yml \
  .env.example \
  DEPLOYMENT.md
```

> **为什么需要 docker-compose.yml？**
> 
> `docker-compose.yml` 是**容器编排配置**，不是容器内的程序。服务器上执行 `docker compose up` 时，Docker 先读取这个文件才知道要启动哪些容器、它们如何连接、用什么镜像。镜像里只包含程序代码，无法包含自己的启动配置。
> 
> 好在这个文件很小（<10KB），只需拷贝 3 个文件：`docker-compose.yml`（编排配置） + `.env.example`（配置模板） + `DEPLOYMENT.md`（运维文档）。

> **镜像名说明**：Compose 用「项目名-服务名」命名构建出的镜像，项目名默认取根目录名（此处 `sport-meeting`）。**服务器端的项目目录名必须也是 `sport-meeting`**，否则启动时 Compose 找不到对应镜像会尝试重建（离线会失败）。如目录名无法保持一致，见[四、常见问题](#四常见问题)的固定 image 名方案。

打包完成后得到两个文件：
1. `sfls-images.tar` — 镜像文件（~500MB-1GB）
2. `sfls-runtime.tar.gz` — 运行配置文件（<10KB）

用 U 盘 / scp / 内网文件服务把这两个文件送到服务器。

### 阶段 B：在离线服务器上载入并启动

```bash
# 1. 创建工作目录（目录名必须是 sport-meeting）
mkdir sport-meeting
cd sport-meeting

# 2. 解压运行文件
tar -xzf /path/to/sfls-runtime.tar.gz
# 得到 3 个文件：docker-compose.yml、.env.example、DEPLOYMENT.md

# 3. 载入镜像
docker load -i /path/to/sfls-images.tar
docker images | grep -E "sport-meeting|mysql"   # 核对三个镜像都在

# 4. 准备配置文件
cp .env.example .env
# 用编辑器改 .env：至少改这些关键配置
#   MYSQL_ROOT_PASSWORD=<强密码>
#   MYSQL_PASSWORD=<强密码>
#   JWT_SECRET=<长随机字符串>
#   ADMIN_PASSWORD=<管理员密码>
#   APP_PORT=8687  (确认端口未被占用)
#
# 离线环境 DEEPSEEK_API_KEY 可不填，日程「AI优化」不可用，
# 其余功能（规则生成、手动编辑、成绩录入等）全部正常。

# 5. 启动（关键：--no-build，绝不触发联网构建）
docker compose up -d --no-build

# 6. 查看状态与日志
docker compose ps
docker compose logs -f backend      # 看到 uvicorn 启动、建表完成即 OK，Ctrl+C 退出
```

启动顺序由 Compose 保证：mysql 健康后才起 backend，backend 起来后才起 frontend。首次启动 backend 的 `bootstrap` 会**自动建表并播种管理员账号**，无需手动初始化数据库。

### 验证

```bash
# 浏览器访问（APP_PORT 默认 8687）
http://<服务器IP>:8687
# 默认管理员：admin / <你在 .env 里设的 ADMIN_PASSWORD>
```

登录成功即部署完成。

## 二、运维：三种重启方式

以下命令都在服务器的项目根目录（`sport-meeting/`）执行。

### 2.1 纯重启（不动数据、不重构）

代码和镜像都没变，只想重启进程（如改了 `.env`、机器重启后、服务卡住）。数据保存在命名卷中，以下任何一种都**不会丢数据**。

**方式一：仅重启进程（最快，不重建容器）**

```bash
docker compose restart
# 或只重启某个服务
docker compose restart backend
```

> 注意：`restart` 不会重新读取 `.env` 里的环境变量。**若改过 `.env`**，用下面的方式二。

**方式二：重建容器（改了 `.env` 用这个）**

```bash
docker compose down          # 停止并删除容器（保留命名卷/数据）
docker compose up -d --no-build
```

`down` 只删容器和网络，**不带 `-v` 就不会删数据卷**，MySQL 数据完好。

### 2.2 重新 build 前后端后重启

改了后端 Python 代码或前端 Vue 代码，需要重新构建镜像。

> ⚠️ **离线服务器不能直接 build**（要联网拉基础镜像、装依赖）。正确做法是回到[阶段 A](#阶段-a在联网机器上打包构建--导出)在联网机器上重新构建并导出，再拷到服务器 `docker load`。下面分两种场景。

**场景一：服务器可以联网（有外网的环境）**

```bash
# 重新构建并启动，Compose 会自动用新镜像重建变化的容器
docker compose up -d --build

# 只重构某一个：
docker compose build backend
docker compose up -d --no-deps backend
```

**场景二：离线服务器（标准流程）**

在联网机器上重构并导出：

```bash
# 联网机器
cd sport-meeting
git pull        # 或用其它方式更新到最新代码

# 方式一：用一键脚本（推荐）
bash deploy-package.sh      # Linux/Mac
# 或
.\deploy-package.ps1        # Windows
# 生成 deploy-package/ 目录，拷贝到服务器

# 方式二：手动打包
docker compose build backend frontend
docker save -o sfls-images-update.tar \
  sport-meeting-backend:latest sport-meeting-frontend:latest
# 把 sfls-images-update.tar 拷到服务器
```

把更新包拷到服务器后：

```bash
# 离线服务器
cd sport-meeting

# 若用一键脚本打包，先解压运行文件（可能包含更新的 docker-compose.yml）
tar -xzf /path/to/sfls-runtime.tar.gz

# 载入新镜像
docker load -i /path/to/sfls-images-update.tar   # 覆盖旧镜像

# 用新镜像重建容器
docker compose up -d --no-build
docker compose ps
```

Compose 会检测到镜像变化，只重建 backend / frontend，mysql 容器和数据不受影响。

### 2.3 清除数据后重启（清库）

**危险操作**：会**删除数据库所有数据**（学年、项目、报名、日程、成绩全部清空）。重启后回到全新状态，backend 自动重新建表并播种管理员账号。请先确认已[备份](#三数据备份与恢复)。

```bash
# -v 关键：连同命名卷 sport-meeting_mysql-data 一起删除
docker compose down -v

# 重新启动：mysql 是空库，backend 首启会建表 + 播种 admin
docker compose up -d --no-build

docker compose logs -f backend    # 观察建表与播种完成
```

清库后：
- 管理员账号恢复为 `.env` 中的 `ADMIN_USERNAME` / `ADMIN_PASSWORD`。
- 所有业务数据为空，需重新配置学年、导入报名等。

> 如需灌入测试数据（60 班级 / 1071 学生）：
> ```bash
> docker compose exec backend python scripts/generate_test_data.py
> ```

## 三、数据备份与恢复

数据全在 MySQL 命名卷 `sport-meeting_mysql-data` 中。两种备份方式。

### 方式一：SQL 导出（推荐，体积小，可读）

```bash
# 备份（导出到当前目录 backup.sql）
docker compose exec mysql mysqldump \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  sfls_meeting > backup-$(date +%Y%m%d).sql

# 恢复（清库后重灌）
docker compose exec -T mysql mysql \
  -u root -p"$MYSQL_ROOT_PASSWORD" \
  sfls_meeting < backup-20260918.sql
```

> 变量 `$MYSQL_ROOT_PASSWORD` 需从 `.env` 读取或手动替换为实际密码。

### 方式二：卷快照（备份整个卷，最完整）

```bash
# 备份（先停服务，避免脏数据）
docker compose stop mysql
docker run --rm \
  -v sport-meeting_mysql-data:/data \
  -v $(pwd):/backup \
  busybox tar czf /backup/mysql-data-$(date +%Y%m%d).tar.gz -C /data .
docker compose start mysql

# 恢复（前提：卷已存在但要覆盖）
docker compose stop mysql
docker run --rm \
  -v sport-meeting_mysql-data:/data \
  -v $(pwd):/backup \
  busybox sh -c "rm -rf /data/* && tar xzf /backup/mysql-data-20260918.tar.gz -C /data"
docker compose start mysql
```

## 四、常见问题

### Q1: 离线服务器启动时提示 `image not found` 或尝试 build

**原因**：项目目录名与联网机器构建时不一致，Compose 拼出的镜像名对不上。

**解法一**（推荐）：保持目录名一致，都叫 `sport-meeting`。

**解法二**：在 `docker-compose.yml` 里固定镜像名，不依赖自动拼接：

```yaml
services:
  backend:
    image: sfls-backend:latest       # 手动指定
    build: ./backend
    # ...
  frontend:
    image: sfls-frontend:latest      # 手动指定
    build: ./frontend
    # ...
```

联网机器 build 时会用这些名字，`docker save` 时也用这些名字，服务器启动时就能对上。

### Q2: 如何改端口？

`.env` 改 `APP_PORT=8686`，然后 `docker compose down && docker compose up -d --no-build`。

### Q3: backend 启动报错 `Can't connect to MySQL server`

mysql 未完全就绪。查看：

```bash
docker compose logs mysql
# 看到 `ready for connections` 后再重启 backend
docker compose restart backend
```

### Q4: 忘记管理员密码怎么办？

方式一（改 `.env` 重建）：

```bash
# 编辑 .env，改 ADMIN_PASSWORD=new_password
docker compose down
docker compose up -d --no-build
# 重启后 backend bootstrap 会检测管理员已存在则更新密码
```

方式二（SQL 直接改，需进 MySQL）：

```bash
docker compose exec mysql mysql -u root -p
# 输入 MYSQL_ROOT_PASSWORD
mysql> USE sfls_meeting;
mysql> UPDATE users SET hashed_password='<新的bcrypt哈希>' WHERE username='admin';
mysql> exit
```

推荐方式一，简单安全。

### Q5: 如何升级到新版本？

同 [2.2 重新 build](#22-重新-build-前后端后重启) 流程：联网机器拉新代码 → 重构 → 导出 → 服务器载入 → up。数据库 schema 有变动时，backend 启动的 bootstrap 或 Alembic 迁移会自动处理（当前版本未启用 Alembic，表结构变化靠模型 DDL 自动补列）。

### Q6: DeepSeek API 离线服务器能用吗？

不能。DeepSeek API 是外部云服务，离线环境无法访问。日程的「AI 优化」功能不可用，但**其它功能（规则生成、手动编辑、成绩录入、统计等）全部正常**，不依赖外网。

如需在内网使用 AI 功能，可自建兼容 OpenAI API 的本地模型服务（如 Ollama + DeepSeek 模型），修改 `.env` 的 `DEEPSEEK_BASE_URL` 指向内网地址。

### Q7: 容器日志在哪里？

```bash
docker compose logs -f                # 所有服务
docker compose logs -f backend        # 只看后端
docker compose logs --tail=100 mysql  # MySQL 最后 100 行
```

### Q8: 数据库连接参数在哪改？

`.env` 里的 `MYSQL_*` 变量。改后需 `docker compose down && up -d`。

> 注意：改 `MYSQL_DATABASE` / `MYSQL_USER` 会导致容器内数据库名/用户名变化，但已有的命名卷数据库名不会自动跟着改，会导致连不上。建议生产环境这些参数部署前定好，不轻易改。若必须改，走[三、备份恢复](#三数据备份与恢复)流程迁移数据。

---

## 附录：常用命令速查

```bash
# ===== 启动与停止 =====
docker compose up -d --no-build          # 启动（离线必加 --no-build）
docker compose down                       # 停止并删除容器（保留数据）
docker compose down -v                    # 停止 + 删除容器 + 删除数据卷（清库）
docker compose restart                    # 重启所有服务
docker compose restart backend            # 只重启后端

# ===== 查看状态 =====
docker compose ps                         # 容器运行状态
docker compose logs -f                    # 实时查看所有日志
docker compose logs -f backend            # 只看后端日志
docker compose logs --tail=50 mysql       # MySQL 最后 50 行

# ===== 进入容器 =====
docker compose exec backend bash          # 进入后端容器 shell
docker compose exec mysql mysql -u root -p # 进入 MySQL 命令行

# ===== 数据操作 =====
# 备份数据库
docker compose exec mysql mysqldump -u root -p"密码" sfls_meeting > backup.sql
# 恢复数据库
docker compose exec -T mysql mysql -u root -p"密码" sfls_meeting < backup.sql
# 生成测试数据
docker compose exec backend python scripts/generate_test_data.py

# ===== 离线部署关键步骤 =====
# 联网机器：一键打包（推荐）
bash deploy-package.sh              # Linux/Mac
.\deploy-package.ps1                # Windows
# 生成 deploy-package/ 目录，拷贝到服务器

# 或手动打包
docker compose build
docker compose pull mysql
docker save -o sfls-images.tar sport-meeting-backend:latest sport-meeting-frontend:latest mysql:8.0
tar -czf sfls-runtime.tar.gz docker-compose.yml .env.example DEPLOYMENT.md

# 离线服务器：载入并启动
mkdir sport-meeting && cd sport-meeting
tar -xzf /path/to/sfls-runtime.tar.gz
docker load -i /path/to/sfls-images.tar
cp .env.example .env         # 然后编辑 .env 配置密码等
docker compose up -d --no-build
```

---

**维护联系**：赵老师  
**最后更新**：2026-09-18




