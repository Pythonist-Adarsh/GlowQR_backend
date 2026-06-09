import asyncio
from services.groq_service import generate_reviews

async def main():
    print("Testing Premium Plan (3 English + 2 Hinglish)")
    for i in range(3):
        session_id = f"session_premium_{i}"
        print(f"\n--- PREMIUM CALL {i+1} (Session: {session_id}) ---")
        reviews = await generate_reviews(
            business_name="Raj Jewelers",
            category="Jewellery Store",
            overall_rating=5,
            selected_items=["Bridal Necklace", "Gold Bangles"],
            plan="premium",
            city="Lucknow",
            session_id=session_id
        )
        for idx, r in enumerate(reviews):
            print(f"{idx+1}. {r}")
            
    print("\n\nTesting Basic Plan (5 English only)")
    for i in range(1):
        session_id = f"session_basic_{i}"
        print(f"\n--- BASIC CALL {i+1} (Session: {session_id}) ---")
        reviews = await generate_reviews(
            business_name="Raj Jewelers",
            category="Jewellery Store",
            overall_rating=4,
            selected_items=["Silver Ring"],
            plan="basic",
            city="Lucknow",
            session_id=session_id
        )
        for idx, r in enumerate(reviews):
            print(f"{idx+1}. {r}")

if __name__ == "__main__":
    asyncio.run(main())
