import dependencies
from database import engine
from sqlalchemy import text

def add_scan_event_id():
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='negative_feedback' AND column_name='scan_event_id'"))
            if not result.fetchone():
                print("Adding scan_event_id column...")
                conn.execute(text("ALTER TABLE negative_feedback ADD COLUMN scan_event_id INTEGER REFERENCES scan_events(id) ON DELETE CASCADE"))
                conn.commit()
                print("Column added successfully!")
            else:
                print("Column already exists.")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    add_scan_event_id()
