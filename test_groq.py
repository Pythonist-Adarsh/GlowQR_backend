import sys
import asyncio
import os
from dotenv import load_dotenv

# Load env file to get API keys
load_dotenv(dotenv_path="d:/glowQR/backend/.env")

# Ensure python can import backend modules
sys.path.append("d:/glowQR")

from backend.services.groq_service import generate_reviews

async def test_generation():
    print(">>> Starting generate_reviews test for domestic mart...")
    try:
        reviews1 = await generate_reviews(
            business_name="DOMESTIK MART",
            category="domestic mart",
            overall_rating=5,
            selected_items=["Snacks & Biscuits", "Chocolates", "Icecreams"],
            plan="trial",
            city="Lucknow",
            return_debug=False
        )
        print("\n>>> DOMESTIC MART REVIEWS OUTPUT:")
        for i, review in enumerate(reviews1):
            print(f"[{i+1}] {review}")
    except Exception as e:
        print(f">>> TOP LEVEL EXCEPTION (Domestic Mart): {e}")

    print("\n\n>>> Starting generate_reviews test for restaurant...")
    try:
        reviews2 = await generate_reviews(
            business_name="The Food Place",
            category="restaurant",
            overall_rating=4,
            selected_items=["Pizza", "Pasta", "Garlic Bread"],
            plan="trial",
            city="Delhi",
            return_debug=False
        )
        print("\n>>> RESTAURANT REVIEWS OUTPUT:")
        for i, review in enumerate(reviews2):
            print(f"[{i+1}] {review}")
    except Exception as e:
        print(f">>> TOP LEVEL EXCEPTION (Restaurant): {e}")

if __name__ == "__main__":
    asyncio.run(test_generation())
