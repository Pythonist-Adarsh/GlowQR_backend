import sqlite3
import os

def alter_db():
    db_path = "glowqr.db"
    if not os.path.exists(db_path):
        print("DB not found")
        return
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        c.execute("ALTER TABLE negative_feedback ADD COLUMN email_sent BOOLEAN DEFAULT 0")
        print("Added email_sent column")
    except Exception as e:
        print("Error:", e)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    alter_db()
