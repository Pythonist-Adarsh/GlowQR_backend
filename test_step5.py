import requests

BASE_URL = "http://localhost:8000"

# Register a new user
res = requests.post(f"{BASE_URL}/api/auth/register", json={
    "email": "test_step5@example.com",
    "password": "password123",
    "full_name": "Test User"
})
token = res.json().get("access_token")
headers = {"Authorization": f"Bearer {token}"}

# Step 1
res = requests.post(f"{BASE_URL}/api/onboarding/step/1", json={
    "name": "Test Cafe",
    "google_review_url": "https://g.page/r/test",
    "place_id": "test_place",
    "google_rating": 4.5,
    "review_count": 100
}, headers=headers)
print("Step 1:", res.status_code)

# Step 2
res = requests.post(f"{BASE_URL}/api/onboarding/step/2", data={
    "owner_email": "owner@example.com",
    "city": "Test City",
    "phone_number": "1234567890"
}, headers=headers)
print("Step 2:", res.status_code)

# Step 3
res = requests.post(f"{BASE_URL}/api/onboarding/step/3", json={
    "category": "restaurant",
    "price_range": "$$",
    "cuisine_speciality": "Italian"
}, headers=headers)
print("Step 3:", res.status_code)

# Step 4
res = requests.post(f"{BASE_URL}/api/onboarding/step/4", json={
    "signature_dish": "Pasta",
    "highlighted_dishes": "Pizza",
    "menu_categories": []
}, headers=headers)
print("Step 4:", res.status_code)

# Step 5
res = requests.post(f"{BASE_URL}/api/onboarding/step/5", data={
    "theme": "premium",
    "primary_color": "#ff0000",
    "welcome_msg": "Welcome",
    "variants": "3 variants",
    "language": "English"
}, headers=headers)
print("Step 5:", res.status_code)
if res.status_code != 200:
    print(res.text)

# Complete
res = requests.post(f"{BASE_URL}/api/onboarding/complete", headers=headers)
print("Complete:", res.status_code)
if res.status_code != 200:
    print(res.text)
