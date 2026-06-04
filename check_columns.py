import dependencies
from database import engine
from sqlalchemy import text

def check_columns():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='negative_feedback'"))
        columns = result.fetchall()
        print("Columns in negative_feedback:")
        for col in columns:
            print(col)

if __name__ == "__main__":
    check_columns()
