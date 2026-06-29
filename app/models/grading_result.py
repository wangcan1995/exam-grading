"""判分结果模型。

一道题一条记录。记录 AI 判分明细、置信度、是否需复核、最终分。
这是"AI 辅助 + 人工复核"模式的核心数据载体——AI 给出建议，人工可覆盖。
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class GradingResult(Base):
    """单题判分结果。"""
    __tablename__ = "grading_result"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sheet_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("student_sheet.id"), nullable=False, index=True
    )

    question_no: Mapped[str] = mapped_column(String(20), nullable=False)
    question_type: Mapped[str] = mapped_column(String(20), default="objective")
    # objective / fill_blank / short_answer / essay (MVP 仅 objective)

    # AI 判分
    ai_score: Mapped[float] = mapped_column(Float, default=0.0)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)            # [0,1]
    detected_answer: Mapped[str] = mapped_column(String(100), default="")   # 检测/识别内容
    correct_answer: Mapped[str] = mapped_column(String(100), default="")    # 标准答案
    detail: Mapped[dict] = mapped_column(JSON, default=dict)                # 各选项fill_ratio等明细
    max_score: Mapped[float] = mapped_column(Float, default=1.0)

    # 复核 (第3期启用，MVP 先留字段)
    needs_review: Mapped[bool] = mapped_column(default=False, index=True)
    review_status: Mapped[str] = mapped_column(String(20), default="auto")
    # auto: 自动判分 / pending: 待复核 / reviewed: 已复核
    final_score: Mapped[float] = mapped_column(Float, default=0.0)          # 最终分(复核后)
    review_comment: Mapped[str] = mapped_column(Text, default="")
    reviewed_by: Mapped[str] = mapped_column(String(50), default="")
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    sheet: Mapped["StudentSheet"] = relationship(back_populates="results")

    def __repr__(self) -> str:
        return (
            f"<GradingResult q={self.question_no} "
            f"ai={self.ai_score} final={self.final_score}>"
        )
