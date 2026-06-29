"""数据库基础设施。

MVP 用 SQLite，业务层通过依赖注入拿到 Session，切换数据库只改 config.database_url。
"""
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


# SQLite 需要 check_same_thread=False 才能在 FastAPI 多线程中使用
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    echo=settings.app_debug and settings.app_env == "dev",
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有 ORM 模型的基类。"""
    pass


def get_db() -> Generator[Session, None, None]:
    """FastAPI 依赖：每个请求一个 Session，请求结束自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """建表。MVP 用 create_all 直接建，生产环境应走 Alembic 迁移。"""
    # 必须先 import 让 ORM 模型注册到 metadata
    from app.models import exam_paper, grading_result, student_sheet  # noqa: F401

    Base.metadata.create_all(bind=engine)
