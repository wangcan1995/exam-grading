#!/bin/bash
# ============================================================
#  试卷阅卷打分系统 - 一键安装脚本（仅装环境 + 拉代码）
# ============================================================
#  用法（在新服务器上执行一次）:
#    bash deploy/install.sh
#
#  只做两件事:
#    1. 装 Docker（已装则跳过）
#    2. 拉项目代码到 ~/exam-grading
#
#  装完后用运维菜单启动服务:
#    bash ~/exam-grading/deploy/menu.sh
# ============================================================
set -e

BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}   $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

PROJECT_DIR="${PROJECT_DIR:-$HOME/exam-grading}"
REPO_URL="${REPO_URL:-https://github.com/wangcan1995/exam-grading.git}"

echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}  阅卷系统 - 环境安装（拉代码）${NC}"
echo -e "${BLUE}========================================${NC}\n"

# ---------- 1. 装 Docker ----------
info "检查 Docker..."
if command -v docker &> /dev/null; then
    ok "Docker 已装: $(docker --version)"
else
    info "安装 Docker..."
    curl -fsSL https://get.docker.com | bash -s docker --mirror Aliyun
    sudo systemctl enable docker && sudo systemctl start docker

    # 国内镜像加速
    if [ ! -f /etc/docker/daemon.json ]; then
        sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{"registry-mirrors": ["https://docker.m.daocloud.io", "https://dockerproxy.com"]}
EOF
        sudo systemctl daemon-reload && sudo systemctl restart docker
    fi
    ok "Docker 安装完成: $(docker --version)"
fi

# 加入 docker 组（免 sudo，需重新登录生效）
if ! groups | grep -q docker; then
    sudo usermod -aG docker "$USER"
    warn "已加入 docker 组，重新登录后可免 sudo"
fi

# ---------- 2. 拉代码 ----------
info "拉取代码到 $PROJECT_DIR ..."
if [ -d "$PROJECT_DIR/.git" ]; then
    cd "$PROJECT_DIR"
    git pull --rebase || warn "git pull 失败，使用现有代码"
else
    git clone "$REPO_URL" "$PROJECT_DIR"
fi
ok "代码就绪: $PROJECT_DIR"

# ---------- 3. 生成配置模板 ----------
cd "$PROJECT_DIR"
[ ! -f .env.prod ] && cp .env.prod.example .env.prod && ok "已生成 .env.prod 模板"

# ---------- 完成 ----------
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  ✅ 环境安装完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "下一步：进入运维菜单启动服务"
echo -e "  ${BLUE}bash $PROJECT_DIR/deploy/menu.sh${NC}"
echo ""
echo -e "${YELLOW}提示：${NC}"
echo -e "  · 若提示 docker 权限不足，先退出 ssh 重新登录（让 docker 组生效）"
echo -e "  · 想以后直接敲 menu 进菜单，可加个别名："
echo -e "    echo \"alias menu='bash $PROJECT_DIR/deploy/menu.sh'\" >> ~/.bashrc && source ~/.bashrc"
echo ""
