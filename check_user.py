import os
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import User, PaymentOrder, Business
import database

db = database.SessionLocal()

orders = db.query(PaymentOrder).filter(PaymentOrder.status == 'pending').all()
for o in orders:
    business = db.query(Business).filter(Business.id == o.business_id).first()
    if business:
        user = db.query(User).filter(User.id == business.owner_id).first()
        print(f"Order: {o.id}, Created: {o.created_at}, Business: {business.id}, User: {user.id if user else 'None'} ({user.email if user else 'None'})")
    else:
        print(f"Order: {o.id}, Business: {o.business_id} (Not found)")

