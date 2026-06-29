"""扫描上传 + 判分路由 — MVP 核心接口。"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.schemas import GradingResultOut, SheetOut
from app.core.config import settings
from app.core.database import get_db
from app.models import ExamPaper, GradingResult, StudentSheet
from app.services.grading_dispatcher import grade_student_sheet
from app.services.scan_service import create_sheet, save_upload

router = APIRouter(prefix="/api", tags=["扫描判分"])


@router.post("/scan/upload", response_model=SheetOut)
async def upload_and_grade(
    paper_id: int = Form(...),
    file: UploadFile = File(...),
    student_id: str = Form(""),
    student_name: str = Form(""),
    db: Session = Depends(get_db),
):
    """上传一张答题卡并立即判分。

    MVP 为同步判分(客观题很快)。生产环境应改为 Celery 异步 + WebSocket 推送进度。
    """
    # 校验试卷存在
    paper = db.get(ExamPaper, paper_id)
    if not paper:
        raise HTTPException(404, f"试卷 {paper_id} 不存在")
    if not paper.template_json:
        raise HTTPException(400, f"试卷 {paper_id} 未配置答题卡模板，无法判分")

    # 保存文件
    try:
        saved_path, _ = await save_upload(file, paper_id)
    except ValueError as e:
        raise HTTPException(400, str(e))

    # 创建记录
    sheet = create_sheet(db, paper_id, saved_path, student_id, student_name)

    # 同步判分
    try:
        sheet = grade_student_sheet(db, sheet, paper)
    except Exception as e:
        sheet.status = "error"
        db.commit()
        raise HTTPException(500, f"判分失败: {e}") from e

    return sheet


@router.get("/sheets", response_model=list[SheetOut])
def list_sheets(paper_id: int | None = None, db: Session = Depends(get_db)):
    """列出答题卡(可按试卷筛选)。"""
    q = db.query(StudentSheet)
    if paper_id is not None:
        q = q.filter(StudentSheet.paper_id == paper_id)
    return q.order_by(StudentSheet.id.desc()).all()


@router.get("/sheets/{sheet_id}", response_model=SheetOut)
def get_sheet(sheet_id: int, db: Session = Depends(get_db)):
    sheet = db.get(StudentSheet, sheet_id)
    if not sheet:
        raise HTTPException(404, f"答题卡 {sheet_id} 不存在")
    return sheet


@router.get("/sheets/{sheet_id}/results", response_model=list[GradingResultOut])
def get_sheet_results(sheet_id: int, db: Session = Depends(get_db)):
    """获取一张答题卡的逐题判分明细。"""
    if not db.get(StudentSheet, sheet_id):
        raise HTTPException(404, f"答题卡 {sheet_id} 不存在")
    return (
        db.query(GradingResult)
        .filter(GradingResult.sheet_id == sheet_id)
        .order_by(GradingResult.question_no)
        .all()
    )


@router.get("/images/{sheet_id}/{kind}")
def get_image(sheet_id: int, kind: str, db: Session = Depends(get_db)):
    """获取答题卡图片。kind: original / processed。"""
    if kind not in ("original", "processed"):
        raise HTTPException(400, "kind 必须是 original 或 processed")

    sheet = db.get(StudentSheet, sheet_id)
    if not sheet:
        raise HTTPException(404, f"答题卡 {sheet_id} 不存在")

    rel = sheet.original_path if kind == "original" else sheet.processed_path
    if not rel:
        raise HTTPException(404, f"该答题卡没有 {kind} 图片")

    path = Path(rel)
    if not path.is_absolute():
        path = settings.project_root / rel
    if not path.exists():
        raise HTTPException(404, "图片文件不存在")

    return FileResponse(str(path))
