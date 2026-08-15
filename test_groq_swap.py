import asyncio
import os
import sys
from dotenv import load_dotenv
load_dotenv()
import sys

# Add backend directory to sys path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.groq_service import generate_reviews

async def test_category(category_name, business_name, selected_items):
    print(f"\n--- Testing Category: {category_name} ---")
    try:
        # Testing with 'trial' plan to verify 5 variants rule
        reviews = await generate_reviews(
            business_name=business_name,
            category=category_name,
            overall_rating=5,
            selected_items=selected_items,
            plan='trial',
            city='Delhi',
            session_id='test-session-123',
            return_debug=False
        )
        print(f"Generated {len(reviews)} reviews (Expected 5 for trial plan)")
        for i, review in enumerate(reviews):
            print(f"[{i+1}] {review}")
            
    except Exception as e:
        print(f"Error testing {category_name}: {e}")

async def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("Warning: GROQ_API_KEY not found in environment, make sure it is set.")
    
    categories = [
        ("restaurant", "Spice Garden", ["Paneer Tikka", "Butter Chicken"]),
        ("salon", "Glow Beauty", ["Haircut", "Facial"]),
        ("tax / ca firm", "Trust CA", ["Tax Filing", "GST Return"]),
        ("bridal & festive jewellery", "Shine Jewellers", ["Gold Necklace", "Bridal Set"])
    ]
    
    for cat, biz, items in categories:
        await test_category(cat, biz, items)

if __name__ == "__main__":
    asyncio.run(main())
