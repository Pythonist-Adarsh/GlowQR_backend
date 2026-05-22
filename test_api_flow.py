import requests
import json
import time

BASE_URL = "http://localhost:8000"
session = requests.Session()

def print_step(step_num, title):
    print(f"\n{'='*50}\n[STEP {step_num}] {title}\n{'='*50}")

def run_test():
    # Keep track of shared data
    auth_token = None
    business_id = None
    business_slug = None

    print("Starting End-to-End API Test for GlowQR...\n")

    # ---------------------------------------------------------
    # 1. REGISTER
    # ---------------------------------------------------------
    print_step(1, "Register User (Should start 7-day trial)")
    unique_email = f"test_{int(time.time())}@example.com"
    res = session.post(f"{BASE_URL}/api/auth/register", json={
        "email": unique_email,
        "full_name": "Test User",
        "password": "password123"
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))
    
    if res.status_code == 200:
        auth_token = res.json().get("access_token")
        session.headers.update({"Authorization": f"Bearer {auth_token}"})
    else:
        print("Failed to register. Exiting.")
        return

    # ---------------------------------------------------------
    # 2. CREATE BUSINESS
    # ---------------------------------------------------------
    print_step(2, "Create a Business")
    res = session.post(f"{BASE_URL}/businesses/", json={
        "name": "Cafe Lumiere",
        "tagline": "Best coffee in town",
        "category": "Cafe"
    })
    print("Status:", res.status_code)
    data = res.json()
    print("Response:", json.dumps(data, indent=2))
    business_id = data.get("id")
    business_slug = data.get("slug")

    # ---------------------------------------------------------
    # 3. MOCK MENU EXTRACTION
    # ---------------------------------------------------------
    print_step(3, "Extract Menu via AI (Mock)")
    res = session.post(f"{BASE_URL}/api/onboarding/extract-menu", json={
        "image_base64": "data:image/jpeg;base64,/9j/4AAQSk..."
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 4. UPDATE BUSINESS PROFILE (PATCH)
    # ---------------------------------------------------------
    print_step(4, "Update Business Profile (Negative Filter ON)")
    res = session.patch(f"{BASE_URL}/api/business/profile", json={
        "id": business_id,
        "primary_color": "#FF5733",
        "negative_filter_enabled": True
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 5. FETCH QR PAGE DATA
    # ---------------------------------------------------------
    print_step(5, "Fetch QR Page Data for AR Experience")
    res = session.get(f"{BASE_URL}/api/qr/{business_slug}")
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 6. RECORD SCAN EVENT
    # ---------------------------------------------------------
    print_step(6, "Record QR Scan Event")
    res = session.post(f"{BASE_URL}/api/scan/record", json={
        "business_id": business_id,
        "device_type": "iPhone 15 Pro"
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 7. GENERATE AI REVIEW
    # ---------------------------------------------------------
    print_step(7, "Generate AI Review Drafts (5 Star)")
    res = session.post(f"{BASE_URL}/api/scan/generate-review", json={
        "business_id": business_id,
        "rating": 5,
        "selections": {"food": "Excellent", "service": "Good"}
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 8. SUBMIT NEGATIVE FEEDBACK
    # ---------------------------------------------------------
    print_step(8, "Intercept & Submit Negative Feedback (1 Star)")
    res = session.post(f"{BASE_URL}/api/scan/feedback", json={
        "business_id": business_id,
        "rating": 1,
        "feedback_text": "The soup was cold and service was slow."
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 9. CREATE RAZORPAY SUBSCRIPTION
    # ---------------------------------------------------------
    print_step(9, "Create Razorpay Subscription (Upgrade to Premium)")
    res = session.post(f"{BASE_URL}/api/payments/create-subscription", json={
        "plan": "premium"
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

    # ---------------------------------------------------------
    # 10. VERIFY RAZORPAY PAYMENT
    # ---------------------------------------------------------
    print_step(10, "Verify Payment & Upgrade Account")
    res = session.post(f"{BASE_URL}/api/payments/verify", json={
        "razorpay_payment_id": "pay_mock123",
        "razorpay_subscription_id": "sub_mock123",
        "razorpay_signature": "sig_mock123"
    })
    print("Status:", res.status_code)
    print("Response:", json.dumps(res.json(), indent=2))

if __name__ == "__main__":
    run_test()
