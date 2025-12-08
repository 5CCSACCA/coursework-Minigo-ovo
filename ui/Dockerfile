FROM python:3.10-slim

WORKDIR /app

# 安装 curl 用于健康检查
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露 Streamlit 默认端口
EXPOSE 8501

# 健康检查 (确保网页活着)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# 启动 Streamlit
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
