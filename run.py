"""开发服务器启动入口。

用法: python run.py
生产环境用: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
"""
import uvicorn

from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.app_debug,
    )
