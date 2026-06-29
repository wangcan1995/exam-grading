"""试卷 + 答题卡模板模型。

答题卡模板存为 JSON: 包含每道客观题的选项坐标(基于矫正后标准尺寸)。
这是 OMR 检测的"图纸"——告诉系统每个选项圆圈在哪。
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ExamPaper(Base):
    """试卷。

    一张试卷 = 一份答题卡模板 + 标准答案。
    后续可设计可视化编辑器让老师拖拽生成 template_json，MVP 先手动填写。
    """
    __tablename__ = "exam_paper"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)         # "2025期中数学"
    subject: Mapped[str] = mapped_column(String(50), default="")           # 学科
    grade: Mapped[str] = mapped_column(String(50), default="")             # 年级
    description: Mapped[str] = mapped_column(Text, default="")

    # 答题卡模板: [{question_no, correct_answer, score, options:[{option,cx,cy,radius}]}]
    template_json: Mapped[dict] = mapped_column(JSON, default=list)

    total_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sheets: Mapped[list["StudentSheet"]] = relationship(
        back_populates="paper", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<ExamPaper {self.id} {self.name}>"
