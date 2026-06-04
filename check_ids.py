import dependencies
from database import engine
from sqlalchemy import text

def check():
    with engine.connect() as conn:
        print(conn.execute(text("SELECT id, overall_rating, review_text FROM scan_events WHERE id=18")).fetchall())
        print(conn.execute(text("SELECT id, overall_rating, review_text FROM scan_events WHERE id IN (1,4,5,6)")).fetchall())

if __name__ == "__main__":
    check()
