"""API 请求/响应模型 (Pydantic schemas)。

与 ORM 模型解耦：对外接口字段可控，避免直接暴露数据库结构。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


# ------------------------------------------------------------------
# 试卷
# ------------------------------------------------------------------
class BubbleSchema(BaseModel):
    option: str
    cx: float
    cy: float
    radius: float


class QuestionTemplateSchema(BaseModel):
    question_no: str
    correct_answer: str
    score: float = 1.0
    options: list[BubbleSchema]


class PaperCreate(BaseModel):
    name: str
    subject: str = ""
    grade: str = ""
    description: str = ""
    # 模板支持两种结构:
    #   旧: [{"question_no":...,"options":[...]}]
    #   新: {"anchors": {...}, "questions": [...]}
    template_json: list | dict = Field(default_factory=list)


class PaperOut(BaseModel):
    id: int
    name: str
    subject: str
    grade: str
    description: str
    total_score: float
    question_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# 学生答题卡
# ------------------------------------------------------------------
class SheetOut(BaseModel):
    id: int
    paper_id: int
    student_id: str
    student_name: str
    original_path: str
    processed_path: str
    status: str
    total_score: float
    needs_review: bool
    created_at: datetime
    graded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------
# 判分结果
# ------------------------------------------------------------------
class GradingResultOut(BaseModel):
    id: int
    sheet_id: int
    question_no: str
    question_type: str
    ai_score: float
    confidence: float
    detected_answer: str
    correct_answer: str
    detail: dict
    max_score: float
    needs_review: bool
    final_score: float
    review_status: str

    model_config = {"from_attributes": True}


class ReviewUpdate(BaseModel):
    """人工复核修改。"""
    final_score: float
    review_comment: str = ""
    reviewed_by: str = ""


# ------------------------------------------------------------------
# 通用响应
# ------------------------------------------------------------------
class MessageOut(BaseModel):
    message: str
    id: Optional[int] = None
