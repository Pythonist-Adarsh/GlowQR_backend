import os
from dotenv import load_dotenv

load_dotenv()
import resend

resend.api_key = os.environ.get("RESEND_API_KEY")

try:
    response = resend.Emails.send({
        "from": "GlowQR <hello@glowqr.com>",
        "to": ["professional.adarsh.00@gmail.com"],
        "subject": "Test Email from GlowQR",
        "html": "<strong>It works!</strong>"
    })
    print("Email sent!", response)
except Exception as e:
    print("Error:", e)
