import os
from dotenv import load_dotenv

load_dotenv()

from database import SessionLocal
from routers.health_check import run_scan
from schemas_health import ScanRequest

db = SessionLocal()

req = ScanRequest(
    place_id="ChIJTZHqA5DjmzkRtV3moLB6qfQ",
    name="Danbro by Mr. Brown",
    address="Lucknow",
    category="Bakery",
    city="Lucknow"
)

try:
    response = run_scan(req, db)
    print("Headline Score:", response.headline_score)
    print("Issues:")
    for issue in response.issues:
        print(f"- {issue}")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
