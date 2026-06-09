from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import models
from database import SessionLocal
import asyncio
from services.evidence_report import generate_and_upload_evidence_report
from services.email_service import send_owner_bomb_alert, send_admin_bomb_alert

class ReviewBombDetector:
    @staticmethod
    def run_detection(business_id: int):
        db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(minutes=60)
        fifteen_min_ago = now - timedelta(minutes=15)
        thirty_days_ago = now - timedelta(days=30)
        
        # 2A. COLLECT SESSION DATA
        recent_sessions = db.query(models.ScanSession).filter(
            models.ScanSession.business_id == business_id,
            models.ScanSession.scan_timestamp >= one_hour_ago
        ).order_by(models.ScanSession.scan_timestamp.asc()).all()
        
        if not recent_sessions:
            return
            
        reviews_last_1_hr = len(recent_sessions)
        reviews_last_15_min = sum(1 for s in recent_sessions if s.scan_timestamp >= fifteen_min_ago)
        
        # Calculate baseline hourly average (last 30 days)
        total_30_days = db.query(models.ScanSession).filter(
            models.ScanSession.business_id == business_id,
            models.ScanSession.scan_timestamp >= thirty_days_ago
        ).count()
        baseline_hourly_avg = total_30_days / (30 * 24)
        
        # Signals
        ip_counts = {}
        for s in recent_sessions:
            if s.ip_address:
                ip_counts[s.ip_address] = ip_counts.get(s.ip_address, 0) + 1
        same_ip_count = max(ip_counts.values()) if ip_counts else 0
            
        device_counts = {}
        for s in recent_sessions:
            if s.device_fingerprint:
                device_counts[s.device_fingerprint] = device_counts.get(s.device_fingerprint, 0) + 1
        same_device_count = max(device_counts.values()) if device_counts else 0
            
        times_to_rate = [s.time_to_rate_seconds for s in recent_sessions if s.time_to_rate_seconds is not None]
        avg_time_to_rate = sum(times_to_rate) / len(times_to_rate) if times_to_rate else 999
        
        timing_gaps = []
        for i in range(1, len(recent_sessions)):
            gap = (recent_sessions[i].scan_timestamp - recent_sessions[i-1].scan_timestamp).total_seconds()
            timing_gaps.append(gap)
            
        geo_blocks = {s.geo_block for s in recent_sessions if s.geo_block}
        all_same_geo_block = (len(geo_blocks) == 1) and len(recent_sessions) > 1
        
        # 2B. SCORE CALCULATION
        score = 0
        reasons = []
        
        if reviews_last_15_min > 5:
            score += 30
            reasons.append(f"{reviews_last_15_min} negative reviews received in 15 minutes (normal is {baseline_hourly_avg:.1f} per hour)")
        elif reviews_last_15_min > 3:
            score += 15
            reasons.append(f"{reviews_last_15_min} negative reviews received in 15 minutes")
            
        if reviews_last_1_hr > (baseline_hourly_avg * 3) and baseline_hourly_avg > 0:
            score += 25
            reasons.append(f"{reviews_last_1_hr} reviews in 1 hour exceeds 3x baseline of {baseline_hourly_avg:.1f}")
            
        if same_ip_count >= 2:
            score += 20
            reasons.append(f"{same_ip_count} sessions came from the same IP address")
            
        if same_device_count >= 2:
            score += 20
            reasons.append(f"{same_device_count} sessions came from the same device fingerprint")
            
        if avg_time_to_rate < 10:
            score += 20
            reasons.append(f"Average time from scan to rating was {avg_time_to_rate:.1f} seconds — too fast for a real customer")
        elif avg_time_to_rate < 20:
            score += 10
            reasons.append(f"Average time from scan to rating was {avg_time_to_rate:.1f} seconds — unusually fast")
            
        if timing_gaps and len(timing_gaps) >= 2 and (max(timing_gaps) - min(timing_gaps)) <= 5:
            score += 15
            reasons.append("All sessions arrived exactly within 5 seconds of each other — looks automated")
            
        if all_same_geo_block:
            score += 15
            reasons.append("All scans came from the same physical location block")
            
        score = min(score, 100)
        
        # 2C. VERDICT LOGIC
        if score < 40:
            verdict = 'organic'
            alert_level = 'none'
        elif score < 70:
            verdict = 'suspicious'
            alert_level = 'yellow'
        else:
            verdict = 'coordinated_attack'
            alert_level = 'red'
            
        # If it's organic, maybe don't flood the DB with organic alerts unless necessary. 
        # But we will save it to satisfy "Save a new row in bomb_alerts with all calculated fields."
        # Actually, let's only save if it's suspicious/attack to not clutter organic sessions, 
        # but the prompt says "Save a new row...". I will save it.
        
        session_ids = [str(s.id) for s in recent_sessions]
        is_flagged = (verdict != 'organic')
        
        alert = models.BombAlert(
            business_id=business_id,
            risk_score=score,
            verdict=verdict,
            alert_level=alert_level,
            sessions_involved=session_ids,
            reasons=reasons,
            recommended_action="Review the attached evidence report and contact Google support." if is_flagged else "No action needed."
        )
        db.add(alert)
        
        if is_flagged:
            for s in recent_sessions:
                s.is_flagged = True
                s.flag_reason = reasons[0] if reasons else "Suspicious activity detected"
                
        db.commit()
        
        business = db.query(models.Business).filter(models.Business.id == business_id).first()
        owner = db.query(models.User).filter(models.User.id == business.owner_id).first() if business else None
        
        if is_flagged and business:
            try:
                evidence_url = asyncio.run(generate_and_upload_evidence_report(alert, business, recent_sessions))
                if evidence_url:
                    alert.evidence_report_url = evidence_url
                    db.commit()
            except Exception as e:
                print(f"Error generating evidence PDF: {e}")
                
        # Trigger Emails
        if owner and alert_level in ['yellow', 'red']:
            try:
                send_owner_bomb_alert(owner.email, business.name, alert, owner.id)
            except Exception as e:
                print(f"Error sending owner alert email: {e}")
                
        if is_flagged and business:
            try:
                admin_email = "professional.adarsh.00@gmail.com" # Default admin or fetch from settings
                send_admin_bomb_alert(admin_email, business.name, alert, owner)
            except Exception as e:
                print(f"Error sending admin alert email: {e}")

        except Exception as e:
            print(f"Error in ReviewBombDetector: {e}")
        finally:
            db.close()
