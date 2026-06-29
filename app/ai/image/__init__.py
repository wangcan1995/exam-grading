"""AI 图像处理子包统一导出。"""
from app.ai.image.anchor import (
    AnchorPoints,
    WarpResult,
    detect_and_warp,
)
from app.ai.image.omr import (
    BubbleRegion,
    BubbleResult,
    QuestionGradeResult,
    QuestionLayout,
    detect_marked_options,
    grade_question,
)
from app.ai.image.preprocess import (
    adaptive_threshold,
    deskew,
    detect_skew_angle,
    denoise,
    load_image,
    preprocess,
    preprocess_image,
    to_gray,
)

__all__ = [
    # preprocess
    "load_image", "to_gray", "denoise", "adaptive_threshold",
    "detect_skew_angle", "deskew", "preprocess", "preprocess_image",
    # anchor
    "AnchorPoints", "WarpResult", "detect_and_warp",
    # omr
    "BubbleRegion", "QuestionLayout", "BubbleResult",
    "QuestionGradeResult", "detect_marked_options", "grade_question",
]
