import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure backend directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

from services.groq_service import generate_reviews

async def test_category(category, items, rating, plan='premium'):
    print(f"\n{'='*50}\nTesting Category: {category}\nItems: {items}\nRating: {rating}\n{'='*50}")
    
    # Run 3 times to check for repetition/duplicates
    for run in range(3):
        print(f"\n--- Run {run+1} ---")
        reviews = await generate_reviews(
            business_name="Test Business",
            category=category,
            overall_rating=rating,
            selected_items=items,
            plan=plan,
            city="Mumbai"
        )
        
        # Verify
        for i, rev in enumerate(reviews):
            missing = []
            for item in items:
                if item.lower() not in rev.lower():
                    missing.append(item)
            
            if missing:
                print(f"[FAIL] Variant {i+1} missing items {missing}: {rev[:100]}...")
            else:
                print(f"[PASS] Variant {i+1} includes all items.")
                
        # Check uniqueness in this batch
        if len(set(reviews)) < len(reviews):
            print("[FAIL] Duplicate reviews found in this batch!")
        else:
            print("[PASS] All variants in this batch are unique.")

async def main():
    print("Starting tests...")
    
    # Bakery / Cakes
    await test_category("Bakery", ["Chocolate Milk Cake Box", "Lemon Berry Mousse", "Motichoor Rabdi Cake"], 5)
    
    # Gym
    await test_category("Gym", ["Personal Training", "Zumba Classes"], 4)
    
    # Real Estate
    await test_category("Real Estate", ["Residential Sales", "Legal & Documentation", "Property Management"], 5)
    
    # CA Firm
    await test_category("CA Firm", ["ITR Filing", "Tax Consultation"], 3)
    
    print("\nTests complete.")

if __name__ == "__main__":
    asyncio.run(main())
