import unittest
import requests
import time
import os

BASE_URL = os.getenv("API_URL", "http://uploader:8000")

TEST_IMAGE_URL = "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg"

class TestSystemIntegration(unittest.TestCase):
    
    def setUp(self):
        print(f"\n[Setup] Connecting to API at {BASE_URL}...")
        try:
            for i in range(5):
                try:
                    res = requests.get(f"{BASE_URL}/health", timeout=5)
                    if res.status_code == 200:
                        print("   -> API is ready!")
                        return
                except requests.exceptions.ConnectionError:
                    print(f"   -> Waiting for API... ({i+1}/5)")
                    time.sleep(2)
            
            requests.get(f"{BASE_URL}/health", timeout=5)
        except Exception as e:
            self.fail(f"API is not reachable at {BASE_URL}. Error: {e}")

    def test_full_async_flow(self):
        
        # 1. POST
        print("[Step 1] Submitting Task...")
        payload = {"image_url": TEST_IMAGE_URL}
        response = requests.post(f"{BASE_URL}/submit_task", json=payload)
        
        self.assertEqual(response.status_code, 200, f"Submit failed: {response.text}")
        data = response.json()
        
        self.assertEqual(data["status"], "queued")
        record_id = data.get("record_id")
        print(f"   -> Task queued successfully. Record ID: {record_id}")
        self.assertIsNotNone(record_id)

        # 2. Wait Worker
        print("[Step 2] Waiting for Worker (Polling)...")
        max_retries = 15
        found = False
        
        for i in range(max_retries):
            time.sleep(2)
            print(f"   -> Attempt {i+1}/{max_retries}: Checking Firebase result...")
            
            # GET
            res = requests.get(f"{BASE_URL}/firebase/{record_id}")
            
            if res.status_code == 200:
                result_data = res.json().get("result", {})
                description = result_data.get("description")
                if description:
                    print(f"   -> Success! Worker finished.")
                    print(f"   -> LLM Output: {description[:50]}...")
                    found = True
                    break
            elif res.status_code == 404:
                continue
            else:
                self.fail(f"Unexpected error during polling: {res.text}")
        
        self.assertTrue(found, "Timed out! Worker did not process the task in time.")

        # 3. DELETE
        print("[Step 3] Cleaning up...")
        del_res = requests.delete(f"{BASE_URL}/firebase/{record_id}")
        self.assertEqual(del_res.status_code, 200, "Delete failed")
        print("   -> Cleanup successful.")

if __name__ == "__main__":
    unittest.main()
