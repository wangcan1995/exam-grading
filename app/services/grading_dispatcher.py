"""判分调度服务 — 串联整条判分流水线。

流程: 预处理 → 锚点矫正 → 按模板遍历每道客观题 → OMR 判分 → 汇总
这是后端业务层最核心的编排逻辑。
"""
from datetime import datetime
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger
from sqlalchemy.orm import Session

from app.ai.image import (
    AnchorPoints,
    BubbleRegion,
    QuestionLayout,
    detect_and_warp,
    grade_question,
    preprocess,
)
from app.ai.image.preprocess import adaptive_threshold, denoise
from app.core.config import settings
from app.models import ExamPaper, GradingResult, StudentSheet


def _get_questions(template_json) -> list[dict]:
    """从模板 JSON 取题目列表，兼容两种格式:
    - 新格式: {"anchors": {...}, "questions": [...]}
    - 旧格式: [...] (纯题目数组)
    """
    if isinstance(template_json, dict):
        return template_json.get("questions", [])
    if isinstance(template_json, list):
        return template_json
    return []


def _get_reference_anchors(template_json) -> Optional[AnchorPoints]:
    """从模板提取参考锚点坐标(用于透视矫正 dst)。无则返回 None。"""
    if not isinstance(template_json, dict):
        return None
    a = template_json.get("anchors")
    if not a or len(a) < 4:
        return None
    try:
        return AnchorPoints(
            top_left=tuple(a["top_left"]),
            top_right=tuple(a["top_right"]),
            bottom_right=tuple(a["bottom_right"]),
            bottom_left=tuple(a["bottom_left"]),
        )
    except (KeyError, TypeError):
        return None


def _template_to_layout(template_json) -> list[QuestionLayout]:
    """把数据库里的答题卡模板 JSON 转成 QuestionLayout 对象。"""
    layouts = []
    for q in _get_questions(template_json):
        options = [
            BubbleRegion(
                option=o["option"],
                cx=float(o["cx"]),
                cy=float(o["cy"]),
                radius=float(o["radius"]),
            )
            for o in q.get("options", [])
        ]
        layouts.append(
            QuestionLayout(
                question_no=str(q["question_no"]),
                options=options,
                correct_answer=str(q["correct_answer"]),
                score=float(q.get("score", 1.0)),
            )
        )
    return layouts


def _save_image(img: np.ndarray, name: str) -> str:
    """保存矫正后图片，返回 key (相对项目根路径，兼容本地/COS)。

    本地模式: 存到 storage/processed/{name}
    COS 模式: 存到 COS 的 storage/processed/{name}
    """
    from app.core.storage import get_storage
    key = f"storage/processed/{name}"
    return get_storage().save_image(img, key)


def grade_student_sheet(
    db: Session, sheet: StudentSheet, paper: ExamPaper
) -> StudentSheet:
    """对一张学生答题卡执行完整判分流程。

    会原地更新 sheet 和写入 grading_result 记录。
    """
    sheet.status = "grading"
    db.flush()
    logger.info(f"开始判分 sheet={sheet.id} paper={paper.name}")

    # ① 预处理 (从存储层读原图到内存，兼容本地/COS)
    from app.core.storage import get_storage
    from app.ai.image import preprocess_image
    original_img = get_storage().read_image(sheet.original_path)
    if original_img is None:
        raise FileNotFoundError(f"原图读取失败: {sheet.original_path}")
    _, deskewed_bgr, binary = preprocess_image(original_img)
    logger.info(
        f"预处理完成 sheet={sheet.id} "
        f"shape={deskewed_bgr.shape} 矫正图尺寸"
    )

    # ② 锚点检测 + 透视矫正。传入模板参考锚点，保证矫正后坐标系与模板一致
    ref_anchors = _get_reference_anchors(paper.template_json)
    warp = detect_and_warp(binary, deskewed_bgr, reference_anchors=ref_anchors)
    sheet.processed_path = _save_image(warp.warped, f"sheet_{sheet.id}_warped.png")
    if warp.fallback_used:
        logger.warning(
            f"sheet={sheet.id} 未检测到锚点，使用页面边缘兜底矫正，"
            "建议检查图片质量或答题卡是否含标准锚点"
        )
    db.flush()

    # ③ 对矫正后图重新二值化 (保证检测精度)
    gray = cv2.cvtColor(warp.warped, cv2.COLOR_BGR2GRAY) if len(warp.warped.shape) == 3 else warp.warped
    warped_binary = adaptive_threshold(denoise(gray))

    # ④ 遍历模板逐题判分
    layouts = _template_to_layout(paper.template_json)
    if not layouts:
        logger.warning(f"试卷 {paper.id} 没有配置答题卡模板，跳过判分")
        sheet.status = "graded"
        sheet.needs_review = True
        db.flush()
        return sheet

    # 清理旧结果(支持重判)
    db.query(GradingResult).filter(GradingResult.sheet_id == sheet.id).delete()
    db.flush()

    total = 0.0
    any_review = False
    for layout in layouts:
        result = grade_question(warped_binary, layout)
        logger.debug(
            f"  题{result.question_no}: 检测={result.detected_answer or '∅'} "
            f"正确={result.correct_answer} 得分={result.score} "
            f"置信度={result.confidence:.2f} 复核={result.needs_review}"
        )

        # 各选项的 fill_ratio 明细存 JSON，便于前端可视化展示
        options_detail = [
            {"option": o.option, "fill_ratio": round(o.fill_ratio, 3),
             "marked": o.marked}
            for o in result.options
        ]

        gr = GradingResult(
            sheet_id=sheet.id,
            question_no=result.question_no,
            question_type="objective",
            ai_score=result.score,
            confidence=result.confidence,
            detected_answer=result.detected_answer,
            correct_answer=result.correct_answer,
            detail={"options": options_detail,
                    "reason": result.reason,
                    "is_correct": result.is_correct},
            max_score=result.max_score,
            needs_review=result.needs_review,
            review_status="pending" if result.needs_review else "auto",
            final_score=result.score,
        )
        db.add(gr)
        total += result.score
        if result.needs_review:
            any_review = True

    # ⑤ 汇总
    sheet.total_score = round(total, 2)
    sheet.needs_review = any_review
    sheet.status = "graded"
    sheet.graded_at = datetime.utcnow()
    db.commit()
    logger.info(
        f"判分完成 sheet={sheet.id} 总分={sheet.total_score} "
        f"需复核={'是' if any_review else '否'}"
    )
    return sheet
