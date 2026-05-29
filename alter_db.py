from database import engine
from sqlalchemy import text

try:
    with engine.connect() as conn:
        conn.execute(text('ALTER TABLE scan_events ADD COLUMN review_text VARCHAR;'))
        conn.commit()
        print("Column review_text added successfully")
except Exception as e:
    print(f"Error: {e}")
