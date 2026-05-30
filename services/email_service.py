import resend
import os

resend.api_key = os.environ.get("RESEND_API_KEY")
APP_URL = os.environ.get("APP_URL", "https://glow-qr-frontend.vercel.app")
# Hardcode to ensure Render doesn't override with an old invalid email
ADMIN_EMAIL = "professional.adarsh.00@gmail.com"

def send_upgrade_alert_to_admin(request: dict, approve_url: str, reject_url: str):
    amount = "₹299" if request['plan_requested'] == 'basic' else "₹699"
    resend.Emails.send({
        "from": "GlowQR <onboarding@resend.dev>",
        "to": [ADMIN_EMAIL],
        "subject": f"🔔 New Upgrade — {request['business_name']} wants {request['plan_requested'].upper()} {amount}",
        "html": f"""
        <h2>New Upgrade Request</h2>
        <p><b>Ref:</b> GQ-{request['id']:04d}</p>
        <p><b>Business:</b> {request['business_name']}</p>
        <p><b>Owner:</b> {request['contact_name']}</p>
        <p><b>Phone:</b> {request['phone']}</p>
        <p><b>Email:</b> {request['email']}</p>
        <p><b>Plan:</b> {request['plan_requested']} ({amount})</p>
        <p><b>UTR:</b> {request.get('utr_number') or 'Not provided'}</p>
        <p><b>Method:</b> {request['payment_method']}</p>
        <br>
        <a href="{approve_url}" style="background:#16a34a;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">✅ APPROVE</a>
        &nbsp;&nbsp;
        <a href="{reject_url}" style="background:#dc2626;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">❌ REJECT</a>
        """
    })

def send_qr_is_live(business_name: str, owner_email: str, scan_url: str):
    resend.Emails.send({
        "from": "GlowQR <onboarding@resend.dev>",
        "to": [owner_email],
        "subject": f"🎉 Your GlowQR for {business_name} is live!",
        "html": f"""
        <h2>Your QR code is ready!</h2>
        <p>Business: {business_name}</p>
        <p>Scan URL: <a href="{scan_url}">{scan_url}</a></p>
        <p>Dashboard: <a href="{APP_URL}/dashboard">View Dashboard</a></p>
        <p>Download your QR from the dashboard and place it at your counter.</p>
        """
    })

def send_negative_feedback_alert(business_name: str, owner_email: str, rating: int, feedback_text: str):
    resend.Emails.send({
        "from": "GlowQR <onboarding@resend.dev>",
        "to": [owner_email],
        "subject": f"⚠️ New negative feedback — {business_name}",
        "html": f"""
        <h2>Negative Feedback Received</h2>
        <p><b>Business:</b> {business_name}</p>
        <p><b>Rating:</b> {rating}/5</p>
        <p><b>Feedback:</b> {feedback_text}</p>
        <br>
        <p><a href="{APP_URL}/dashboard/analytics">View in Dashboard</a></p>
        """
    })

def send_activation_email(user, business_name: str, plan: str, expires_at):
    try:
        resend.Emails.send({
            "from": "GlowQR <onboarding@resend.dev>",
            "to": [user.email],
            "subject": f"🎉 Your GlowQR {plan.capitalize()} Plan is Now Active!",
            "html": f"""
            <h3>Hi {user.email},</h3>
            <p>Your {plan.upper()} plan for <b>{business_name}</b> is now active.</p>
            <p>Valid until: <b>{expires_at.strftime('%B %d, %Y')}</b></p>
            <br>
            <p><a href="{APP_URL}/login" style="background:#16a34a;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">Login to your dashboard</a></p>
            <br>
            <p>— GlowQR Team</p>
            """
        })
    except Exception as e:
        print(f"Failed to send activation email: {e}")

def send_rejection_email(user, business_name: str, reason: str):
    try:
        resend.Emails.send({
            "from": "GlowQR <onboarding@resend.dev>",
            "to": [user.email],
            "subject": "GlowQR Payment Verification — Action Required",
            "html": f"""
            <h3>Hi {user.email},</h3>
            <p>We could not verify your payment for <b>{business_name}</b>.</p>
            <p>Reason: <b>{reason}</b></p>
            <p>Please contact us at support@glowqr.in or resend your UTR.</p>
            <br>
            <p>— GlowQR Team</p>
            """
        })
    except Exception as e:
        print(f"Failed to send rejection email: {e}")
