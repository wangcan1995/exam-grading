"""扫描上传服务。

负责接收上传的试卷图片，保存到 storage，创建 StudentSheet 记录。
"""
import uuid
from pathlib import Path

from fastapi import UploadFile
from loguru import logger

from app.core.config import settings
from app.models import StudentSheet

ALLOWED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


async def save_upload(
    upload_file: UploadFile, paper_id: int
) -> tuple[str, str]:
    """保存上传文件，返回 (存储 key, 原始文件名)。

    本地模式: 存到 storage/uploads/{uuid}.ext，返回相对项目根路径
    COS 模式: 存到 COS，返回相对 key (前端通过 /api/images 访问)
    """
    ext = Path(upload_file.filename or "").suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        raise ValueError(
            f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_IMAGE_EXTS)}"
        )

    saved_name = f"{uuid.uuid4().hex}{ext}"
    key = f"storage/uploads/{saved_name}"

    content = await upload_file.read()
    from app.core.storage import get_storage
    get_storage().save_bytes(content, key)
    logger.info(f"文件已保存: {key} ({len(content)} bytes)")
    return key, upload_file.filename or saved_name


def create_sheet(
    db, paper_id: int, original_path: str,
    student_id: str = "", student_name: str = "",
) -> StudentSheet:
    """创建一条 StudentSheet 记录。"""
    sheet = StudentSheet(
        paper_id=paper_id,
        original_path=original_path,
        student_id=student_id,
        student_name=student_name,
        status="pending",
    )
    db.add(sheet)
    db.commit()
    db.refresh(sheet)
    logger.info(f"创建答题卡记录 sheet={sheet.id} paper={paper_id}")
    return sheet
