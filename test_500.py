from fastapi.testclient import TestClient
from main import app
from database import SessionLocal, engine, Base

# Create tables
Base.metadata.create_all(bind=engine)

client = TestClient(app)

# 1. Register a user to get token
response = client.post("/register", json={
    "email": "test@test.com",
    "password": "test",
    "full_name": "Test User"
})
if response.status_code == 400: # Already registered
    response = client.post("/login", json={
        "email": "test@test.com",
        "password": "test"
    })
    
token = response.json()["access_token"]

# 2. Create business
response = client.post(
    "/businesses/",
    headers={"Authorization": f"Bearer {token}"},
    json={
        "name": "The Velvet Cafe",
        "tagline": "Best coffee in town",
        "address": "123 Main St, City",
        "primary_color": "#1a8a3c",
        "logo_url": "https://example.com/logo.png",
        "google_review_url": "https://g.page/r/...",
        "category": "cafe",
        "menu_data": [{"category": "Beverages", "items": [{"id": 1, "name": "Latte", "price": "$4", "emoji": "☕"}]}],
        "negative_filter_enabled": True,
        "review_language": "English",
        "ai_variant_count": "3",
        "welcome_message": "Welcome to our cafe!",
        "animation_style": "premium"
    }
)
print("STATUS:", response.status_code)
print("BODY:", response.json() if response.status_code < 500 else response.text)
