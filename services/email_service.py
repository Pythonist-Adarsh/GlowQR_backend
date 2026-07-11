import resend
import os

resend.api_key = os.environ.get("RESEND_API_KEY")
APP_URL = os.environ.get("APP_URL", "https://glowqr.com")
# Hardcode to ensure Render doesn't override with an old invalid email
ADMIN_EMAIL = "professional.adarsh.00@gmail.com"

def send_upgrade_alert_to_admin(request: dict, approve_url: str, reject_url: str):
    amount = "Ã¢â€šÂ¹199" if request['plan_requested'] == 'basic' else "Ã¢â€šÂ¹499"
    resend.Emails.send({
        "from": "GlowQR <hello@glowqr.com>",
        "to": [ADMIN_EMAIL],
        "subject": f"Ã°Å¸â€â€ New Upgrade Ã¢â‚¬â€ {request['business_name']} wants {request['plan_requested'].upper()} {amount}",
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
        <a href="{approve_url}" style="background:#16a34a;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">Ã¢Å“â€¦ APPROVE</a>
        &nbsp;&nbsp;
        <a href="{reject_url}" style="background:#dc2626;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">Ã¢ï¿½Å’ REJECT</a>
        """
    })

def send_qr_is_live(business_name: str, owner_email: str, scan_url: str):
    resend.Emails.send({
        "from": "GlowQR <hello@glowqr.com>",
        "to": [owner_email],
        "subject": f"Ã°Å¸Å½â€° Your GlowQR for {business_name} is live!",
        "html": f"""
        <h2>Your QR code is ready!</h2>
        <p>Business: {business_name}</p>
        <p>Scan URL: <a href="{scan_url}">{scan_url}</a></p>
        <p>Download your QR from the dashboard and place it at your counter.</p>
        """
    })

def send_groq_rate_limit_alert(business_name: str, error_msg: str):
    resend.Emails.send({
        "from": "GlowQR <hello@glowqr.com>",
        "to": [ADMIN_EMAIL],
        "subject": "🚨 URGENT: GROQ Rate Limit Hit",
        "html": f"""
        <h2 style="color:red;">GROQ Rate Limit Exhausted</h2>
        <p><b>Business Context:</b> {business_name}</p>
        <p><b>Error Details:</b> {error_msg}</p>
        <p>Customers are currently receiving hardcoded fallback reviews. Please consider upgrading the Groq tier immediately.</p>
        <p><a href="https://console.groq.com/settings/billing">Go to Groq Billing Dashboard</a></p>
        """
    })

def send_negative_feedback_alert(business_name: str, owner_email: str, rating: int, feedback_text: str):
    resend.Emails.send({
        "from": "GlowQR <hello@glowqr.com>",
        "to": [owner_email],
        "subject": f"Ã¢Å¡Â Ã¯Â¸ï¿½ New negative feedback Ã¢â‚¬â€ {business_name}",
        "html": f"""
        <h2>Negative Feedback Received</h2>
        <p><b>Business:</b> {business_name}</p>
        <p><b>Rating:</b> {rating}/5</p>
        <p><b>Feedback:</b> {feedback_text}</p>
        <br>
        <p><a href="{APP_URL}/dashboard/analytics">View in Dashboard</a></p>
        """
    })

def send_password_reset_email(email: str, reset_link: str):
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [email],
            "subject": "Reset your GlowQR Password",
            "html": f"""
            <h2>Password Reset Request</h2>
            <p>We received a request to reset your password for your GlowQR account.</p>
            <p>Click the button below to choose a new password. This link is valid for 15 minutes.</p>
            <br>
            <a href="{reset_link}" style="background:#111111;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold;display:inline-block;">Reset Password</a>
            <br><br>
            <p>If you did not request a password reset, please ignore this email or reply to let us know.</p>
            <p>Ã¢â‚¬â€  GlowQR Team</p>
            """
        })
    except Exception as e:
        print(f"Failed to send password reset email: {e}")

def send_activation_email(user, business_name: str, plan: str, expires_at):
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [user.email],
            "subject": f"Ã°Å¸Å½â€° Your GlowQR {plan.capitalize()} Plan is Now Active!",
            "html": f"""
            <h3>Hi {user.email},</h3>
            <p>Your {plan.upper()} plan for <b>{business_name}</b> is now active.</p>
            <p>Valid until: <b>{expires_at.strftime('%B %d, %Y')}</b></p>
            <br>
            <p><a href="{APP_URL}/login" style="background:#16a34a;color:white;padding:12px 24px;border-radius:6px;text-decoration:none;font-weight:bold">Login to your dashboard</a></p>
            <br>
            <p>Ã¢â‚¬â€ GlowQR Team</p>
            """
        })
    except Exception as e:
        print(f"Failed to send activation email: {e}")

def send_rejection_email(user, business_name: str, reason: str):
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [user.email],
            "subject": "GlowQR Payment Verification Ã¢â‚¬â€ Action Required",
            "html": f"""
            <h3>Hi {user.email},</h3>
            <p>We could not verify your payment for <b>{business_name}</b>.</p>
            <p>Reason: <b>{reason}</b></p>
            <p>Please contact us at support@glowqr.in or resend your UTR.</p>
            <br>
            <p>Ã¢â‚¬â€ GlowQR Team</p>
            """
        })
    except Exception as e:
        print(f"Failed to send rejection email: {e}")

from datetime import datetime

async def send_low_rating_alert_email(
    owner_email: str,
    business_name: str,
    google_review_url: str,
    rating: int,
    selected_items: list,
    meal_type: str,
    price_range: str,
    wait_time: str,
    review_text: str,
    weak_areas: list,
    pattern: dict,
    action_tip: str,
    visit_time: datetime
):
    stars_display = "★" * rating + "☆" * (5 - rating)
    visit_time_str = visit_time.strftime("%d %b %Y, %I:%M %p") + " IST"
    items_str = ", ".join(selected_items) if selected_items else "Not specified"
    
    pattern_count = int(pattern["total_count"]) if pattern else 0
    pattern_html = ""
    if pattern_count >= 2:
        last_seen = pattern["last_seen"]
        last_seen_str = last_seen.strftime("%d %b, %I:%M %p") if last_seen else "recently"
        pattern_html = f"""
        <div style="background:#FFF7ED;border-left:3px solid #F59E0B;
                    padding:12px 16px;border-radius:0 8px 8px 0;margin:16px 0">
          <p style="margin:0 0 4px;font-size:13px;font-weight:600;color:#92400E">
            ⚠️ Pattern detected
          </p>
          <p style="margin:0;font-size:13px;color:#78350F">
            This is the <strong>{pattern_count}rd low rating</strong> in the last 30 days.
            Last one: {last_seen_str}
          </p>
        </div>
        """
    
    weak_html = ""
    if weak_areas:
        weak_items = "".join([
            f"<li style=\"margin-bottom:4px;font-size:13px;color:#374151\">"
            f"<strong>{area}</strong>: {rating_val}/5 ⭐</li>"
            for area, rating_val in weak_areas
        ])
        weak_html = f"""
        <div style="margin:16px 0">
          <p style="font-size:12px;font-weight:600;color:#6B7280;
                    text-transform:uppercase;letter-spacing:0.05em;margin:0 0 8px">
            Specifically low
          </p>
          <ul style="margin:0;padding-left:20px">{weak_items}</ul>
        </div>
        """
    
    google_reply_url = "https://business.google.com/reviews"
    
    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
    </head>
    <body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
                 background:#F9FAFB;margin:0;padding:24px">
      <div style="max-width:520px;margin:0 auto;background:#fff;
                  border-radius:12px;overflow:hidden;
                  border:1px solid #E5E7EB">
        <div style="background:#111;padding:20px 24px;
                    display:flex;align-items:center;gap:12px">
          <span style="font-size:22px">🔔</span>
          <div>
            <p style="margin:0;font-size:16px;font-weight:600;color:#fff">
              {rating}★ Review — {business_name}
            </p>
            <p style="margin:4px 0 0;font-size:13px;color:#9CA3AF">
              {visit_time_str}
            </p>
          </div>
        </div>
        <div style="padding:24px">
          <div style="display:flex;align-items:center;gap:12px;
                      padding:12px 16px;background:#FEF2F2;
                      border-radius:8px;margin-bottom:16px">
            <span style="font-size:24px;color:#EF4444">{stars_display}</span>
            <div>
              <p style="margin:0;font-size:14px;font-weight:600;color:#991B1B">
                {rating} out of 5 stars
              </p>
              <p style="margin:2px 0 0;font-size:12px;color:#B91C1C">
                {(meal_type.capitalize() if meal_type else "Visit")} · 
                {price_range or "Price not recorded"} per head ·
                Wait: {wait_time or "not recorded"}
              </p>
            </div>
          </div>
          <div style="margin-bottom:16px">
            <p style="font-size:12px;font-weight:600;color:#6B7280;
                      text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px">
              What they ordered
            </p>
            <p style="font-size:14px;color:#111827;margin:0">{items_str}</p>
          </div>
          {weak_html}
          <div style="background:#F9FAFB;border-radius:8px;
                      padding:12px 16px;margin-bottom:16px;
                      border-left:3px solid #E5E7EB">
            <p style="font-size:12px;font-weight:600;color:#6B7280;
                      text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px">
              Review they copied
            </p>
            <p style="font-size:13px;color:#374151;font-style:italic;margin:0;
                      line-height:1.6">
              "{review_text or "Review text not captured"}"
            </p>
          </div>
          {pattern_html}
          <div style="background:#F0FDF4;border:1px solid #86EFAC;
                      border-radius:8px;padding:16px;margin-bottom:20px">
            <p style="font-size:12px;font-weight:600;color:#166534;
                      text-transform:uppercase;letter-spacing:0.05em;margin:0 0 6px">
              💡 What to do now
            </p>
            <p style="font-size:14px;color:#14532D;margin:0;line-height:1.6">
              {action_tip}
            </p>
          </div>
          <div style="display:flex;gap:10px;flex-wrap:wrap">
            <a href="{google_reply_url}" 
               style="display:inline-block;background:#111;color:#fff;
                      text-decoration:none;padding:10px 20px;
                      border-radius:8px;font-size:13px;font-weight:600">
              Reply on Google ↗
            </a>
            <a href="{APP_URL}/dashboard" 
               style="display:inline-block;background:#F3F4F6;color:#374151;
                      text-decoration:none;padding:10px 20px;
                      border-radius:8px;font-size:13px;font-weight:600">
              View in Dashboard
            </a>
          </div>
        </div>
        <div style="padding:16px 24px;border-top:1px solid #F3F4F6;
                    background:#F9FAFB">
          <p style="margin:0;font-size:12px;color:#9CA3AF;line-height:1.6">
            This alert is part of your GlowQR Premium plan. 
            A handled 1-star review with a professional reply 
            is better for your business than no review at all.
            <br>WhatsApp alerts coming in GlowQR v2.0.
          </p>
        </div>
      </div>
    </body>
    </html>
    """
    
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [owner_email],
            "subject": f"🚨 {rating}★ Review just posted — {business_name}",
            "html": html_body
        })
    except Exception as e:
        print(f"Error sending email: {e}")

import os
import resend

APP_URL = os.environ.get('APP_URL', 'https://glowqr.com')
SENDER = 'GlowQR <hello@glowqr.com>'

def send_weekly_digest(owner_email: str, data: dict):
    try:
        with open('d:/glowQR/backend/templates/weekly_report.html', 'r', encoding='utf-8') as f:
            html_template = f.read()
            
        for key, value in data.items():
            html_template = html_template.replace(f'{{{{{key}}}}}', str(value))
            
        resend.Emails.send({
            'from': 'GlowQR <hello@glowqr.com>',
            'to': [owner_email],
            'subject': f"{data.get('business_name', 'Your Business')} — Weekly Performance Report & Improvement Tips",
            'html': html_template
        })
    except Exception as e:
        print(f"Failed to send weekly digest: {e}")

def send_owner_bomb_alert(owner_email: str, business_name: str, alert, business_id: int):
    subject = f"URGENT: Possible review attack on {business_name}" if alert.alert_level == 'red' else f"Unusual review activity detected — {business_name}"
    color = "#EF4444" if alert.alert_level == 'red' else "#F59E0B"
    badge_text = alert.alert_level.upper()
    
    reasons_html = "".join([f"<li>{r}</li>" for r in (alert.reasons or [])])
    
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: {color};">[{badge_text}] Review Bomb Alert</h2>
        <p><b>Business:</b> {business_name}</p>
        <p><b>Risk Score:</b> {alert.risk_score}/100</p>
        <p><b>Verdict:</b> {alert.verdict.replace('_', ' ').title()}</p>
        
        <h3>What happened?</h3>
        <p>{(alert.reasons[0] if alert.reasons else "We detected highly unusual review patterns directed at your QR code.")}</p>
        
        <h3>Detection Reasons:</h3>
        <ul>
            {reasons_html}
        </ul>
        
        <h3>Recommended Actions:</h3>
        <ul>
            <li>Check your Google Business Profile for new 1-star reviews</li>
            <li>Use the "Flag as inappropriate" option on each suspicious review</li>
            <li>Attach this report when contacting Google Business Support</li>
            <li>Brief your team — this appears to be a coordinated attack</li>
            <li>Contact GlowQR admin for further assistance</li>
        </ul>
        
        <br/>
        <a href="{alert.evidence_report_url or '#'}" style="display:inline-block; background:#111; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px; margin-right:10px;">Download Evidence Report</a>
        <a href="{APP_URL}/dashboard" style="display:inline-block; background:#f3f4f6; color:#111; text-decoration:none; padding:10px 20px; border-radius:8px;">View in Dashboard</a>
        
        <hr style="margin-top: 30px; border: none; border-top: 1px solid #e5e7eb;" />
        <p style="font-size: 12px; color: #6b7280;">Your internal GlowQR rating has NOT been affected by these flagged sessions.</p>
    </div>
    """
    
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [owner_email],
            "subject": subject,
            "html": html
        })
    except Exception as e:
        print(f"Error sending owner bomb alert: {e}")

def send_admin_bomb_alert(admin_email: str, business_name: str, alert, owner):
    subject = f"Bomb alert [{alert.alert_level}] — {business_name} — Score: {alert.risk_score}"
    
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #111;">Admin Alert: Review Bomb Detected</h2>
        <p><b>Business:</b> {business_name} (ID: {alert.business_id})</p>
        <p><b>Owner:</b> {owner.full_name} ({owner.email})</p>
        <p><b>Risk Score:</b> {alert.risk_score}/100</p>
        <p><b>Verdict:</b> {alert.verdict}</p>
        <p><b>Sessions Involved:</b> {len(alert.sessions_involved) if alert.sessions_involved else 0}</p>
        
        <br/>
        <a href="{APP_URL}/admin/bomb-alerts" style="display:inline-block; background:#111; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px; margin-right:10px;">View in Admin Dashboard</a>
    </div>
    """
    
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [admin_email],
            "subject": subject,
            "html": html
        })
    except Exception as e:
        print(f"Error sending admin bomb alert: {e}")

def send_renewal_reminder_alert(owner_email: str, owner_name: str, plan: str, expiry_date: str, upi_id: str, amount: str = "₹199"):
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #F59E0B;">Reminder: Your GlowQR Plan Expires Soon</h2>
        <p>Hi {owner_name}! 👋</p>
        <p>Your GlowQR <b>{plan}</b> plan expires soon (on {expiry_date}).</p>
        <p>Renew now to keep your QR active:</p>
        <p>👉 <b>Login → Dashboard → Renew Plan</b></p>
        <p>Or pay <b>{amount}</b> via UPI to: <b>{upi_id}</b></p>
        <br/>
        <a href="{APP_URL}/dashboard" style="display:inline-block; background:#111; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px;">Go to Dashboard</a>
        <br/><br/>
        <p>Need help? Reply to this email. 🙏</p>
        <p>— GlowQR Team</p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [owner_email],
            "subject": f"⚠️ Action Required: Your GlowQR plan expires soon",
            "html": html
        })
    except Exception as e:
        print(f"Error sending renewal reminder alert: {e}")

def send_expired_alert(owner_email: str, owner_name: str, upi_id: str):
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #EF4444;">Your GlowQR Plan Has Expired</h2>
        <p>Hi {owner_name}, your GlowQR plan has expired. 😔</p>
        <p>Your QR code is now inactive — customers see a paused message.</p>
        <p>Renew now to reactivate instantly:</p>
        <p>👉 <b>Login → Dashboard → Renew Plan</b></p>
        <p>UPI ID: <b>{upi_id}</b></p>
        <br/>
        <a href="{APP_URL}/dashboard" style="display:inline-block; background:#111; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px;">Renew Now</a>
        <br/><br/>
        <p>— GlowQR Team</p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [owner_email],
            "subject": f"🔴 Your GlowQR Plan has Expired",
            "html": html
        })
    except Exception as e:
        print(f"Error sending expired alert: {e}")

def send_renewal_confirmed_alert(owner_email: str, owner_name: str, plan: str, new_expiry_date: str):
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #10B981;">Renewal Confirmed! 🎉</h2>
        <p>Hi {owner_name}! 🎉</p>
        <p>Your GlowQR <b>{plan}</b> plan has been renewed successfully!</p>
        <p>QR is active again — valid till <b>{new_expiry_date}</b>.</p>
        <br/>
        <p>Thank you for continuing with GlowQR! 🙏</p>
        <br/>
        <a href="{APP_URL}/dashboard" style="display:inline-block; background:#111; color:#fff; text-decoration:none; padding:10px 20px; border-radius:8px;">Go to Dashboard</a>
        <br/><br/>
        <p>— GlowQR Team</p>
    </div>
    """
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [owner_email],
            "subject": f"✅ Renewal Successful: Your GlowQR plan is active",
            "html": html
        })
    except Exception as e:
        print(f"Error sending renewal confirmed alert: {e}")

def send_health_report_email(email: str, scan):
    business_name = scan.business_name
    score = scan.headline_score
    
    html = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #e5e7eb; border-radius: 8px;">
        <h2 style="color: #2563EB;">Your Local SEO Health Report</h2>
        <p>Hi there,</p>
        <p>Thank you for scanning <b>{business_name}</b>.</p>
        <p>Your Local Health Score is: <strong style="font-size: 24px; color: {'#16A34A' if score >= 70 else '#F59E0B' if score >= 40 else '#DC2626'}">{score}/100</strong></p>
        
        <p>If you'd like to improve your score and get more customers from Google, you can upgrade to GlowQR Premium!</p>
        <br/>
        <a href="{APP_URL}" style="display:inline-block; background:#2563EB; color:#fff; text-decoration:none; padding:12px 24px; border-radius:8px; font-weight: bold;">Get Started with GlowQR</a>
        <br/><br/>
        <p>— GlowQR Team</p>
    </div>
    """
    
    try:
        resend.Emails.send({
            "from": "GlowQR <hello@glowqr.com>",
            "to": [email],
            "subject": f"Your Local Health Score for {business_name}: {score}/100",
            "html": html
        })
    except Exception as e:
        print(f"Error sending health report email: {e}")
