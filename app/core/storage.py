"""对象存储抽象层 — 统一"本地存储"和"腾讯云 COS"两种模式。

设计: 提供统一的 save_bytes / save_image / get_bytes / file_exists 接口,
业务层不感知数据存在哪。通过 settings.STORAGE_TYPE 切换。

模式切换:
- STORAGE_TYPE=local  图片存服务器本地 (默认,零配置)
- STORAGE_TYPE=cos    图片存腾讯云 COS (需填 COS_SECRET_ID/KEY/BUCKET)

COS SDK: pip install cos-python-sdk-v5
"""
import io
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from loguru import logger

from app.core.config import settings


class StorageBackend(ABC):
    """存储后端抽象基类。"""

    @abstractmethod
    def save_bytes(self, data: bytes, key: str) -> str:
        """保存字节数据，返回访问路径(key)。"""

    @abstractmethod
    def save_image(self, img: np.ndarray, key: str) -> str:
        """保存 OpenCV 图像 (numpy 数组) 为 PNG，返回 key。"""

    @abstractmethod
    def get_bytes(self, key: str) -> Optional[bytes]:
        """读取数据，不存在返回 None。"""

    @abstractmethod
    def read_image(self, key: str) -> Optional[np.ndarray]:
        """读取为 OpenCV 图像，失败返回 None。"""

    @abstractmethod
    def file_exists(self, key: str) -> bool:
        """文件是否存在。"""

    @abstractmethod
    def access_url(self, key: str) -> str:
        """获取可访问的 URL（本地返回相对路径，COS 返回完整 URL）。"""


# ============================================================
# 本地存储
# ============================================================
class LocalStorage(StorageBackend):
    """本地文件系统存储 (默认)。

    key 约定为相对项目根的路径 (如 'storage/processed/xxx.png')，
    与历史数据兼容；本地存储时直接拼到项目根下。
    """

    def _full_path(self, key: str) -> Path:
        """key → 本地绝对路径。key 是相对项目根的路径。"""
        p = Path(key)
        if not p.is_absolute():
            p = settings.project_root / key
        return p

    def save_bytes(self, data: bytes, key: str) -> str:
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def save_image(self, img: np.ndarray, key: str) -> str:
        path = self._full_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            raise RuntimeError(f"图片编码失败: {key}")
        buf.tofile(str(path))   # tofile 兼容中文路径
        return key

    def get_bytes(self, key: str) -> Optional[bytes]:
        path = self._full_path(key)
        if not path.exists():
            return None
        return path.read_bytes()

    def read_image(self, key: str) -> Optional[np.ndarray]:
        path = self._full_path(key)
        if not path.exists():
            return None
        data = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(data, cv2.IMREAD_COLOR)

    def file_exists(self, key: str) -> bool:
        return self._full_path(key).exists()

    def access_url(self, key: str) -> str:
        # 本地存储返回相对路径，前端通过 /api/images/{sheet}/{kind} 访问
        return key


# ============================================================
# 腾讯云 COS 存储
# ============================================================
class CosStorage(StorageBackend):
    """腾讯云 COS 对象存储。

    需在 .env 配置:
        COS_SECRET_ID, COS_SECRET_KEY, COS_REGION, COS_BUCKET
    """

    _client = None  # 懒加载,全局复用

    def __init__(self):
        if CosStorage._client is None:
            self._init_client()

    def _init_client(self):
        """初始化 COS 客户端。"""
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as e:
            raise RuntimeError(
                "COS SDK 未安装,请运行: pip install cos-python-sdk-v5"
            ) from e

        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
            Scheme="https",
        )
        CosStorage._client = CosS3Client(config)
        logger.info(
            f"COS 客户端已初始化: bucket={settings.cos_bucket} "
            f"region={settings.cos_region}"
        )

    def _full_key(self, key: str) -> str:
        """本地 key → COS 对象键 (去掉前导斜杠)。"""
        return key.lstrip("/")

    def save_bytes(self, data: bytes, key: str) -> str:
        cos_key = self._full_key(key)
        self._client.put_object(
            Bucket=settings.cos_bucket,
            Body=data,
            Key=cos_key,
        )
        logger.debug(f"COS 上传: {cos_key} ({len(data)} bytes)")
        return key

    def save_image(self, img: np.ndarray, key: str) -> str:
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            raise RuntimeError(f"图片编码失败: {key}")
        return self.save_bytes(buf.tobytes(), key)

    def get_bytes(self, key: str) -> Optional[bytes]:
        try:
            resp = self._client.get_object(
                Bucket=settings.cos_bucket, Key=self._full_key(key)
            )
            return resp["Body"].get_raw_stream().read()
        except Exception:
            return None

    def read_image(self, key: str) -> Optional[np.ndarray]:
        data = self.get_bytes(key)
        if data is None:
            return None
        arr = np.frombuffer(data, dtype=np.uint8)
        return cv2.imdecode(arr, cv2.IMREAD_COLOR)

    def file_exists(self, key: str) -> bool:
        try:
            self._client.head_object(
                Bucket=settings.cos_bucket, Key=self._full_key(key)
            )
            return True
        except Exception:
            return False

    def access_url(self, key: str) -> str:
        """COS 对象的公网访问 URL。"""
        return (
            f"https://{settings.cos_bucket}.cos.{settings.cos_region}."
            f"myqcloud.com/{self._full_key(key)}"
        )


# ============================================================
# 工厂函数 — 根据 settings.STORAGE_TYPE 返回对应后端
# ============================================================
_storage: Optional[StorageBackend] = None


def get_storage() -> StorageBackend:
    """获取存储后端单例。全局复用,避免重复初始化。"""
    global _storage
    if _storage is None:
        stype = settings.storage_type.lower()
        if stype == "cos":
            logger.info("启用 COS 对象存储")
            _storage = CosStorage()
        else:
            logger.info("启用本地文件存储")
            _storage = LocalStorage()
    return _storage


def reset_storage() -> None:
    """重置单例 (改配置后用,主要给测试用)。"""
    global _storage
    _storage = None
