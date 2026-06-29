"""答题卡锚点检测 + 透视矫正模块。

设计思路:
- 标准答题卡四角有定位锚点(黑色实心方块/L形角标)。
- 检测这 4 个锚点 → 计算透视变换矩阵 → 把答题卡"摆正"到标准尺寸。
- 矫正后，所有题块位置可用统一的归一化坐标定位，无需每张图重新检测。

锚点检测策略 (按优先级):
1. 模板匹配 (cv2.matchTemplate) — 有标准锚点模板时最稳
2. 轮廓特征过滤 — 无模板时，用面积+长宽比+位置过滤四角的方形黑块
"""
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from app.core.config import settings


@dataclass
class AnchorPoints:
    """答题卡四角锚点坐标 (按 TL, TR, BR, BL 顺序)。"""
    top_left: tuple[float, float]
    top_right: tuple[float, float]
    bottom_right: tuple[float, float]
    bottom_left: tuple[float, float]

    def as_array(self) -> np.ndarray:
        """返回 (4,2) float32 数组，供 cv2.perspectiveTransform 使用。"""
        return np.array(
            [self.top_left, self.top_right, self.bottom_right, self.bottom_left],
            dtype=np.float32,
        )


@dataclass
class WarpResult:
    """透视矫正结果。"""
    warped: np.ndarray               # 矫正后的 BGR 图
    anchors: AnchorPoints            # 检测到的锚点 (用于调试/可视化)
    fallback_used: bool              # 是否用了边缘兜底(未检测到锚点)
    matrix: np.ndarray               # 透视变换矩阵


def _detect_corner_blocks(binary: np.ndarray) -> list[tuple[float, float, float, float]]:
    """在二值图中检测方形黑色锚点(仅按形状特征，不限位置)。

    锚点(实心方块) vs 选项圆圈 的关键区分:
    - 圆度 circularity = 4π·area / peri²；圆≈1.0，方块≈0.78，但二者接近，不够稳。
    - 更稳的是"外接矩形填充率"：实心方块 fill_ratio≈1.0，圆圈 fill_ratio≈π/4≈0.785。
      且锚点是实心方块，圆圈即便涂黑其外接矩形内也有四角空白 → fill_ratio 更低。

    :return: [(cx, cy, w, h), ...] 每个候选锚点的中心坐标和尺寸
    """
    # 取反让黑色锚点成为前景(白)，findContours 才能找到
    fg = cv2.bitwise_not(binary)
    contours, _ = cv2.findContours(
        fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )

    h, w = binary.shape
    candidates = []
    img_area = h * w

    for c in contours:
        area = cv2.contourArea(c)
        # 锚点面积占图片的 0.01% ~ 0.5%
        if area < img_area * 0.0001 or area > img_area * 0.005:
            continue

        x, y, bw, bh = cv2.boundingRect(c)
        aspect = bw / bh if bh > 0 else 0
        # 锚点应接近正方形 (0.6 ~ 1.6)
        if not (0.6 <= aspect <= 1.6):
            continue

        peri = cv2.arcLength(c, True)
        if peri == 0:
            continue

        # 实心方块的矩形填充率高 (方块≈1.0，圆圈≈0.78)
        fill_ratio = area / (bw * bh)
        # 锚点要求填充率 ≥0.85，把圆圈(≤0.785)排除掉
        if fill_ratio < 0.85:
            continue

        candidates.append((x + bw / 2, y + bh / 2, bw, bh))

    return candidates


def _select_corner_anchors(
    candidates: list[tuple[float, float, float, float]],
    img_h: int,
    img_w: int,
    corner_region_ratio: float = 0.12,
) -> Optional[AnchorPoints]:
    """从候选锚点中选出最可能位于四角的 4 个点。

    :param corner_region_ratio: 四角搜索区域占图片边长的比例(每角 12%)
    """
    if len(candidates) < 4:
        return None

    margin_x = img_w * corner_region_ratio
    margin_y = img_h * corner_region_ratio

    def in_corner(cx: float, cy: float) -> str:
        """判断点位于哪个角。"""
        left = cx < margin_x
        right = cx > img_w - margin_x
        top = cy < margin_y
        bottom = cy > img_h - margin_y
        if top and left:
            return "TL"
        if top and right:
            return "TR"
        if bottom and right:
            return "BR"
        if bottom and left:
            return "BL"
        return ""

    corners: dict[str, tuple[float, float, float, float]] = {}
    for cand in candidates:
        cx, cy = cand[0], cand[1]
        corner = in_corner(cx, cy)
        if corner and corner not in corners:
            corners[corner] = cand

    if len(corners) < 4:
        return None

    return AnchorPoints(
        top_left=corners["TL"][:2],
        top_right=corners["TR"][:2],
        bottom_right=corners["BR"][:2],
        bottom_left=corners["BL"][:2],
    )


def _fallback_page_corners(binary: np.ndarray) -> AnchorPoints:
    """兜底: 未检测到锚点时，用最大外接矩形四角作为锚点。

    适用于扫描质量好、文档占满画面的场景。
    取反让黑色内容(边框)成为前景再找轮廓。
    """
    fg = cv2.bitwise_not(binary)
    contours, _ = cv2.findContours(
        fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        h, w = binary.shape
        return AnchorPoints((0, 0), (w, 0), (w, h), (0, h))

    largest = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(largest)
    return AnchorPoints(
        top_left=(x, y),
        top_right=(x + w, y),
        bottom_right=(x + w, y + h),
        bottom_left=(x, y + h),
    )


def detect_and_warp(
    binary: np.ndarray,
    bgr: np.ndarray,
    target_width: Optional[int] = None,
    target_height: Optional[int] = None,
    reference_anchors: Optional["AnchorPoints"] = None,
) -> WarpResult:
    """检测锚点并透视矫正。

    :param binary: 二值化图 (用于锚点检测)
    :param bgr: 原始 BGR 图 (矫正目标)
    :param target_width/height: 输出尺寸，默认用 settings 中的标准答题卡尺寸
    :param reference_anchors: 模板定义的标准锚点坐标(TL,TR,BR,BL)。
        若提供，矫正目标(dst)用这些坐标，使矫正后图与模板坐标系严格一致；
        若不提供，dst 用画布四角 (0,0)(tw,0)(tw,th)(0,th)。
    :return: WarpResult
    """
    tw = target_width or settings.answer_sheet_width
    th = target_height or settings.answer_sheet_height
    img_h, img_w = binary.shape

    # 尝试检测锚点
    candidates = _detect_corner_blocks(binary)
    anchors = _select_corner_anchors(candidates, img_h, img_w)
    fallback = False

    if anchors is None:
        anchors = _fallback_page_corners(binary)
        fallback = True

    src = anchors.as_array()
    # dst: 若有模板参考锚点，用它保证坐标系一致；否则用画布四角
    if reference_anchors is not None:
        dst = reference_anchors.as_array()
        # 输出尺寸以参考锚点的外接矩形为准
        out_w = int(max(dst[:, 0])) + 1
        out_h = int(max(dst[:, 1])) + 1
    else:
        dst = np.array([[0, 0], [tw, 0], [tw, th], [0, th]], dtype=np.float32)
        out_w, out_h = tw, th

    matrix = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(bgr, matrix, (out_w, out_h))

    return WarpResult(
        warped=warped, anchors=anchors, fallback_used=fallback, matrix=matrix
    )
