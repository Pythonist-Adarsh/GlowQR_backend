import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
import time

client = TestClient(app)

def test_extract():
    print("Triggering AI Profile Extraction...")
    start = time.time()
    res = client.post("/ai-profile/extract")
    print("Status:", res.status_code)
    print("Response:", res.json())
    print(f"Extraction took {time.time() - start:.2f} seconds")

if __name__ == "__main__":
    test_extract()
