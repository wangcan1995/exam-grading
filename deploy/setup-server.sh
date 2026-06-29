#!/bin/bash
# ============================================================
# 服务器初始化脚本 - 在新买的 Ubuntu 服务器上执行一次
# 用法: bash setup-server.sh
# 作用: 装 Docker + 建目录 + 配防火墙
# ============================================================
set -e

echo "=========================================="
echo "  试卷阅卷系统 - 服务器初始化"
echo "=========================================="

# 1. 更新系统
echo "[1/4] 更新系统包..."
apt update -y && apt upgrade -y

# 2. 安装 Docker
if ! command -v docker &> /dev/null; then
    echo "[2/4] 安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker
    systemctl start docker
    echo "  Docker 版本: $(docker --version)"
else
    echo "[2/4] Docker 已安装: $(docker --version)"
fi

# 3. 安装 docker compose 插件
if ! docker compose version &> /dev/null; then
    echo "[3/4] 安装 docker compose 插件..."
    apt install -y docker-compose-plugin
fi
echo "  Compose 版本: $(docker compose version)"

# 4. 配置防火墙 (开放 Web 端口 + SSH)
echo "[4/4] 配置防火墙..."
if command -v ufw &> /dev/null; then
    ufw allow 22/tcp      # SSH
    ufw allow 80/tcp      # HTTP
    ufw allow 443/tcp     # HTTPS
    ufw --force enable
    ufw status
fi

echo ""
echo "=========================================="
echo "  ✅ 服务器初始化完成!"
echo "=========================================="
echo ""
echo "下一步:"
echo "  1. 把项目代码上传到服务器 (用 git clone 或 scp)"
echo "  2. cd 到项目目录"
echo "  3. cp .env.prod.example .env.prod  并编辑配置"
echo "  4. cd frontend && npm install && npm run build  (构建前端)"
echo "  5. docker compose -f docker-compose.prod.yml up -d --build"
echo ""
echo "详细步骤见: docs/部署指南.md"
