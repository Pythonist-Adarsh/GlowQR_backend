import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import psycopg2

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

constraints_to_add = [
    ("menu_items", "business_id", "businesses", "id", "menu_items_business_id_fkey"),
    ("qr_codes", "business_id", "businesses", "id", "qr_codes_business_id_fkey"),
    ("scan_events", "qr_code_id", "qr_codes", "id", "scan_events_qr_code_id_fkey"),
    ("scan_events", "business_id", "businesses", "id", "scan_events_business_id_fkey"),
    ("negative_feedback", "business_id", "businesses", "id", "negative_feedback_business_id_fkey"),
    ("negative_feedback", "scan_event_id", "scan_events", "id", "negative_feedback_scan_event_id_fkey"),
    ("upgrade_requests", "user_id", "users", "id", "upgrade_requests_user_id_fkey"),
    ("subscriptions", "user_id", "users", "id", "subscriptions_user_id_fkey"),
    ("refresh_tokens", "user_id", "users", "id", "refresh_tokens_user_id_fkey")
]

for table, col, ftable, fcol, cname in constraints_to_add:
    print(f"Processing {cname} on {table}...")
    with engine.connect() as conn:
        try:
            # Clean up orphaned rows first!
            cleanup_stmt = f"""
            DELETE FROM {table} 
            WHERE {col} IS NOT NULL 
              AND {col} NOT IN (SELECT {fcol} FROM {ftable});
            """
            conn.execute(text(cleanup_stmt))
            
            # Try to drop if it exists
            conn.execute(text(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {cname}"))
            
            # Add the constraint
            stmt = f"""
            ALTER TABLE {table}
            ADD CONSTRAINT {cname}
            FOREIGN KEY ({col})
            REFERENCES {ftable} ({fcol})
            ON DELETE CASCADE;
            """
            conn.execute(text(stmt))
            conn.commit()
            print(f"  -> Added {cname} successfully.")
        except Exception as e:
            print(f"  -> Error: {e}")
