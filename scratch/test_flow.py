import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from database import SessionLocal
import models
import time

client = TestClient(app)

def test_flow():
    db = SessionLocal()
    try:
        # Find Taxcare or House of Adayein
        business = db.query(models.Business).filter(models.Business.name.ilike("%Adayein%")).first()
        if not business:
            print("House of Adayein not found")
            return
            
        print(f"Found business: {business.name} with slug: {business.slug}")
        
        # 1. Fetch QR Page Data
        print("1. Fetching QR page data...")
        res = client.get(f"/api/qr/{business.slug}")
        print("Status:", res.status_code)
        if res.status_code != 200:
            print("Failed.")
            return
            
        # 2. Record Scan Event
        print("2. Recording Scan Event...")
        res = client.post("/api/scan/record", json={
            "qr_slug": business.slug,
            "stage": "scanned",
            "device_type": "Test Script"
        })
        print("Status:", res.status_code)
        if res.status_code != 200:
            print("Failed. Error:", res.json())
            return
        
        session_id = res.json().get("session_id")
            
        # 3. Generate AI Review
        print("3. Generating AI Review (5 Star)...")
        res = client.post("/api/scan/generate-review", json={
            "qr_slug": business.slug,
            "business_name": business.name,
            "category": business.category or "restaurant",
            "overall_rating": 5,
            "selected_items": ["Good Food", "Great Service"],
            "session_id": session_id
        })
        print("Status:", res.status_code)
        if res.status_code != 200:
            print(res.json())
            print("Failed.")
            return
            
        print("Generated Review Response:", res.json())
        print("Test passed successfully.")
        
    finally:
        db.close()

if __name__ == "__main__":
    start = time.time()
    test_flow()
    print(f"Test took {time.time() - start:.2f} seconds")
