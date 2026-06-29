"""图像预处理模块。

流水线: 读取 → 灰度 → 去噪 → 自适应二值化 → 倾斜矫正
所有函数接收/返回 numpy 数组 (BGR 或灰度)，纯函数无副作用，便于测试。
"""
from pathlib import Path
from typing import Optional

import cv2
import numpy as np


# ------------------------------------------------------------------
# 读取与基础转换
# ------------------------------------------------------------------
def load_image(path: str | Path) -> np.ndarray:
    """读取图片。OpenCV 默认 BGR。

    注意: cv2.imread 对中文路径会返回 None，用 np.fromfile + imdecode 兜底。
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"图片不存在: {path}")

    # 兼容中文路径
    data = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"无法解码图片 (可能格式损坏): {path}")
    return img


def to_gray(img: np.ndarray) -> np.ndarray:
    """BGR → 灰度。已为灰度则原样返回。"""
    if len(img.shape) == 2:
        return img
    return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)


def denoise(img: np.ndarray) -> np.ndarray:
    """去噪。轻度 bilateralFilter 保边缘，比 medianBlur 更适合答题卡线条保留。"""
    return cv2.bilateralFilter(img, d=5, sigmaColor=75, sigmaSpace=75)


def adaptive_threshold(gray: np.ndarray) -> np.ndarray:
    """二值化。

    用 Otsu 自适应全局阈值。对高对比度答题卡(白纸黑字/涂卡)非常稳，
    能精确区分涂卡(黑)与背景(白)。
    对严重光照不均的真实扫描件，可改用 cv2.adaptiveThreshold
    (ADAPTIVE_THRESH_GAUSSIAN_C) 分块处理，但需谨慎调 C 值，
    C 过大会把涂卡反转。

    输出约定: 背景=白(255)，墨迹/涂卡=黑(0)。OMR 据此统计黑色占比。
    """
    _, binary = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
    )
    return binary


# ------------------------------------------------------------------
# 倾斜矫正
# ------------------------------------------------------------------
def detect_skew_angle(binary: np.ndarray, angle_limit: float = 15.0) -> float:
    """通过最小外接矩形检测整体倾斜角度。

    答题卡是大面积矩形文档(外边框)，外接矩形主方向即文档方向。
    输入二值图约定: 背景=白，墨迹/边框=黑；此处取反让黑色物体成为前景。
    """
    # 取反: 让黑色边框/锚点成为白色前景，findContours 才能找到
    fg = cv2.bitwise_not(binary)
    contours, _ = cv2.findContours(
        fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
    )
    if not contours:
        return 0.0

    # 取面积最大的轮廓 (应该是文档边框)
    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < 1000:  # 太小，不可靠
        return 0.0

    rect = cv2.minAreaRect(largest)
    angle = rect[-1]

    # minAreaRect 角度范围 [-90, 0)，需要规整化
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90

    # 超过限制视为异常，不矫正 (避免把正常图转 90°)
    if abs(angle) > angle_limit:
        return 0.0
    return angle


def deskew(img: np.ndarray, angle: Optional[float] = None) -> np.ndarray:
    """旋转图片矫正倾斜。

    :param angle: 已知角度则直接用；否则自动检测。
    """
    if angle is None:
        gray = to_gray(img) if len(img.shape) == 3 else img
        binary = adaptive_threshold(gray)
        angle = detect_skew_angle(binary)

    if abs(angle) < 0.1:  # 几乎无倾斜
        return img

    h, w = img.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    return cv2.warpAffine(
        img, matrix, (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )


# ------------------------------------------------------------------
# 完整预处理流水线
# ------------------------------------------------------------------
def preprocess_image(img: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """完整预处理流水线 (从内存图像数组开始)。

    :param img: BGR 图像 (numpy 数组)
    :return: (原始BGR, 矫正后BGR, 二值化图)
    """
    gray = to_gray(img)
    denoised = denoise(gray)

    # 先检测角度，对原图旋转，再重新二值化 (避免二值化噪声影响角度检测)
    angle = detect_skew_angle(adaptive_threshold(denoised))
    deskewed_bgr = deskew(img, angle) if abs(angle) >= 0.1 else img

    # 对矫正后的图重新做灰度+二值化，供后续锚点检测/OMR 使用
    final_gray = to_gray(deskewed_bgr)
    final_binary = adaptive_threshold(denoise(final_gray))

    return img, deskewed_bgr, final_binary


def preprocess(image_path: str | Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """完整预处理流水线 (从文件路径读取)。

    :return: (原始BGR, 矫正后BGR, 二值化图)
    """
    img = load_image(image_path)
    return preprocess_image(img)
