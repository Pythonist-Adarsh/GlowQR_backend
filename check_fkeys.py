import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    query = """
    SELECT
        tc.table_name, 
        tc.constraint_name,
        rc.update_rule,
        rc.delete_rule
    FROM 
        information_schema.table_constraints AS tc 
        JOIN information_schema.referential_constraints AS rc
          ON tc.constraint_name = rc.constraint_name
    WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public';
    """
    result = conn.execute(text(query)).fetchall()
    for row in result:
        print(f"Table: {row[0]}, Constraint: {row[1]}, On Delete: {row[3]}")
