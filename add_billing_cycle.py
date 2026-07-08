import os
from sqlalchemy import text
from database import engine

def add_billing_cycle():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE users ADD COLUMN billing_cycle VARCHAR DEFAULT 'monthly';"))
            conn.commit()
            print("Added billing_cycle to users")
        except Exception as e:
            print(f"Error adding to users: {e}")
            
        try:
            conn.execute(text("ALTER TABLE upgrade_requests ADD COLUMN billing_cycle VARCHAR DEFAULT 'monthly';"))
            conn.commit()
            print("Added billing_cycle to upgrade_requests")
        except Exception as e:
            print(f"Error adding to upgrade_requests: {e}")

if __name__ == "__main__":
    add_billing_cycle()
