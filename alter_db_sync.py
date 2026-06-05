import asyncio
from sqlalchemy import text
from database import engine
import models

def run_migration():
    # create new tables (e.g. google_rating_history)
    models.Base.metadata.create_all(bind=engine)
    
    # alter existing tables
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE businesses ADD COLUMN last_google_sync TIMESTAMP WITH TIME ZONE"))
            conn.commit()
            print("Successfully added last_google_sync to businesses.")
        except Exception as e:
            if 'already exists' in str(e).lower() or 'duplicate column' in str(e).lower():
                print("Column last_google_sync already exists.")
            else:
                print(f"Error altering businesses table: {e}")

if __name__ == "__main__":
    run_migration()
