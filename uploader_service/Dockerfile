FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    libpq-dev \
    libgl1 \
    libsm6 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./requirements.txt /app/requirements.txt
COPY . /app

RUN pip install --no-cache-dir -r requirements.txt

# Command to run the FastAPI application
CMD ["uvicorn", "uploader_api:app", "--host", "0.0.0.0", "--port", "8000"]
