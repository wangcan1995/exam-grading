"""复核路由。

MVP 提供基础改分接口；完整复核流转(任务分配/状态机/WebSocket)在第 3 期实现。
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import GradingResultOut, ReviewUpdate
from app.core.database import get_db
from app.models import GradingResult, StudentSheet

router = APIRouter(prefix="/api/review", tags=["复核"])


@router.get("/pending", response_model=list[GradingResultOut])
def list_pending(db: Session = Depends(get_db)):
    """列出所有待复核的题目(跨所有答题卡)。"""
    return (
        db.query(GradingResult)
        .filter(GradingResult.needs_review == True)      # noqa: E712
        .filter(GradingResult.review_status == "pending")
        .order_by(GradingResult.id)
        .all()
    )


@router.put("/{result_id}", response_model=GradingResultOut)
def review_result(
    result_id: int, payload: ReviewUpdate, db: Session = Depends(get_db)
):
    """人工复核单题: 覆盖最终分 + 批注。"""
    result = db.get(GradingResult, result_id)
    if not result:
        raise HTTPException(404, f"判分结果 {result_id} 不存在")

    result.final_score = payload.final_score
    result.review_comment = payload.review_comment
    result.reviewed_by = payload.reviewed_by or "anonymous"
    result.reviewed_at = datetime.utcnow()
    result.review_status = "reviewed"

    # 重新汇总所在答题卡的总分(以 final_score 为准)
    sheet = db.get(StudentSheet, result.sheet_id)
    if sheet:
        all_results = (
            db.query(GradingResult)
            .filter(GradingResult.sheet_id == sheet.id)
            .all()
        )
        sheet.total_score = round(sum(r.final_score for r in all_results), 2)
        sheet.needs_review = any(r.review_status == "pending" for r in all_results)
        if not sheet.needs_review:
            sheet.status = "reviewed"

    db.commit()
    db.refresh(result)
    return result
