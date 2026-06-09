import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'glowqr.db')

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE businesses ADD COLUMN instagram_url VARCHAR;")
    conn.commit()
    print("Successfully added instagram_url column.")
except sqlite3.OperationalError as e:
    print(f"Migration error (might already exist): {e}")

conn.close()
