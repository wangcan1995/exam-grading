"""学生答题卡模型。

每扫描一张试卷 = 一条 StudentSheet 记录。
存原始图、矫正后图路径，以及该卷的判分汇总。
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class StudentSheet(Base):
    """学生答题卡(一张扫描的试卷)。"""
    __tablename__ = "student_sheet"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    paper_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("exam_paper.id"), nullable=False, index=True
    )

    student_id: Mapped[str] = mapped_column(String(50), default="")         # 学号(第4期条码识别)
    student_name: Mapped[str] = mapped_column(String(50), default="")

    # 文件路径 (相对 storage 目录)
    original_path: Mapped[str] = mapped_column(String(500), nullable=False)
    processed_path: Mapped[str] = mapped_column(String(500), default="")    # 矫正后图

    # 判分状态
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)
    # pending: 待判分 / grading: 判分中 / graded: 已判分 / reviewed: 已复核

    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    needs_review: Mapped[bool] = mapped_column(default=False, index=True)   # 是否有题需复核

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    paper: Mapped["ExamPaper"] = relationship(back_populates="sheets")
    results: Mapped[list["GradingResult"]] = relationship(
        back_populates="sheet", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<StudentSheet {self.id} paper={self.paper_id} score={self.total_score}>"
