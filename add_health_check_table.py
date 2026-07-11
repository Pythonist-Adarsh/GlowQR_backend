import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine
from models import Base

def create_table():
    print("Creating health_check_scans table...")
    # This will create tables that don't exist yet
    Base.metadata.create_all(bind=engine)
    print("Done!")

if __name__ == "__main__":
    create_table()
