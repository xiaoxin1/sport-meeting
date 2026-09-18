#!/bin/bash
# 一键打包离线部署包（联网机器上执行）

set -e

echo "=== SFLS 运动会系统 - 离线部署包制作 ==="
echo ""

# 1. 构建镜像
echo "[1/4] 构建镜像..."
docker compose build
docker compose pull mysql

# 2. 导出镜像
echo "[2/4] 导出镜像..."
docker save -o sfls-images.tar \
  sport-meeting-backend:latest \
  sport-meeting-frontend:latest \
  mysql:8.0

# 3. 打包最小运行文件（仅需这三个文件）
echo "[3/4] 打包运行文件..."
tar -czf sfls-runtime.tar.gz \
  docker-compose.yml \
  .env.example \
  DEPLOYMENT.md

# 4. 合并为单个部署包（可选）
echo "[4/4] 生成最终部署包..."
mkdir -p deploy-package
mv sfls-images.tar deploy-package/
mv sfls-runtime.tar.gz deploy-package/

cat > deploy-package/README.txt << 'EOF'
SFLS 运动会系统 - 离线部署包
================================

本目录包含：
  sfls-images.tar       - Docker 镜像（~500MB-1GB）
  sfls-runtime.tar.gz   - 运行配置文件（<10KB）

部署步骤（在服务器上）：
  1. 解压运行文件：
     tar -xzf sfls-runtime.tar.gz

  2. 配置环境：
     cp .env.example .env
     # 编辑 .env，至少修改：
     #   MYSQL_ROOT_PASSWORD / MYSQL_PASSWORD
     #   JWT_SECRET / ADMIN_PASSWORD
     #   APP_PORT（默认8687）

  3. 载入镜像：
     docker load -i sfls-images.tar

  4. 启动：
     docker compose up -d --no-build

详细说明见 DEPLOYMENT.md
EOF

echo ""
echo "✅ 部署包已生成到 deploy-package/ 目录"
echo "   - sfls-images.tar (镜像)"
echo "   - sfls-runtime.tar.gz (配置文件，仅含3个文件)"
echo "   - README.txt (部署说明)"
echo ""
echo "拷贝整个 deploy-package/ 目录到服务器即可部署"
