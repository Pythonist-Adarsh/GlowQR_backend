import dependencies
from database import engine
from sqlalchemy import text

def add_missing_columns():
    with engine.connect() as conn:
        try:
            print("Adding missing columns...")
            conn.execute(text("ALTER TABLE negative_feedback ADD COLUMN IF NOT EXISTS is_read BOOLEAN DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE negative_feedback ADD COLUMN IF NOT EXISTS is_resolved BOOLEAN DEFAULT FALSE"))
            conn.execute(text("ALTER TABLE negative_feedback ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITH TIME ZONE"))
            conn.commit()
            print("Columns added successfully!")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_missing_columns()
