from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
import schemas

router = APIRouter(
    prefix="/api/contact",
    tags=["Contact"]
)

@router.post("")
def submit_contact_form(contact: schemas.ContactMessageCreate, db: Session = Depends(get_db)):
    try:
        db_contact = models.ContactMessage(
            topic=contact.topic,
            name=contact.name,
            business_name=contact.business_name,
            phone=contact.phone,
            email=contact.email,
            current_plan=contact.current_plan,
            message=contact.message
        )
        db.add(db_contact)
        db.commit()
        db.refresh(db_contact)
        return {"status": "success", "message": "Message received"}
    except Exception as e:
        db.rollback()
        print(f"Error saving contact message: {e}")
        raise HTTPException(status_code=500, detail="Could not send message. Please try again.")
