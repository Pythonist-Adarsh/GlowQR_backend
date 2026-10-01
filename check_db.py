from database import SessionLocal
import models
from sqlalchemy import text

def test():
    db = SessionLocal()
    
    upgrade_requests = db.query(models.UpgradeRequest).order_by(models.UpgradeRequest.id.desc()).limit(10).all()
    print('UpgradeRequests (last 10):')
    for req in upgrade_requests:
        amount = getattr(req, 'amount', 'N/A')
        print(f'ID: {req.id}, BusinessID: {getattr(req, "business_id", getattr(req, "business_name", "N/A"))}, Plan: {getattr(req, "requested_plan", "N/A")}, Status: {req.status}, Amount: {amount}')
        
    payments = db.query(models.Payment).order_by(models.Payment.id.desc()).limit(10).all()
    print('Payments (last 10):')
    for p in payments:
        amount = getattr(p, 'amount', getattr(p, 'order_amount', getattr(p, 'payment_amount', 'N/A')))
        print(f'ID: {p.id}, OrderID: {getattr(p, "order_id", "N/A")}, Amount: {amount}, Status: {getattr(p, "payment_status", getattr(p, "status", "N/A"))}')
        
test()
