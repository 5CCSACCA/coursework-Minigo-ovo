FROM python:3.10-slim

# ⚡ 安装 PostgreSQL 客户端和图像处理所需的系统库
RUN apt-get update && apt-get install -y \
    libpq-dev \
    libgl1 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 复制依赖清单
COPY ./requirements.txt /app/requirements.txt

# ⚡ 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制当前目录下的所有代码 (包括 worker_consumer.py) 到容器
COPY . /app

# 启动 Worker 消费者进程
CMD ["python", "worker_consumer.py"]
