#!/bin/bash
# ============================================================
#  阅卷系统 - 卸载脚本 (干净回滚,保留数据备份)
# ============================================================
#  用法: bash deploy/uninstall.sh
#  会停止并删除容器,但保留:
#    - 数据库数据 (Docker volume)
#    - .env.prod 配置
#    - backups/ 备份
#  如需彻底删除(含数据),加 --purge 参数
# ============================================================
set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="${PROJECT_DIR:-$HOME/exam-grading}"
COMPOSE_FILE="docker-compose.prod.yml"
PURGE=false

if [ "$1" = "--purge" ]; then
    PURGE=true
fi

echo -e "\n${YELLOW}========================================${NC}"
echo -e "${YELLOW}  阅卷系统 - 卸载${NC}"
echo -e "${YELLOW}========================================${NC}\n"

cd "$PROJECT_DIR"

# 1. 停止并删除容器
info() { echo -e "${BLUE}[INFO]${NC} $*"; }
ok()   { echo -e "${GREEN}[OK]${NC}   $*"; }

if [ -f "$COMPOSE_FILE" ]; then
    info "停止并删除容器..."
    sudo docker compose -f "$COMPOSE_FILE" down
    ok "容器已停止并删除"
fi

# 2. 处理数据卷
if [ "$PURGE" = true ]; then
    info "${RED}--purge 模式: 删除所有数据(含数据库)!${NC}"
    read -p "确认彻底删除所有数据? 输入 yes 继续: " CONFIRM
    if [ "$CONFIRM" = "yes" ]; then
        sudo docker compose -f "$COMPOSE_FILE" down -v
        ok "数据卷已删除"
    else
        info "取消删除,数据保留"
    fi
else
    ok "保留数据卷 (数据库/图片),容器已停止"
    info "如需彻底删除: bash deploy/uninstall.sh --purge"
fi

# 3. 移除备份定时任务
if crontab -l 2>/dev/null | grep -q "backup.sh"; then
    crontab -l | grep -v "backup.sh" | crontab -
    ok "已移除备份定时任务"
fi

echo ""
echo -e "${GREEN}卸载完成${NC}"
if [ "$PURGE" != true ]; then
    echo -e "  数据保留在 Docker volume,重新部署即可恢复:"
    echo -e "  ${BLUE}bash deploy/install.sh${NC}"
fi
echo ""
