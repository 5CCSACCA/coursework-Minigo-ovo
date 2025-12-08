import os
import json
import asyncio
import aio_pika
import threading
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
from prometheus_client import Counter, Gauge, start_http_server

from firebase_admin import credentials, initialize_app, db as firebase_db_module
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

# --- 0. Prometheus 监控配置 (Stage 9) ---
# 启动 metrics server 在 8002 端口 (根据教授 PDF 要求)
try:
    start_http_server(8002)
    print("Uploader: Prometheus metrics server started on port 8002")
except Exception as e:
    print(f"Uploader: Failed to start metrics server: {e}")

# 定义指标
IMAGES_UPLOADED = Counter('uploader_images_uploaded_total', 'Total images uploaded')
RABBITMQ_CONNECTED = Gauge('uploader_rabbitmq_connected', 'RabbitMQ connection status (1=Connected, 0=Disconnected)')

# --- 1. 配置加载 ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
POSTGRES_DB_URL = os.getenv("POSTGRES_DB_URL") # 确保 .env 里有这个
# 注意：Uploader 不再需要 GEMINI_API_KEY，因为是 Worker 在用
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE")

# --- 2. 数据库设置 (PostgreSQL) ---
Base = declarative_base()
class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, nullable=True)
    text_prompt = Column(String, nullable=False)
    llm_description = Column(String, nullable=True) # 初始为空，由 Worker 填充
    model_used = Column(String, default="gemini-2.5-flash") # 默认值
    timestamp = Column(DateTime, default=datetime.utcnow)

# 初始化 DB
engine = None
SessionLocal = None
try:
    engine = create_engine(POSTGRES_DB_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    print("Uploader: Database initialized.")
except Exception as e:
    print(f"FATAL: DB Init failed: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- 3. Firebase 初始化 (仅用于读取/更新/删除结果) ---
firebase_db = None
try:
    if FIREBASE_CREDENTIALS_FILE and os.path.exists(FIREBASE_CREDENTIALS_FILE):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
        initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
        firebase_db = firebase_db_module
        print("Uploader: Firebase initialized.")
    else:
        print("WARNING: Firebase credentials not found.")
except Exception as e:
    print(f"FATAL: Firebase init failed: {e}")

# --- FastAPI App ---
app = FastAPI()

class InputTask(BaseModel):
    image_url: str = None
    text_prompt: str = None

# --- 4. 核心逻辑：发送到 RabbitMQ ---
async def send_to_rabbitmq(message: dict):
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        async with connection:
            channel = await connection.channel()
            queue = await channel.declare_queue("task_queue", durable=True)
            
            await channel.default_exchange.publish(
                aio_pika.Message(
                    body=json.dumps(message).encode(),
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT
                ),
                routing_key=queue.name,
            )
        # ⚡ 监控埋点：连接成功
        RABBITMQ_CONNECTED.set(1)
        return True
    except Exception as e:
        # ⚡ 监控埋点：连接失败
        RABBITMQ_CONNECTED.set(0)
        raise e

@app.post("/submit_task")
async def submit_task(task: InputTask, db: Session = Depends(get_db)):
    """接收请求 -> 存DB占位 -> 发送给 Worker (异步)"""
    if not task.image_url and not task.text_prompt:
        raise HTTPException(status_code=400, detail="Provide image_url or text_prompt")

    final_prompt = task.text_prompt if task.text_prompt else "Describe this image..."

    # 1. 先在 Postgres 占个位 (状态: Pending)
    log_entry = RequestLog(
        image_url=task.image_url,
        text_prompt=final_prompt,
        llm_description="[Processing...]", # 标记为处理中
    )
    db.add(log_entry)
    db.commit()
    db.refresh(log_entry)
    
    # 2. 打包任务
    task_payload = {
        "record_id": log_entry.id,
        "image_url": task.image_url,
        "text_prompt": final_prompt
    }

    # 3. 发送给 Worker
    try:
        await send_to_rabbitmq(task_payload)
        IMAGES_UPLOADED.inc()
        return {
            "status": "queued", # 状态变成了已排队
            "record_id": log_entry.id,
            "message": "Task sent to Worker. Check results later via GET /firebase/{id}"
        }
    except Exception as e:
        print(f"RabbitMQ Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to queue task")

# --- 5. CRUD Endpoints (用于查看 Worker 的劳动成果) ---

@app.get("/firebase/{record_id}")
def get_firebase_result(record_id: int):
    if not firebase_db: raise HTTPException(503, "Firebase not ready")
    firebase_key = f"id_{record_id}"
    result = firebase_db.reference(f'results/{firebase_key}').get()
    if not result:
        raise HTTPException(404, "Result not found (Worker might be still processing)")
    return {"status": "success", "result": result}

@app.put("/firebase/{record_id}")
def update_firebase_result(record_id: int, new_description: str):
    if not firebase_db: raise HTTPException(503, "Firebase not ready")
    firebase_key = f"id_{record_id}"
    ref = firebase_db.reference(f'results/{firebase_key}')
    if not ref.get(): raise HTTPException(404, "Record not found")
    ref.update({"description": new_description})
    return {"status": "success", "message": "Updated"}

@app.delete("/firebase/{record_id}")
def delete_firebase_result(record_id: int):
    if not firebase_db: raise HTTPException(503, "Firebase not ready")
    firebase_key = f"id_{record_id}"
    firebase_db.reference(f'results/{firebase_key}').delete()
    return {"status": "success", "message": "Deleted"}

@app.get("/health")
def health():
    return {"status": "ok", "mode": "Async/Producer"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
