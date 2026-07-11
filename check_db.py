from database import SessionLocal
from models import HealthCheckScan

db = SessionLocal()
scans = db.query(HealthCheckScan).all()
print(f"Total scans in DB: {len(scans)}")
for s in scans:
    print(f"- {s.id}: {s.business_name} ({s.category})")
db.close()
