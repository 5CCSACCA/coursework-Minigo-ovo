import asyncio
import os
import json
import io
import datetime
import time # ⚡ 新增：用于计算时间
import aio_pika
import requests
from PIL import Image
from google import genai
from google.genai import types
from firebase_admin import credentials, initialize_app, db as firebase_db_module
from sqlalchemy import create_engine, Column, Integer, String, DateTime, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
# ⚡ 新增：Prometheus 客户端
from prometheus_client import Counter, Histogram, Gauge, start_http_server

# --- 0. Prometheus 监控配置 (Stage 9) ---
try:
    start_http_server(8003)
    print("Worker: Prometheus metrics server started on port 8003")
except Exception as e:
    print(f"Worker: Failed to start metrics server: {e}")

# 定义指标
IMAGES_PROCESSED = Counter('worker_images_processed_total', 'Total images processed by Worker')
INFERENCE_TIME = Histogram('worker_inference_seconds', 'Time taken for AI inference')
RABBITMQ_CONNECTED = Gauge('worker_rabbitmq_connected', 'RabbitMQ connection status (1=Connected, 0=Disconnected)')

# --- 1. 配置加载 ---
RABBITMQ_URL = os.getenv("RABBITMQ_URL", "amqp://guest:guest@rabbitmq/")
POSTGRES_DB_URL = os.getenv("POSTGRES_DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
FIREBASE_DATABASE_URL = os.getenv("FIREBASE_DATABASE_URL")
FIREBASE_CREDENTIALS_FILE = os.getenv("FIREBASE_CREDENTIALS_FILE", "/app/firebase-credentials.json")

# --- 2. 数据库设置 (PostgreSQL) ---
Base = declarative_base()
class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True, index=True)
    image_url = Column(String, nullable=True)
    text_prompt = Column(String, nullable=False)
    llm_description = Column(String, nullable=True) 
    model_used = Column(String, default=GEMINI_MODEL)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)

engine = create_engine(POSTGRES_DB_URL)
SessionLocal = sessionmaker(bind=engine)

# --- 3. Firebase 初始化 ---
firebase_ref = None
try:
    if FIREBASE_CREDENTIALS_FILE and os.path.exists(FIREBASE_CREDENTIALS_FILE):
        cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
        initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
        firebase_ref = firebase_db_module
        print("Worker: Firebase initialized successfully.")
    else:
        print("Worker: Firebase credentials not found. Skipping Firebase.")
except Exception as e:
    print(f"Worker: Firebase init failed: {e}")

# --- 4. Gemini 初始化 ---
client = None
if GEMINI_API_KEY:
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        print("Worker: Gemini client initialized.")
    except Exception as e:
        print(f"Worker: Gemini init failed: {e}")

# --- 5. 核心处理函数 ---
def process_task(task_data):
    """同步执行耗时任务：下载 -> Gemini -> DB更新 -> Firebase"""
    start_time = time.time() # ⚡ 监控埋点：开始计时
    
    record_id = task_data.get("record_id")
    image_url = task_data.get("image_url")
    text_prompt = task_data.get("text_prompt")
    
    print(f"Worker: Processing Task ID {record_id}...")

    # A. 准备 Gemini 输入
    contents = []
    if image_url:
        try:
            # 下载图片
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(image_url, stream=True, timeout=15, headers=headers)
            resp.raise_for_status()
            
            # 转换图片
            image = Image.open(io.BytesIO(resp.content))
            mime_type = Image.MIME.get(image.format) if image.format else 'image/jpeg'
            image_part = types.Part.from_bytes(data=resp.content, mime_type=mime_type)
            contents.append(image_part)
        except Exception as e:
            print(f"Worker Error: Image download failed: {e}")
            return # 停止处理

    contents.append(text_prompt)

    # B. 调用 Gemini
    try:
        response = client.models.generate_content(model=GEMINI_MODEL, contents=contents)
        llm_result = response.text
    except Exception as e:
        print(f"Worker Error: Gemini call failed: {e}")
        llm_result = f"Error generating description: {e}"

    # C. 更新 PostgreSQL (填入结果)
    session = SessionLocal()
    try:
        record = session.query(RequestLog).filter(RequestLog.id == record_id).first()
        if record:
            record.llm_description = llm_result
            session.commit()
            print(f"Worker: PostgreSQL ID {record_id} updated.")
    except Exception as e:
        print(f"Worker Error: DB Update failed: {e}")
    finally:
        session.close()

    # D. 写入 Firebase (带前缀)
    if firebase_ref:
        try:
            firebase_key = f"id_{record_id}"
            data = {
                "postgres_id": record_id,
                "image_url": image_url,
                "text_prompt": text_prompt,
                "description": llm_result,
                "processed_at": datetime.datetime.utcnow().isoformat()
            }
            firebase_ref.reference(f'results/{firebase_key}').set(data)
            print(f"Worker: Firebase key {firebase_key} written.")
        except Exception as e:
            print(f"Worker Error: Firebase write failed: {e}")
            
    # ⚡ 监控埋点：更新指标
    IMAGES_PROCESSED.inc() # 计数器 +1
    duration = time.time() - start_time
    INFERENCE_TIME.observe(duration) # 记录处理时长

# --- 6. RabbitMQ 监听主循环 ---
async def main():
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)
        # ⚡ 监控埋点：连接成功
        RABBITMQ_CONNECTED.set(1) 
    except Exception as e:
        # ⚡ 监控埋点：连接失败
        RABBITMQ_CONNECTED.set(0)
        raise e

    async with connection:
        channel = await connection.channel()
        queue = await channel.declare_queue("task_queue", durable=True)

        print("Worker: Waiting for messages...")
        
        async with queue.iterator() as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    try:
                        task_data = json.loads(message.body.decode())
                        await asyncio.to_thread(process_task, task_data)
                    except Exception as e:
                        print(f"Worker: Message processing error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Worker stopped.")
