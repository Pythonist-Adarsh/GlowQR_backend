import os
import sqlalchemy
from database import engine, Base
import models # Ensure models are loaded

def add_column(table, column, definition):
    with engine.connect() as conn:
        try:
            conn.execute(sqlalchemy.text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
            conn.commit()
            print(f"Added {column} to {table}")
        except Exception as e:
            print(f"Could not add {column} to {table}: {e}")

# Scan Events analytics additions
add_column("public.scan_events", "qr_code_id", "INTEGER")
add_column("public.scan_events", "user_agent", "VARCHAR")
add_column("public.scan_events", "ip_hash", "VARCHAR")
add_column("public.scan_events", "hour_of_day", "INTEGER")
add_column("public.scan_events", "day_of_week", "INTEGER")

# Add website_url to businesses
add_column("public.businesses", "website_url", "VARCHAR")

# Create new tables (DailyAnalytics, OnboardingRecord)
Base.metadata.create_all(bind=engine)
print("Schema update complete.")
Base.metadata.create_all(bind=engine)
print("Schema update complete.")
