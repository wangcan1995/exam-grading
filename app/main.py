"""FastAPI 应用入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api import papers, review, scan, stat
from app.core.config import settings
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期: 启动时建表。"""
    logger.info(f"启动 {settings.app_name} (env={settings.app_env})")
    init_db()
    logger.info("数据库表已就绪")
    yield
    logger.info("应用关闭")


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="试卷扫描 + AI 辅助阅卷打分系统 (MVP)",
    lifespan=lifespan,
)

# CORS: 允许前端跨域 (MVP 前后端分离开发)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.app_env == "dev" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(papers.router)
app.include_router(scan.router)
app.include_router(review.router)
app.include_router(stat.router)


@app.get("/", tags=["健康检查"])
def root():
    return {
        "app": settings.app_name,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["健康检查"])
def health():
    return {"status": "ok"}
