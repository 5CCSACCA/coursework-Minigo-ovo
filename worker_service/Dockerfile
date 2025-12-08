FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    libgl1 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

CMD ["python", "worker_consumer.py"]
