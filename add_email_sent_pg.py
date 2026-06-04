import dependencies
from database import engine
from sqlalchemy import text

def alter_db():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE negative_feedback ADD COLUMN email_sent BOOLEAN DEFAULT FALSE"))
            conn.commit()
            print("Added email_sent column")
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    alter_db()
