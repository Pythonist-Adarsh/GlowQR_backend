import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE businesses ADD COLUMN instagram_url VARCHAR;"))
        conn.commit()
        print("Successfully added instagram_url column.")
    except Exception as e:
        print(f"Migration error (might already exist): {e}")
