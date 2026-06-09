import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    print("Users:")
    result = conn.execute(text("SELECT id, plan FROM users;"))
    for row in result:
        print(row)
        
    print("\nSubscriptions:")
    result = conn.execute(text("SELECT id, user_id, plan_name, status FROM subscriptions;"))
    for row in result:
        print(row)
