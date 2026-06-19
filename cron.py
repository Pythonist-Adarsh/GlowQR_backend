import os
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from database import SessionLocal
import models
from services.email_service import send_renewal_reminder_alert, send_expired_alert

def run_daily_renewal_jobs():
    """
    Cron job function that handles two tasks:
    1. Expire overdue plans (plan_expires_at < now() - 1 day)
    2. Send 7-day renewal reminders (plan_expires_at BETWEEN now() AND now() + 7 days)
    """
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        
        # Admin settings for UPI
        admin_settings = db.query(models.AdminSettings).first()
        upi_id = admin_settings.upi_id if admin_settings and admin_settings.upi_id else "Not configured"

        # TASK 1: Expire overdue plans
        # plan_expires_at < now() - 1 day AND plan NOT IN ('trial', 'expired')
        one_day_ago = now - timedelta(days=1)
        overdue_users = db.query(models.User).filter(
            models.User.plan_expires_at < one_day_ago,
            models.User.plan.notin_(['trial', 'expired'])
        ).all()

        for user in overdue_users:
            user.plan = 'expired'
            
            # Find their businesses and deactivate QR codes
            businesses = db.query(models.Business).filter(models.Business.owner_id == user.id).all()
            for business in businesses:
                qr_codes = db.query(models.QRCode).filter(models.QRCode.business_id == business.id).all()
                for qr in qr_codes:
                    qr.is_active = False

            db.commit()

            # Send expired alert
            send_expired_alert(
                owner_email=user.email,
                owner_name=user.full_name or "User",
                upi_id=upi_id
            )

        # TASK 2: Send 7-day renewal reminders
        # plan_expires_at BETWEEN now() AND now() + 7 days AND renewal_reminder_sent = false
        seven_days_from_now = now + timedelta(days=7)
        expiring_users = db.query(models.User).filter(
            models.User.plan_expires_at >= now,
            models.User.plan_expires_at <= seven_days_from_now,
            models.User.renewal_reminder_sent == False,
            models.User.plan.notin_(['trial', 'expired'])
        ).all()

        for user in expiring_users:
            # Send reminder alert
            expiry_date_str = user.plan_expires_at.strftime("%B %d, %Y") if user.plan_expires_at else "soon"
            send_renewal_reminder_alert(
                owner_email=user.email,
                owner_name=user.full_name or "User",
                plan=user.plan,
                expiry_date=expiry_date_str,
                upi_id=upi_id
            )
            
            user.renewal_reminder_sent = True
            db.commit()

    except Exception as e:
        print(f"Error in daily renewal jobs: {e}")
    finally:
        db.close()
