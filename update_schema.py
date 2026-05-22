import os
import sqlalchemy
from database import engine

def add_column(conn, table, column, definition):
    try:
        conn.execute(sqlalchemy.text(f"ALTER TABLE {table} ADD COLUMN {column} {definition}"))
        print(f"Added {column} to {table}")
    except Exception as e:
        print(f"Could not add {column} to {table}: {e}")

with engine.begin() as conn:
    # Users table
    add_column(conn, "public.users", "plan", "VARCHAR DEFAULT 'trial'")
    add_column(conn, "public.users", "trial_ends_at", "TIMESTAMP WITH TIME ZONE")
    add_column(conn, "public.users", "razorpay_customer_id", "VARCHAR")
    add_column(conn, "public.users", "razorpay_subscription_id", "VARCHAR")
    
    # Businesses table
    add_column(conn, "public.businesses", "negative_filter_enabled", "BOOLEAN DEFAULT FALSE")
    add_column(conn, "public.businesses", "animation_style", "VARCHAR DEFAULT 'Glow & Float'")
    add_column(conn, "public.businesses", "seasonal_theme", "VARCHAR")

print("Schema update complete.")
