# 试卷扫描 + 阅卷打分系统 📝

> AI 辅助判分 + 人工复核的试卷阅卷系统。扫描答题卡 → OpenCV 定位矫正 → OMR/OCR/LLM 判分 → 人工复核出分。

**当前状态：第 1 期 MVP**（客观题自动判分闭环已实现 ✅ 已跑通端到端验证）

> 已验证：从扫描图片上传 → 预处理 → 锚点定位 → 透视矫正 → OMR 涂卡检测 → 判分入库 → HTTP API 返回结果，全流程闭环，判分准确。

---

## ✨ 功能特性

| 题型 | 判分方式 | 准确率 | 状态 |
|---|---|---|---|
| 客观题（选择/判断） | OpenCV 涂卡检测（OMR） | >99% | ✅ MVP 已完成 |
| 填空题 | 手写 OCR + 文本比对 | 70-85% | 🔜 第 2 期 |
| 简答/解答题 | 大模型判分 + 人工复核 | 80-90% | 🔜 第 2 期 |
| 作文 | 大模型多维评分 + 人工复核 | - | 🔜 第 2 期 |

**核心机制**：每个判分结果带 `confidence`（置信度），低于阈值的自动进人工复核队列——用"AI 提效 + 人工兜底"平衡效率与准确。

---

## 🏗️ 技术栈

- **后端**：FastAPI + SQLAlchemy + SQLite（MVP）/ PostgreSQL（生产）
- **图像处理**：OpenCV（预处理、锚点定位、透视矫正、OMR 涂卡检测）
- **OCR**：PaddleOCR（第 2 期）
- **大模型**：GLM-4.6 / DeepSeek / Qwen（第 2 期）
- **前端**：Vue 3 + Vite + Element Plus（第 1 期后补充）

### ⚠️ 已知限制（MVP）

- **歪斜容错有限**：当前 `deskew`（倾斜矫正）对无边框的白底图检测不可靠，要求扫描件尽量摆正。透视矫正依赖答题卡四角锚点 + 模板参考坐标，模板需配置 `anchors` 字段才能精确对齐。后续可加文档外边框检测或换用更鲁棒的 deskew 算法。
- **答题卡模板需预先配置**：通过脚本/JSON 定义每题选项的坐标（基于矫正后标准坐标系），可视化模板编辑器在第 4 期实现。
- **同步判分**：MVP 为同步处理（客观题很快），生产环境改 Celery 异步 + WebSocket 进度推送。

---

## 🚀 快速开始

### 方式一：本地 Python 运行（开发）

```bash
cd exam-grading

# 1. 创建虚拟环境并安装依赖
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env

# 3. 生成测试数据（答题卡图片 + 模板）
python scripts/gen_answer_sheet.py

# 4. 跑端到端验证（验证判分流水线）
python tests/test_e2e_grading.py

# 5. 启动 API 服务
python run.py
# 访问 http://localhost:8000/docs 查看交互式 API 文档
```

### 方式二：Docker 一键启动

```bash
cd exam-grading
docker compose up --build
# 后端: http://localhost:8000  前端: http://localhost:5173
```

### 方式三：生产服务器部署（Ubuntu / 4核4G）

**一次安装环境（新服务器执行一次）**：
```bash
bash deploy/install.sh      # 装 Docker + 拉代码 + 生成配置
```

**日常运维（数字菜单，选数字操作）**：
```bash
bash deploy/menu.sh         # 进菜单：启动/停止/重启/更新代码/看日志/状态/备份
```

> 💡 建议加别名，以后直接敲 `menu` 进菜单：
> `echo "alias menu='bash ~/exam-grading/deploy/menu.sh'" >> ~/.bashrc && source ~/.bashrc`

详细流程见 **[部署指南](docs/部署指南.md)**。

`deploy/` 目录脚本说明：

| 脚本 | 用途 |
|---|---|
| `install.sh` | 一次性安装：装 Docker + 拉代码 + 生成 `.env.prod` |
| `menu.sh` | ⭐ 日常运维菜单（启动/停止/重启/更新/日志/状态/备份/进容器） |
| `backup.sh` | 数据备份（数据库+配置打包，菜单里也能调用） |
| `uninstall.sh` | 卸载（保留数据；加 `--purge` 彻底删除） |
| `nginx.conf` | Nginx 反代配置 |


---

## 📖 API 概览

| 接口 | 说明 |
|---|---|
| `POST /api/papers` | 创建试卷（含答题卡模板坐标） |
| `GET /api/papers` | 试卷列表 |
| `POST /api/scan/upload` | **上传答题卡图片并立即判分** |
| `GET /api/sheets` | 答题卡列表 |
| `GET /api/sheets/{id}/results` | 单卷逐题判分明细 |
| `GET /api/images/{id}/{original\|processed}` | 查看原图/矫正后图 |
| `GET /api/review/pending` | 待复核题目列表 |
| `PUT /api/review/{result_id}` | 人工复核改分 |
| `GET /api/stats/papers/{id}` | 成绩统计 + 错题率 |

完整交互文档：启动后访问 `/docs`（Swagger UI）。

---

## 🗂️ 项目结构

```
exam-grading/
├── app/
│   ├── ai/image/              # ★ 图像处理核心
│   │   ├── preprocess.py      # 去噪/二值化/倾斜矫正
│   │   ├── anchor.py          # 锚点检测 + 透视矫正
│   │   └── omr.py             # OMR 涂卡检测（客观题判分）
│   ├── api/                   # FastAPI 路由
│   ├── services/              # 业务编排（判分调度器）
│   ├── models/                # ORM 数据模型
│   └── core/                  # 配置、数据库
├── scripts/
│   └── gen_answer_sheet.py    # 测试答题卡生成器
├── tests/
│   └── test_e2e_grading.py    # 端到端判分测试
├── frontend/                  # Vue3 前端（待补充）
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## 🧪 如何验证判分效果

```bash
# 1. 生成一张测试答题卡（含已知答案 + 倾斜角度）
python scripts/gen_answer_sheet.py

# 2. 跑判分测试，会打印每题的识别结果和得分
python tests/test_e2e_grading.py
```

预期输出：
```
✓ 端到端判分测试通过！
============================================================
试卷: 测试卷-选择题 (满分 10.0)
题号  学生答案  标准答案  检测    得分    结果
------------------------------------------------------------
1     A         A         A       2.0     ✓对
2     C         C         C       2.0     ✓对
3     D         B         D       0.0     ✗错
...
============================================================
```

---

## 📋 开发路线图

- [x] **第 1 期 MVP**：客观题 OMR 自动判分闭环
- [ ] **学生身份自动识别**：学号 OMR 填涂区识别 + 学生名册反查 + 姓名 OCR 核验 👉 [实现计划](docs/学生身份自动识别-实现计划.md)
- [ ] **第 2 期**：接入 PaddleOCR（填空题）+ 大模型（简答/作文）
- [ ] **第 3 期**：人工复核 Web 界面（Fabric.js 批注 + 改分）
- [ ] **第 4 期**：多评/双盲、答题卡模板设计器、批量扫描

详见 `docs/` 下的整体方案文档。
