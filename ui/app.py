import streamlit as st
import requests
import time
import os
import json

# --- Configuration ---
# API URL access within Docker network
API_URL = os.getenv("API_URL", "http://uploader:8000")

# External URLs for the buttons (accessed from the browser)
PROM_URL = "http://localhost:9090"
GRAFANA_URL = "http://localhost:3000"

FIREBASE_CONSOLE_URL = "https://console.firebase.google.com/" 

st.set_page_config(page_title="AI SaaS Dashboard", layout="wide")

# --- Sidebar: Navigation and Testing ---
with st.sidebar:
    st.header("Quick Links")
    st.link_button("Go to Grafana", GRAFANA_URL)
    st.link_button("Go to Prometheus", PROM_URL)
    st.link_button("Go to Firebase Console", FIREBASE_CONSOLE_URL)
    
    st.divider()
    st.header("System Test")
    if st.button("Run System Test"):
        with st.status("Running full system test...", expanded=True) as status:
            try:
                # 1. Submit Task
                st.write("1. Submitting test task...")
                test_img = "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg"
                payload = {"image_url": test_img}
                
                res = requests.post(f"{API_URL}/submit_task", json=payload)
                if res.status_code != 200:
                    status.update(label="Test Failed: API submission error", state="error")
                    st.error(res.text)
                    st.stop()
                
                data = res.json()
                rid = data.get("record_id")
                st.write(f"   -> Task queued. ID: {rid}")
                
                # 2. Polling for results
                st.write("2. Waiting for Worker processing...")
                found = False
                for i in range(15):
                    time.sleep(1)
                    check = requests.get(f"{API_URL}/firebase/{rid}")
                    if check.status_code == 200:
                        result_data = check.json().get("result", {})
                        desc = result_data.get("description", "")
                        st.write(f"   -> Processing complete! Result: {desc[:30]}...")
                        found = True
                        break
                
                if found:
                    # 3. Cleanup
                    requests.delete(f"{API_URL}/firebase/{rid}")
                    st.write("3. Test data cleaned up.")
                    status.update(label="Test Passed! System operational.", state="complete")
                else:
                    status.update(label="Test Timeout: Worker did not respond", state="error")
                    
            except Exception as e:
                status.update(label="Connection Error", state="error")
                st.error(f"Cannot connect to API: {e}")

# --- Main Page: Task Submission ---
st.title("AI Object Detection & LLM SaaS")
st.markdown("Submit images or text prompts to be processed by the backend Worker and Gemini LLM.")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Task Input")
    input_type = st.radio("Select Input Mode", ["Image Only", "Text Only", "Multimodal (Image + Text)"])
    
    img_url = ""
    text_prompt = ""
    
    # Logic for input fields based on selection
    if input_type in ["Image Only", "Multimodal (Image + Text)"]:
        img_url = st.text_input("Image URL", "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg")
        if img_url:
            st.image(img_url, caption="Preview", width=300)
            
    if input_type in ["Text Only", "Multimodal (Image + Text)"]:
        text_prompt = st.text_area("Text Prompt", "Describe this image in detail.")

    if st.button("Submit Task", type="primary"):
        payload = {}
        if img_url: 
            payload["image_url"] = img_url
        if text_prompt: 
            payload["text_prompt"] = text_prompt
        
        # Determine strict mode logic for payload
        if input_type == "Image Only":
            payload["text_prompt"] = None
        elif input_type == "Text Only":
            payload["image_url"] = None

        with st.spinner("Submitting to message queue..."):
            try:
                resp = requests.post(f"{API_URL}/submit_task", json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    new_id = data.get("record_id")
                    st.session_state['last_id'] = new_id
                    st.success(f"Task Accepted! Task ID: {new_id}")
                else:
                    st.error(f"Submission failed: {resp.text}")
            except Exception as e:
                st.error(f"Connection failed: {e}")

with col2:
    st.subheader("View Results")
    
    # Retrieve ID from session state if available
    default_id = str(st.session_state.get('last_id', ''))
    search_id = st.text_input("Enter Task ID", value=default_id)
    
    if st.button("Check Result / Refresh"):
        if search_id:
            try:
                res = requests.get(f"{API_URL}/firebase/{search_id}")
                if res.status_code == 200:
                    result = res.json().get("result", {})
                    st.write("### Raw JSON Result")
                    st.json(result)
                    
                    description = result.get('description')
                    if description:
                        st.write("### LLM Description")
                        st.info(description)
                elif res.status_code == 404:
                    st.warning("Result not found. The worker might still be processing, or the ID is incorrect.")
                else:
                    st.error(f"Error fetching result: Status {res.status_code}")
            except Exception as e:
                st.error(f"Connection error: {e}")
