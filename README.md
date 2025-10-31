# 5CCSACCA AI SaaS Deployment Manual
This document provides instructions for deploying the dual-modal AI SaaS application using Docker.

## 1. Build the Docker Image (One Command)
Use the following command to build the image, ensuring all dependencies and code are packaged:
```bash
sudo docker build . -t ai-saas-app
```

## 2. Run the Service (One Command)
Use the following command to run the container in the background, mapping the host's port 8000 to the container's internal API port 80:
```bash
sudo docker run -d -p 8000:80 ai-saas-app
```

## 3. API Endpoints
Once the service is deployed and running on port 8000, you can test the following endpoints:

### 3.1 Health Check (Verification)
* **Path:** `/`
* **Method:** `GET`
* **Test Command:**
```bash
curl http://localhost:8000/
```
* **Expected Output:**
```json
{"status": "ok", "message": "API is running"}
```

### 3.2 Text Generation Service (BitNet Placeholder)
* **Path:** `/api/v1/generate`
* **Method:** `POST`
* **Input:** JSON body containing a string prompt.
* **Test Command:**
```bash
curl -X POST -H "Content-Type: application/json" -d '{"prompt": "Tell me a joke."}' http://localhost:8000/api/v1/generate
```
* **Expected Output:**
```json
{"input_prompt":"Tell me a joke.","llm_response":"BitNet Placeholder: I received your prompt and processed it: 'Tell me a joke.'.","model":"BitNet(Placeholder)"}
```

### 3.3 Image Detection Service (Yolo Placeholder)

* **Path:** `/api/v1/detect`
* **Method:** `POST` (Multipart form data)
* **Input:** A file named `test_image.jpg` or similar.
* **Test Command:**
```bash
curl -X POST -F "file=@test_image.jpg" http://localhost:8000/api/v1/detect
```
* **Expected Output:**
```json
{"filename":"test.jpeg","size_bytes":5648,"status":"File received and model structure ready for inference."}
```

## Project Vision: The "Imaginer" (Contextual Narrative Generator)

The "Imaginer" is an advanced AI service designed to generate short, imaginative narratives based on visual input. Instead of simple object descriptions, the system aims to create a backstory, a cause-and-effect chain, or an absurd, creative explanation for the events captured in an image or video frame. This project serves as a demonstration of integrating objective machine vision with sophisticated language creativity.

### 1. Dual-Modality Mechanism

The system integrates two core AI services:

* **Visual Service (Yolo):** Uses a small Yolo model (e.g., YOLOv8n) not only for standard object detection but also—in later stages—to capture relational data (e.g., person *next to* a red car, cat *jumping* over a fence). The output is a structured, contextualized prompt for the LLM.
* **Narrative Service (BitNet LLM):** Receives the detailed contextual prompt from the Yolo service. It then leverages the compact power of BitNet to generate a short (approx. 100-word), highly imaginative story that explains the visual scene.

### 2. Future Implementation Plan (Phase 3 Roadmap)

The development will progress through the required stages, with a focus on building a robust, scalable, and secure narrative generation service:

| Phase 3 Stage | "Imaginer" Implementation Focus |
| :--- | :--- |
| **Stage 4 (Persistence)** | Database records every user request (e.g., input file name, initial Yolo detection results). This enables users to retrieve the *raw detected data* that formed the basis of their story. |
| **Stage 5 (Firebase)** | Store the **final generated narrative/story** (the high-value output) in Firebase Storage. Endpoints will be implemented to retrieve, update, or delete these unique stories from the user's history. |
| **Stage 6 (Messaging/Orchestration)** | **RabbitMQ** will decouple the I/O-intensive Yolo detection from the high-latency LLM generation. The Yolo service posts a detailed JSON message to the queue. A separate **Narrative Generation Service** (LLM) consumes this message and generates the creative story asynchronously, ensuring the API remains responsive. |
| **Stage 7 (Authentication)** | Implement Firebase user authentication to secure API access and manage user story history. |
| **Stage 8 (Cost Estimation)** | Provide cost calculations under the required load conditions (100 users for core services, 100,000 for the RabbitMQ/LLM service) to prove scalability and cost-efficiency. |
| **Stage 10/11 (Testing/Security)** | Implement a complete test suite for API endpoints and ensure robust security measures protect the database, API, and Firebase components. |

---
