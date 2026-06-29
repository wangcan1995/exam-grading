#!/bin/bash
# ============================================================
# 数据备份脚本 - 定时备份 数据库 + 配置
# 用法: bash backup.sh
# 建议: crontab 定时执行, 如每天凌晨3点
#   crontab -e  →  0 3 * * * /path/to/backup.sh
# ============================================================
set -e

# 项目根目录 (脚本所在目录的上级)
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BACKUP_DIR="${PROJECT_DIR}/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/exam_backup_${DATE}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "开始备份..."
echo "  项目目录: $PROJECT_DIR"
echo "  备份文件: $BACKUP_FILE"

# 备份内容:
# - 数据库 (docker volume 里的 sqlite)
# - 环境配置 (.env.prod)
# 不备份图片 (图片建议存COS; 本地图太大不适合打包)
cd "$PROJECT_DIR"

# 从容器复制数据库出来
echo "  [1/2] 导出数据库..."
docker cp exam-backend:/app/data/exam_grading.db /tmp/exam_grading.db 2>/dev/null || {
    echo "  ⚠️  无法从容器复制数据库(容器可能未运行)，跳过"
    touch /tmp/exam_grading.db
}

# 打包
echo "  [2/2] 打包..."
tar -czf "$BACKUP_FILE" \
    -C /tmp exam_grading.db \
    -C "$PROJECT_DIR" .env.prod 2>/dev/null || true

rm -f /tmp/exam_grading.db
SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
echo ""
echo "✅ 备份完成: $BACKUP_FILE ($SIZE)"

# 自动清理 7 天前的备份
find "$BACKUP_DIR" -name "exam_backup_*.tar.gz" -mtime +7 -delete 2>/dev/null
echo "   (已自动清理 7 天前的旧备份)"
