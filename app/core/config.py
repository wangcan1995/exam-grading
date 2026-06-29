"""应用配置中心。

MVP 阶段从 .env 读取配置，使用 SQLite + 本地文件系统。
后续切换 PostgreSQL / MinIO 只需改环境变量，业务代码无感知。
"""
from pathlib import Path
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ===== 应用 =====
    app_name: str = "试卷阅卷打分系统"
    app_env: Literal["dev", "prod"] = "dev"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    app_debug: bool = True

    # ===== 数据库 =====
    database_url: str = "sqlite:///./exam_grading.db"

    # ===== 存储 =====
    storage_dir: str = "./storage"
    upload_dir: str = "./storage/uploads"
    processed_dir: str = "./storage/processed"

    # ===== AI: OMR 涂卡检测 =====
    omr_fill_threshold: float = 0.50       # 黑像素占比阈值
    answer_sheet_width: int = 1240         # 矫正后标准宽
    answer_sheet_height: int = 1754         # 矫正后标准高 (A4@150dpi)

    # ===== AI: 第 2 期预留 =====
    llm_api_provider: str = ""
    llm_api_key: str = ""
    llm_model: str = ""

    # ===== 对象存储 =====
    storage_type: str = "local"        # local 或 cos
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_region: str = "ap-guangzhou"
    cos_bucket: str = ""

    @model_validator(mode="after")
    def _resolve_storage_paths(self):
        """把相对存储路径转成基于项目根目录的绝对路径。

        以本文件所在位置 (app/core/config.py) 往上两级 = 项目根，
        这样无论从哪个 cwd 启动，存储位置都固定，且 _save_image 的
        relative_to 计算才正确。
        """
        project_root = Path(__file__).resolve().parent.parent.parent
        for attr in ("storage_dir", "upload_dir", "processed_dir"):
            val = getattr(self, attr)
            p = Path(val)
            if not p.is_absolute():
                setattr(self, attr, str((project_root / val).resolve()))
        return self

    @property
    def upload_path(self) -> Path:
        p = Path(self.upload_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def processed_path(self) -> Path:
        p = Path(self.processed_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def project_root(self) -> Path:
        """项目根目录，用于计算图片存储的相对路径。"""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def storage_dir_path(self) -> Path:
        """本地存储的根目录 (storage_type=local 时用)。"""
        p = Path(self.storage_dir)
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
