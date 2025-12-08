import unittest
import requests
import time
import os

# ⚡ 自动适配：如果在 Docker 里跑，用 uploader；如果在本地跑，用 localhost
BASE_URL = os.getenv("API_URL", "http://uploader:8000")
# 测试用的图片 (Zidane)
TEST_IMAGE_URL = "https://raw.githubusercontent.com/ultralytics/yolov5/master/data/images/zidane.jpg"

class TestSystemIntegration(unittest.TestCase):
    
    def setUp(self):
        """测试前的准备工作：确保 API 活着"""
        print(f"\n[Setup] Connecting to API at {BASE_URL}...")
        try:
            # 尝试连接 5 次，每次等待 2 秒（给容器启动时间）
            for i in range(5):
                try:
                    res = requests.get(f"{BASE_URL}/health", timeout=5)
                    if res.status_code == 200:
                        print("   -> API is ready!")
                        return
                except requests.exceptions.ConnectionError:
                    print(f"   -> Waiting for API... ({i+1}/5)")
                    time.sleep(2)
            
            # 如果还连不上，就报错
            requests.get(f"{BASE_URL}/health", timeout=5)
        except Exception as e:
            self.fail(f"API is not reachable at {BASE_URL}. Error: {e}")

    def test_full_async_flow(self):
        """核心测试：提交任务 -> 异步处理 -> 验证结果 -> 清理"""
        
        # 1. 提交任务 (POST)
        print("[Step 1] Submitting Task...")
        payload = {"image_url": TEST_IMAGE_URL}
        response = requests.post(f"{BASE_URL}/submit_task", json=payload)
        
        # 验证提交是否成功
        self.assertEqual(response.status_code, 200, f"Submit failed: {response.text}")
        data = response.json()
        
        # 验证是否进入队列
        self.assertEqual(data["status"], "queued")
        record_id = data.get("record_id")
        print(f"   -> Task queued successfully. Record ID: {record_id}")
        self.assertIsNotNone(record_id)

        # 2. 等待 Worker 处理 (轮询检查)
        print("[Step 2] Waiting for Worker (Polling)...")
        max_retries = 15 # 最多等 30 秒
        found = False
        
        for i in range(max_retries):
            time.sleep(2) # 每次等 2 秒
            print(f"   -> Attempt {i+1}/{max_retries}: Checking Firebase result...")
            
            # 从 API 获取结果 (GET)
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
                # 还在处理中，继续循环
                continue
            else:
                self.fail(f"Unexpected error during polling: {res.text}")
        
        self.assertTrue(found, "Timed out! Worker did not process the task in time.")

        # 3. 清理数据 (DELETE)
        print("[Step 3] Cleaning up...")
        del_res = requests.delete(f"{BASE_URL}/firebase/{record_id}")
        self.assertEqual(del_res.status_code, 200, "Delete failed")
        print("   -> Cleanup successful.")

if __name__ == "__main__":
    unittest.main()
