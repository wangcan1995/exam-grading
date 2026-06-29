# 后端镜像: Python + OpenCV + FastAPI
FROM python:3.11-slim

# OpenCV 系统依赖 (使用阿里云镜像加速 apt)
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources || true \
    && apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先装依赖 (利用 Docker 层缓存)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 再拷代码
COPY . .

# 建存储目录
RUN mkdir -p storage/uploads storage/processed

EXPOSE 8000

# 生产用 gunicorn 多 worker (uvicorn worker class)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
