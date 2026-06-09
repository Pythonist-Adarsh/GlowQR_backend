import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    result = conn.execute(text("SELECT id, owner_id, name FROM businesses WHERE id = 26;"))
    for row in result:
        print("Business:", row)
        owner_id = row[1]
        owner_result = conn.execute(text(f"SELECT id, plan FROM users WHERE id = {owner_id};"))
        for o_row in owner_result:
            print("Owner:", o_row)
