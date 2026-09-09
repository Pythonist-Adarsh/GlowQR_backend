import asyncio
import os
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.groq_service import generate_reviews

async def test_category_repeatedly(category_name, business_name, selected_items, num_runs=10):
    print(f"\n--- Testing Category: {category_name} ({num_runs} runs) ---")
    failures = 0
    for i in range(num_runs):
        try:
            reviews = await generate_reviews(
                business_name=business_name,
                category=category_name,
                overall_rating=5,
                selected_items=selected_items,
                plan='trial',
                city='Delhi',
                session_id=f'test-session-{i}',
                return_debug=False
            )
            if len(reviews) != 5:
                print(f"Run {i+1}: Failed! Expected 5 reviews, got {len(reviews)}.")
                failures += 1
            else:
                print(f"Run {i+1}: Success.")
        except Exception as e:
            print(f"Run {i+1}: Error testing {category_name}: {e}")
            failures += 1
            
    return failures

async def main():
    if not os.environ.get("GROQ_API_KEY"):
        print("Warning: GROQ_API_KEY not found in environment, make sure it is set.")
    
    categories = [
        ("restaurant", "Spice Garden", ["Paneer Tikka", "Butter Chicken"]),
        ("salon", "Glow Beauty", ["Haircut", "Facial"]),
        ("tax / ca firm", "Trust CA", ["Tax Filing", "GST Return"]),
        ("bridal & festive jewellery", "Shine Jewellers", ["Gold Necklace", "Bridal Set"])
    ]
    
    total_failures = 0
    for cat, biz, items in categories:
        fails = await test_category_repeatedly(cat, biz, items, num_runs=10)
        total_failures += fails
        
    print(f"\nTotal Failures across 40 runs: {total_failures}")
    if total_failures == 0:
        print("All tests passed! 0 failures.")
    else:
        print(f"{total_failures} tests failed. Max tokens might still be too low or there is another issue.")

if __name__ == "__main__":
    asyncio.run(main())
