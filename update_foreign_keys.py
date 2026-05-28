import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker

# Assuming .env is loaded or DATABASE_URL is available
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("No DATABASE_URL found")
    exit(1)

engine = create_engine(DATABASE_URL)
metadata = MetaData()

def update_fkeys_to_cascade():
    with engine.connect() as conn:
        print("Fetching existing foreign keys...")
        
        # Query to find all foreign keys
        query = """
        SELECT
            tc.table_name, 
            kcu.column_name, 
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
        """
        
        result = conn.execute(text(query)).fetchall()
        
        for row in result:
            table = row[0]
            col = row[1]
            ftable = row[2]
            fcol = row[3]
            cname = row[4]
            
            print(f"Updating constraint {cname} on {table}.{col} -> {ftable}.{fcol}...")
            
            # Drop the old constraint
            drop_stmt = f"ALTER TABLE {table} DROP CONSTRAINT {cname};"
            conn.execute(text(drop_stmt))
            
            # Add the new constraint with CASCADE
            add_stmt = f"""
            ALTER TABLE {table}
            ADD CONSTRAINT {cname} 
            FOREIGN KEY ({col}) 
            REFERENCES {ftable} ({fcol})
            ON DELETE CASCADE;
            """
            conn.execute(text(add_stmt))
            print(f"Success for {cname}")

        conn.commit()
        print("All foreign keys updated to ON DELETE CASCADE!")

from sqlalchemy import text
if __name__ == "__main__":
    update_fkeys_to_cascade()
