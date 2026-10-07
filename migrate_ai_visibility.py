from sqlalchemy import text
from database import SessionLocal

def migrate_ai():
    db = SessionLocal()
    try:
        db.execute(text("ALTER TABLE ai_visibility_log ADD COLUMN IF NOT EXISTS sourced_from_us BOOLEAN DEFAULT FALSE"))
        db.execute(text("ALTER TABLE ai_visibility_log ADD COLUMN IF NOT EXISTS sources JSON DEFAULT '[]'::json"))
        db.execute(text("ALTER TABLE businesses ADD COLUMN IF NOT EXISTS visibility_queries JSON DEFAULT '[]'::json"))
        db.commit()
        print("Successfully added AI visibility columns")
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    migrate_ai()
