"""统计路由: 成绩汇总、错题统计。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import ExamPaper, GradingResult, StudentSheet

router = APIRouter(prefix="/api/stats", tags=["统计"])


@router.get("/papers/{paper_id}")
def paper_stats(paper_id: int, db: Session = Depends(get_db)):
    """某份试卷的整体统计: 参加人数、平均分、最高/最低分、错题率。"""
    paper = db.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(404, f"试卷 {paper_id} 不存在")

    sheets = (
        db.query(StudentSheet)
        .filter(StudentSheet.paper_id == paper_id)
        .filter(StudentSheet.status.in_(["graded", "reviewed"]))
        .all()
    )

    if not sheets:
        return {"paper_id": paper_id, "count": 0, "message": "暂无判分数据"}

    scores = [s.total_score for s in sheets]
    total = paper.total_score or 1

    # 错题统计: 每道题的错误率
    sheet_ids = [s.id for s in sheets]
    results = (
        db.query(GradingResult)
        .filter(GradingResult.sheet_id.in_(sheet_ids))
        .all()
    )
    error_by_q: dict[str, dict] = {}
    for r in results:
        q = error_by_q.setdefault(r.question_no, {
            "question_no": r.question_no,
            "total": 0, "wrong": 0, "score_rate": 0.0,
        })
        q["total"] += 1
        if r.final_score < r.max_score:
            q["wrong"] += 1
    for q in error_by_q.values():
        q["error_rate"] = round(q["wrong"] / q["total"], 3) if q["total"] else 0
        q["score_rate"] = round(1 - q["error_rate"], 3)

    return {
        "paper_id": paper_id,
        "paper_name": paper.name,
        "full_score": total,
        "count": len(scores),
        "average": round(sum(scores) / len(scores), 2),
        "max_score": max(scores),
        "min_score": min(scores),
        "pass_rate": round(
            sum(1 for s in scores if s >= total * 0.6) / len(scores), 3
        ),
        "excellent_rate": round(
            sum(1 for s in scores if s >= total * 0.85) / len(scores), 3
        ),
        "questions": sorted(
            error_by_q.values(), key=lambda x: -x["error_rate"]
        ),
    }
