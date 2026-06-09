import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine, Base
from models import ScanSession, BombAlert

# Create only the new tables
ScanSession.__table__.create(bind=engine, checkfirst=True)
BombAlert.__table__.create(bind=engine, checkfirst=True)

print("Tables scan_sessions and bomb_alerts created successfully.")
