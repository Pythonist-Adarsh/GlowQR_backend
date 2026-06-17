import sys
import os

# Ensure the backend directory is in the python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
import models
from routers.business import sync_business_now

db = SessionLocal()
b = db.query(models.Business).filter_by(name='DANBAM').first()
u = db.query(models.User).filter_by(id=b.owner_id).first()

try:
    res = sync_business_now(db=db, current_user=u)
    print("Success:", res)
    b2 = db.query(models.Business).filter_by(name='DANBAM').first()
    print("Review count now:", b2.review_count)
except Exception as e:
    print("Error:", e)
