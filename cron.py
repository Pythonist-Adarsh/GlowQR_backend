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

        # TASK 2: Send renewal reminders
        # Monthly: 7-day buffer (plan_expires_at <= now() + 7 days)
        # Yearly: 30-day buffer (plan_expires_at <= now() + 30 days)
        thirty_days_from_now = now + timedelta(days=30)
        seven_days_from_now = now + timedelta(days=7)
        
        # Get all users who haven't been reminded and haven't expired
        potential_users = db.query(models.User).filter(
            models.User.plan_expires_at >= now,
            models.User.plan_expires_at <= thirty_days_from_now,
            models.User.renewal_reminder_sent == False,
            models.User.plan.notin_(['trial', 'expired'])
        ).all()

        for user in potential_users:
            is_yearly = (user.billing_cycle == 'yearly')
            threshold = thirty_days_from_now if is_yearly else seven_days_from_now
            
            if user.plan_expires_at <= threshold:
                # Send reminder alert
                expiry_date_str = user.plan_expires_at.strftime("%B %d, %Y") if user.plan_expires_at else "soon"
                send_renewal_reminder_alert(
                    owner_email=user.email,
                    owner_name=user.full_name or "User",
                    plan=user.plan,
                    expiry_date=expiry_date_str,
                    upi_id=upi_id,
                    amount="₹1,899" if (is_yearly and user.plan == 'basic') else
                           "₹4,799" if (is_yearly and user.plan == 'premium') else
                           "₹199" if user.plan == 'basic' else "₹499"
                )
                
                user.renewal_reminder_sent = True
                db.commit()

    except Exception as e:
        print(f"Error in daily renewal jobs: {e}")
    finally:
        db.close()

def run_weekly_ai_profile_extraction():
    db = SessionLocal()
    try:
        # Check if House of Aadayein has new reviews since last_generated_at
        business = db.query(models.Business).filter(models.Business.name.ilike("%House of Aadayein%")).first()
        if not business:
            return
            
        import models_ai
        profile = db.query(models_ai.BusinessAIProfile).filter(models_ai.BusinessAIProfile.business_id == business.id).first()
        
        last_generated = profile.last_generated_at if profile else None
        
        query = db.query(models.ScanEvent).filter(
            models.ScanEvent.business_id == business.id,
            models.ScanEvent.review_text.isnot(None),
            models.ScanEvent.review_text != ''
        )
        if last_generated:
            query = query.filter(models.ScanEvent.scanned_at > last_generated)
            
        new_reviews = query.all()
        
        if new_reviews or not profile:
            # We have new reviews (or no profile yet). Let's call the extraction logic directly.
            # We can reuse the router's function or call it via HTTP. Let's just import and call it.
            # Actually, to avoid async issues in sync cron, we can use requests to call localhost or run the logic here.
            import httpx
            import os
            try:
                # Call local endpoint
                port = os.getenv("PORT", "10000")
                httpx.post(f"http://127.0.0.1:{port}/ai-profile/extract", timeout=60.0)
                print("Successfully triggered weekly AI profile extraction for House of Aadayein")
            except Exception as e:
                print(f"Error calling ai-profile extraction: {e}")
                
    except Exception as e:
        print(f"Error in weekly AI profile extraction: {e}")
    finally:
        db.close()

