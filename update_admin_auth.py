import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext
from models import AdminSettings
from dotenv import load_dotenv

load_dotenv()

# Setup passlib
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SQLALCHEMY_DATABASE_URL = os.environ.get("DATABASE_URL")
if not SQLALCHEMY_DATABASE_URL:
    print("DATABASE_URL not found in .env")
    exit(1)

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def update_admin():
    db = SessionLocal()
    try:
        # Get or create admin settings
        settings = db.query(AdminSettings).first()
        if not settings:
            settings = AdminSettings()
            db.add(settings)
            db.commit()
            db.refresh(settings)
            
        settings.admin_email = "Adarshtiwari2412@gmail.com"
        settings.admin_password_hash = pwd_context.hash("Adarsh@Millionaire#GlowQR")
        
        db.commit()
        print("Admin user updated successfully with email/password authentication.")
    except Exception as e:
        print(f"Error updating admin: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    update_admin()
