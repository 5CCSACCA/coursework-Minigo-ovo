# 5CCSACCA AI SaaS Deployment Manual
This document provides instructions for deploying the dual-modal AI SaaS application using Docker.

##1. Build the Docker Image (One Command)
Use the following command to build the image, ensuring all dependencies and code are packaged:
```bash
sudo docker build . -t ai-saas-app
```

##2. Run the Service (One Command)
Use the following command to run the container in the background, mapping the host's port 8000 to the container's internal API port 80:
```bash
sudo docker run -d -p 8000:80 ai-saas-app
```

##3. API Endpoints
Once the service is deployed and running on port 8000, you can test the following endpoints:

### 3.1 Health Check (Verification)
* **Path:** `/`
* **Method:** `GET`
* **Expected Output:** `{"status": "ok", "message": "API is running"}`
* **Test Command:** ```bash
    curl http://localhost:8000/
    ```

### 3.2 Text Generation Service (BitNet Placeholder)
* **Path:** `/api/v1/generate`
* **Method:** `POST`
* **Input:** JSON body containing a string prompt.
* **Expected Output:** A JSON object summarizing the input and the placeholder LLM response.
* **Test Command:** ```bash
    curl -X POST -H "Content-Type: application/json" -d '{"prompt": "Hello BitNet"}' http://localhost:8000/api/v1/generate
    ```

### 3.3 Image Detection Service (Yolo Placeholder)
* **Path:** `/api/v1/detect`
* **Method:** `POST`
* **Input:** Multipart form data containing an image file.
* **Expected Output:** A JSON object summarizing the placeholder detection results.
* **Note:** This endpoint is configured to receive and process files but currently returns placeholder data for this initial submission.
