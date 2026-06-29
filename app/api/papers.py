"""试卷管理路由: 增删改查 + 答题卡模板配置。"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.schemas import MessageOut, PaperCreate, PaperOut
from app.core.database import get_db
from app.models import ExamPaper

router = APIRouter(prefix="/api/papers", tags=["试卷"])


def _calc_total_score(template_json) -> float:
    """从模板算总分，兼容新旧结构。"""
    if isinstance(template_json, dict):
        questions = template_json.get("questions", [])
    elif isinstance(template_json, list):
        questions = template_json
    else:
        return 0.0
    return sum(float(q.get("score", 1.0)) for q in questions)


@router.post("", response_model=PaperOut, status_code=status.HTTP_201_CREATED)
def create_paper(payload: PaperCreate, db: Session = Depends(get_db)):
    """创建试卷(含答题卡模板)。"""
    paper = ExamPaper(
        name=payload.name,
        subject=payload.subject,
        grade=payload.grade,
        description=payload.description,
        template_json=payload.template_json,
        total_score=_calc_total_score(payload.template_json),
    )
    db.add(paper)
    db.commit()
    db.refresh(paper)
    return _to_out(paper)


@router.get("", response_model=list[PaperOut])
def list_papers(db: Session = Depends(get_db)):
    return [_to_out(p) for p in db.query(ExamPaper).order_by(ExamPaper.id.desc()).all()]


@router.get("/{paper_id}", response_model=PaperOut)
def get_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(404, f"试卷 {paper_id} 不存在")
    return _to_out(paper)


@router.delete("/{paper_id}", response_model=MessageOut)
def delete_paper(paper_id: int, db: Session = Depends(get_db)):
    paper = db.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(404, f"试卷 {paper_id} 不存在")
    db.delete(paper)
    db.commit()
    return MessageOut(message=f"试卷 {paper_id} 已删除", id=paper_id)


def _to_out(paper: ExamPaper) -> PaperOut:
    """ORM → PaperOut，补充题目数。"""
    return PaperOut(
        id=paper.id,
        name=paper.name,
        subject=paper.subject,
        grade=paper.grade,
        description=paper.description,
        total_score=paper.total_score,
        question_count=(
            len(paper.template_json.get("questions", []))
            if isinstance(paper.template_json, dict)
            else len(paper.template_json) if paper.template_json else 0
        ),
        created_at=paper.created_at,
    )
