import os
import sqlalchemy
from database import engine, Base
import models
from sqlalchemy import inspect

def sync_table(engine, table_name, model_class):
    inspector = inspect(engine)
    existing_columns = [col['name'] for col in inspector.get_columns(table_name)]
    
    with engine.connect() as conn:
        for column in model_class.__table__.columns:
            if column.name not in existing_columns:
                # Basic mapping for column types
                col_type = column.type.compile(engine.dialect)
                print(f"Missing column {column.name} of type {col_type} in {table_name}. Adding...")
                
                try:
                    conn.execute(sqlalchemy.text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {col_type}"))
                    conn.commit()
                    print(f"Successfully added {column.name}")
                except Exception as e:
                    print(f"Failed to add {column.name}: {e}")

sync_table(engine, 'scan_events', models.ScanEvent)
sync_table(engine, 'businesses', models.Business)
print("Sync complete.")
