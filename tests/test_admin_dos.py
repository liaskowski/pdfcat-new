import requests
import time
import concurrent.futures

BASE_URL = "http://127.0.0.1:8000"

def test_admin_dos_reindex():
    print("Testing Admin Reindex DoS scenario...")
    
    # 1. Login as Admin
    resp = requests.post(f"{BASE_URL}/auth/token", data={"username": "admin", "password": "admin"})
    if resp.status_code != 200:
        print("Admin login failed.")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Trigger Reindex
    # This might take a while to return if the router doesn't yield properly 
    # OR it might return fast but flood the background_tasks.
    start = time.time()
    try:
        resp = requests.post(f"{BASE_URL}/api/v1/admin/reindex", headers=headers, timeout=5)
        print(f"Reindex triggered: {resp.status_code}, {resp.json()}")
    except Exception as e:
        print(f"Reindex call timed out or failed (as expected if blocking): {e}")
    
    # 3. Check server responsiveness immediately after
    print("Checking server responsiveness...")
    for i in range(10):
        try:
            t1 = time.time()
            # Simple metadata fetch
            resp = requests.get(f"{BASE_URL}/documents/", headers=headers, timeout=2)
            duration = time.time() - t1
            print(f"Ping {i}: status={resp.status_code}, duration={duration:.3f}s")
        except Exception as e:
            print(f"Ping {i}: FAILED ({e})")
        time.sleep(1)

if __name__ == "__main__":
    test_admin_dos_reindex()
