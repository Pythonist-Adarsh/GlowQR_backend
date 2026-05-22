import sys
import os
from sqlalchemy import text
from sqlalchemy.engine import create_engine
from dotenv import load_dotenv

# Add the parent directory to the path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def update_db():
    conn = engine.connect()
    
    # List of columns to add
    new_columns = [
        ("whatsapp_number", "VARCHAR"),
        ("owner_email", "VARCHAR"),
        ("area_locality", "VARCHAR"),
        ("state", "VARCHAR"),
        ("google_rating", "VARCHAR"),
        ("review_count", "VARCHAR"),
        ("price_range", "VARCHAR"),
        ("cuisine_speciality", "VARCHAR"),
        ("dietary_options", "JSON"),
        ("signature_dish", "VARCHAR"),
        ("highlighted_dishes", "VARCHAR"),
        ("excluded_dishes", "VARCHAR"),
        ("experience_type", "VARCHAR DEFAULT 'classic'"),
        ("welcome_message", "VARCHAR"),
        ("ai_variant_count", "VARCHAR"),
        ("review_language", "VARCHAR DEFAULT 'English'")
    ]
    
    for col_name, col_type in new_columns:
        try:
            conn.execute(text(f'ALTER TABLE businesses ADD COLUMN "{col_name}" {col_type}'))
            print(f"Added column: {col_name}")
        except Exception as e:
            print(f"Column {col_name} might already exist or error: {e}")
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    update_db()
