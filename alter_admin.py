import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    print("DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)

def add_columns():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS admin_email VARCHAR;"))
            conn.execute(text("ALTER TABLE admin_settings ADD COLUMN IF NOT EXISTS admin_password_hash VARCHAR;"))
            conn.commit()
            print("Columns added successfully.")
        except Exception as e:
            print(f"Error adding columns: {e}")

if __name__ == "__main__":
    add_columns()
