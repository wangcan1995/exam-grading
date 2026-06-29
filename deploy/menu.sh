#!/bin/bash
# ============================================================
#  阅卷系统 - 运维菜单（数字选择，一键操作）
# ============================================================
#  用法: bash deploy/menu.sh
#  建议: 加个别名，以后直接敲 menu 进菜单
#        echo "alias menu='bash ~/exam-grading/deploy/menu.sh'" >> ~/.bashrc && source ~/.bashrc
# ============================================================

PROJECT_DIR="${PROJECT_DIR:-$HOME/exam-grading}"
COMPOSE_FILE="docker-compose.prod.yml"
cd "$PROJECT_DIR" || { echo "项目目录不存在: $PROJECT_DIR"; exit 1; }

# 判断是否需要 sudo（docker 组没生效时）
USE_SUDO=""
if ! docker info &> /dev/null; then
    USE_SUDO="sudo"
fi

# ---------- 颜色 ----------
BLUE='\033[0;34m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
title() { echo -e "\n${CYAN}════════════════════════════════════════${NC}"; }
pause() { echo ""; read -n 1 -s -r -p "按任意键返回菜单..."; }

# ---------- 各操作函数 ----------
show_status() {
    title; echo -e "${CYAN} 服务状态 ${NC}"; echo -e "${CYAN}════════════════════════════════════════${NC}"
    echo ""
    echo "【容器状态】"
    $USE_SUDO docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || echo "  (服务未启动)"
    echo ""
    echo "【健康检查】"
    if curl -sf http://localhost/health > /dev/null 2>&1; then
        echo -e "  ${GREEN}✓ 后端正常${NC}: $(curl -s http://localhost/health)"
    else
        echo -e "  ${RED}✗ 后端无响应${NC}"
    fi
    echo ""
    echo "【磁盘占用】"
    df -h / | tail -1 | awk '{printf "  总计 %s  已用 %s (%s)  可用 %s\n", $2, $3, $5, $4}'
    echo ""
    echo "【最近备份】"
    ls -lht backups/*.tar.gz 2>/dev/null | head -3 | awk '{printf "  %s  %s\n", $6" "$7, $9}' || echo "  (暂无备份)"
    pause
}

start_service() {
    title; echo -e "${CYAN} 启动服务 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    if [ -d frontend/dist ]; then
        echo "启动中（首次约 3-5 分钟构建镜像）..."
        $USE_SUDO docker compose -f "$COMPOSE_FILE" up -d --build
    else
        echo -e "${YELLOW}前端未构建，需要先构建。是否现在构建？(y/n)${NC}"
        read -p "> " ANS
        if [ "$ANS" = "y" ] || [ "$ANS" = "Y" ]; then
            build_frontend
        else
            echo "取消启动。请先构建前端。"
            pause; return
        fi
    fi
    echo ""
    echo -e "${GREEN}✓ 启动命令已执行${NC}"
    echo "等待服务就绪..."
    for i in $(seq 1 30); do
        curl -sf http://localhost/health > /dev/null 2>&1 && { echo -e "${GREEN}✓ 服务已就绪${NC}"; break; }
        sleep 2; printf "."
    done
    pause
}

build_frontend() {
    echo "构建前端..."
    cd frontend
    if ! command -v node &> /dev/null; then
        echo "安装 Node.js..."
        curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
        sudo apt install -y nodejs
    fi
    npm install --registry=https://registry.npmmirror.com
    npm run build
    cd "$PROJECT_DIR"
    echo -e "${GREEN}✓ 前端构建完成${NC}"
}

stop_service() {
    title; echo -e "${CYAN} 停止服务 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    echo "停止并删除容器（数据保留）..."
    $USE_SUDO docker compose -f "$COMPOSE_FILE" down
    echo -e "\n${GREEN}✓ 已停止${NC}"
    pause
}

restart_service() {
    title; echo -e "${CYAN} 重启服务 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    $USE_SUDO docker compose -f "$COMPOSE_FILE" restart
    echo -e "\n${GREEN}✓ 已重启${NC}"
    pause
}

update_code() {
    title; echo -e "${CYAN} 更新代码 + 重新部署 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    echo "【1/3】拉取最新代码..."
    git pull
    echo ""
    echo "【2/3】重新构建前端？(改了后端/配置可选 n，改了前端选 y)"
    read -p "重新构建前端？(y/n) > " ANS
    if [ "$ANS" = "y" ] || [ "$ANS" = "Y" ]; then
        build_frontend
    fi
    echo ""
    echo "【3/3】重建并启动容器..."
    $USE_SUDO docker compose -f "$COMPOSE_FILE" up -d --build
    echo -e "\n${GREEN}✓ 更新完成${NC}"
    pause
}

show_logs() {
    title; echo -e "${CYAN} 实时日志（Ctrl+C 退出）${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    echo "1) 全部日志   2) 仅后端   3) 仅 Nginx"
    read -p "选择 > " L
    case "$L" in
        2) $USE_SUDO docker compose -f "$COMPOSE_FILE" logs -f --tail=50 backend ;;
        3) $USE_SUDO docker compose -f "$COMPOSE_FILE" logs -f --tail=50 nginx ;;
        *) $USE_SUDO docker compose -f "$COMPOSE_FILE" logs -f --tail=50 ;;
    esac
    pause
}

do_backup() {
    title; echo -e "${CYAN} 手动备份 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    bash deploy/backup.sh
    pause
}

enter_shell() {
    title; echo -e "${CYAN} 进入后端容器 ${NC}"
    echo -e "${CYAN}════════════════════════════════════════${NC}\n"
    echo "进入后端容器（输入 exit 退出）..."
    $USE_SUDO docker compose -f "$COMPOSE_FILE" exec backend bash
}

exit_menu() {
    echo -e "\n${GREEN}再见！${NC}"
    exit 0
}

# ---------- 主菜单循环 ----------
while true; do
    echo -e "\n${CYAN}╔════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     试卷阅卷系统 - 运维菜单           ║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}1)${NC} 📊 查看状态           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}2)${NC} ▶️  启动服务           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}3)${NC} ⏹️  停止服务           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}4)${NC} 🔄 重启服务           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}5)${NC} 📥 更新代码+重新部署  ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}6)${NC} 📜 查看日志           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}7)${NC} 💾 手动备份           ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}8)${NC} 🐚 进入后端容器       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}  ${GREEN}0)${NC} 🚪 退出               ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════╝${NC}"
    echo ""
    read -p "请选择 [0-8] > " choice

    case "$choice" in
        1) show_status ;;
        2) start_service ;;
        3) stop_service ;;
        4) restart_service ;;
        5) update_code ;;
        6) show_logs ;;
        7) do_backup ;;
        8) enter_shell ;;
        0) exit_menu ;;
        *) echo -e "${RED}无效选择${NC}"; sleep 1 ;;
    esac
done
