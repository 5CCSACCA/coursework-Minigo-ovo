# Review: This dockerfile is well-structured for deploying a FastAPI application. Please, consider start creating your docker compose file.
FROM python:3.10-slim
WORKDIR /app
RUN apt-get update && \
    apt-get install -y libgl1 libglib2.0-0 && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
