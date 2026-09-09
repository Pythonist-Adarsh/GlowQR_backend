import asyncio
import os
import time
import sys
from dotenv import load_dotenv

load_dotenv()
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from services.groq_service import generate_reviews

async def run_test(model_name):
    print(f"\n=====================\nTesting Model: {model_name}\n=====================")
    # Patch the groq service to use the new model
    import services.groq_service as gs
    original_generate = gs.client.chat.completions.create
    
    def wrapped_create(*args, **kwargs):
        kwargs['model'] = model_name
        if 'reasoning_effort' in kwargs:
            del kwargs['reasoning_effort']
        return original_generate(*args, **kwargs)
        
    gs.client.chat.completions.create = wrapped_create
    
    start = time.time()
    try:
        reviews = await generate_reviews(
            business_name="Spice Garden",
            category="restaurant",
            overall_rating=5,
            selected_items=["Paneer Tikka", "Butter Chicken"],
            plan='trial',
            city='Delhi',
            session_id='test-session-123',
            return_debug=False
        )
        end = time.time()
        print(f"Time taken: {end-start:.2f}s")
        print(f"Generated {len(reviews)} reviews:")
        for i, r in enumerate(reviews):
            print(f"[{i+1}] {r}")
    except Exception as e:
        print(f"Error: {e}")
    
    # Restore
    gs.client.chat.completions.create = original_generate

async def main():
    await run_test('openai/gpt-oss-120b')
    await run_test('qwen/qwen3.6-27b')
    await run_test('llama-3.1-8b-instant')

if __name__ == "__main__":
    asyncio.run(main())
