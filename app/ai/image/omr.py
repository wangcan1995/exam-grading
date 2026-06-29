"""OMR 涂卡检测模块 — 客观题自动判分的核心。

原理:
- 答题卡经透视矫正后是标准尺寸，每个选项(圆圈/方框)的坐标是固定的。
- 对每个选项区域统计"黑像素占比"(fill_ratio)。
- fill_ratio > 阈值 → 判定已涂。

判分逻辑:
- 单题检测出的已涂选项与标准答案比对。
- 多涂/未涂 → 置信度降低，进入人工复核队列。
"""
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.core.config import settings


@dataclass
class BubbleRegion:
    """单个选项(气泡)的坐标区域。坐标基于矫正后的标准答题卡。"""
    option: str            # "A" / "B" / "C" / ...
    cx: float              # 中心 x
    cy: float              # 中心 y
    radius: float          # 圆半径 (或方框半边长)


@dataclass
class QuestionLayout:
    """一道客观题在答题卡上的布局定义。"""
    question_no: str                       # "1" / "2" ...
    options: list[BubbleRegion]            # 各选项位置
    correct_answer: str                    # 标准答案 "C"
    score: float = 1.0                     # 题目分值


@dataclass
class BubbleResult:
    """单个气泡的检测结果。"""
    option: str
    fill_ratio: float          # 黑像素占比 [0, 1]
    marked: bool               # 是否判定为已涂


@dataclass
class QuestionGradeResult:
    """一道题的判分结果。"""
    question_no: str
    options: list[BubbleResult]
    detected_answer: str          # 检测出的答案，如 "C"；多涂则 "AC"；未涂则 ""
    correct_answer: str
    is_correct: Optional[bool]    # None = 置信度不足，无法判定
    confidence: float             # [0, 1]，多涂/未涂会降低
    score: float                  # 得分
    max_score: float
    needs_review: bool            # 是否需人工复核
    reason: str = ""              # 触发复核的原因


def measure_fill_ratio(
    binary: np.ndarray, cx: float, cy: float, radius: float
) -> float:
    """统计指定圆形区域内【黑色像素】占比。

    二值化约定: 背景=白(255)，涂卡/墨迹=黑(0)。
    因此黑色像素占比越高，说明该选项涂得越满。
    实际测量时只用内圈 (0.7*radius) 避免边缘干扰。
    """
    h, w = binary.shape[:2]
    # 圆形 mask
    mask = np.zeros((h, w), dtype=np.uint8)
    inner_r = max(1.0, radius * 0.7)
    cv2.circle(mask, (int(cx), int(cy)), int(inner_r), 255, -1)

    total = cv2.countNonZero(mask)
    if total == 0:
        return 0.0
    # mask 区域内，黑色像素(值=0)的数量
    region = cv2.bitwise_or(binary, binary, mask=mask)  # mask 外置0
    black = total - cv2.countNonZero(region)
    return black / total


def detect_marked_options(
    binary: np.ndarray,
    bubbles: list[BubbleRegion],
    threshold: Optional[float] = None,
) -> list[BubbleResult]:
    """检测一组选项中哪些被涂了。

    :param threshold: 涂卡阈值，默认用 settings.omr_fill_threshold
    """
    thr = threshold if threshold is not None else settings.omr_fill_threshold
    results = []
    for b in bubbles:
        ratio = measure_fill_ratio(binary, b.cx, b.cy, b.radius)
        results.append(
            BubbleResult(option=b.option, fill_ratio=ratio, marked=ratio >= thr)
        )
    return results


def grade_question(
    binary: np.ndarray, layout: QuestionLayout
) -> QuestionGradeResult:
    """判分一道客观题。

    置信度规则:
    - 正好涂 1 个 + 答案正确 → confidence=1.0，不需复核
    - 正好涂 1 个 + 答案错误 → confidence=0.95，不需复核(涂卡清晰只是答错)
    - 多涂 → confidence=0.3，需复核 (学生可能想改答案)
    - 未涂 → confidence=0.4，需复核 (可能擦得太干净或漏涂)
    """
    results = detect_marked_options(binary, layout.options)
    marked = [r for r in results if r.marked]
    detected = "".join(r.option for r in marked)

    is_correct: Optional[bool]
    confidence: float
    needs_review = False
    reason = ""

    if len(marked) == 0:
        is_correct = None
        confidence = 0.4
        needs_review = True
        reason = "未检测到涂卡(可能漏涂或擦除过度)"
    elif len(marked) > 1:
        is_correct = None
        confidence = 0.3
        needs_review = True
        reason = f"检测到多涂: {detected}(学生可能涂改)"
    else:
        # 正好涂 1 个
        is_correct = (detected == layout.correct_answer)
        confidence = 0.95 if is_correct else 0.90

    score = layout.score if (is_correct is True) else 0.0

    return QuestionGradeResult(
        question_no=layout.question_no,
        options=results,
        detected_answer=detected,
        correct_answer=layout.correct_answer,
        is_correct=is_correct,
        confidence=confidence,
        score=score,
        max_score=layout.score,
        needs_review=needs_review,
        reason=reason,
    )
