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
        
        # Send emails (fire and forget, log if fails)
        try:
            from services.email_service import send_contact_form_alert, send_contact_auto_reply
            message_data = {
                "topic": contact.topic,
                "name": contact.name,
                "business_name": contact.business_name,
                "phone": contact.phone,
                "email": contact.email,
                "current_plan": contact.current_plan,
                "message": contact.message
            }
            send_contact_form_alert(message_data)
            send_contact_auto_reply(contact.email, contact.name)
        except Exception as email_err:
            print(f"Failed to send contact emails: {email_err}")

        return {"status": "success", "message": "Message received"}
    except Exception as e:
        db.rollback()
        print(f"Error saving contact message: {e}")
        raise HTTPException(status_code=500, detail="Could not send message. Please try again.")
