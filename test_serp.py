import asyncio
from database import SessionLocal
import models
from services.serpapi_service import fetch_place_details
import os

db = SessionLocal()
bizs = db.query(models.Business).all()
for b in bizs:
    print(f"Business: {b.name}, Place ID: {b.place_id}")
    if b.place_id:
        res = fetch_place_details(b.place_id)
        print(f"Result: {res}")
