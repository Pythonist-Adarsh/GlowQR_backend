import os
from sqlalchemy.orm import Session
from database import SessionLocal
import models
import security

def reset_passwords():
    db = SessionLocal()
    try:
        users = db.query(models.User).filter(models.User.email.in_(['adarshtiwari2412@gmail.com', 'adarshtiwari2413@gmail.com', 'adarsh.tiwari.harry.2000@gmail.com'])).all()
        for user in users:
            user.hashed_password = security.get_password_hash("Adarsh@123")
            print(f"Reset password for {user.email}")
        db.commit()
    finally:
        db.close()

if __name__ == "__main__":
    reset_passwords()
