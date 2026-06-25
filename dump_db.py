import sys
sys.path.append('d:/glowQR/backend')
from database import SessionLocal
from models import Business, MenuItem
import json

db = SessionLocal()
items = db.query(MenuItem).filter(MenuItem.name.like('%Crispy fries%')).all()
b_ids = set(item.business_id for item in items)
results = [{'name': b.name, 'category': b.category, 'menu_data': b.menu_data} for b in db.query(Business).filter(Business.id.in_(b_ids)).all()]

with open('out.txt', 'w', encoding='utf-8') as f:
    f.write(json.dumps(results, indent=2))
