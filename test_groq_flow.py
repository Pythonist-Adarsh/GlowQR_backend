import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_generate_review():
    payload = {
        "businessName": "Spice Symphony",
        "category": "Indian Restaurant",
        "tagline": "A symphony of flavors",
        "selectedItems": ["Butter Chicken", "Garlic Naan", "Mango Lassi"],
        "mealType": "Dinner",
        "priceRange": "₹500 - ₹1000",
        "seatingType": "Indoor",
        "waitTime": "15 mins",
        "overallRating": 5,
        "foodRating": 5,
        "serviceRating": 4,
        "atmosphereRating": 5,
        "language": "english",
        "variantCount": 3
    }
    
    print("Sending request to /api/v1/scan/generate-review with payload:")
    print(payload)
    print("-" * 50)
    
    response = client.post("/api/v1/scan/generate-review", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    
    print("Response Received:")
    print(data)
    print("-" * 50)
    
    assert "variants" in data
    assert "provider" in data
    assert len(data["variants"]) > 0
    
    print(f"Provider Used: {data['provider']}")
    print(f"Number of Variants Generated: {len(data['variants'])}")
    for i, variant in enumerate(data['variants'], 1):
        print(f"\nVariant {i}:")
        print(variant)

if __name__ == "__main__":
    test_generate_review()
    print("\n✅ Test completed successfully!")
