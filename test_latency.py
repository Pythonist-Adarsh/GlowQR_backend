import os
import time
from dotenv import load_dotenv
from groq import Groq

load_dotenv()
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

prompt = "Business: Test\nCategory: restaurant\nOutput only JSON array of 3 strings."

for i in range(3):
    print(f"\n--- Test Run {i+1} ---")
    start = time.time()
    res = client.chat.completions.create(
        model='openai/gpt-oss-120b', 
        messages=[{'role': 'user', 'content': prompt}], 
        temperature=0.95, 
        max_tokens=2500,
        reasoning_effort='low'
    )
    end = time.time()
    
    usage = res.usage
    reasoning_tokens = usage.completion_tokens_details.reasoning_tokens if usage.completion_tokens_details else 0
    print(f"Time: {end-start:.2f}s")
    print(f"Total tokens: {usage.total_tokens} | Output tokens: {usage.completion_tokens} | Reasoning tokens: {reasoning_tokens}")
    print(f"Content length: {len(res.choices[0].message.content)}")

print("\nFetching models from Groq...")
models = client.models.list()
for m in models.data:
    if 'llama' in m.id.lower() or 'mixtral' in m.id.lower() or 'gemma' in m.id.lower() or 'qwen' in m.id.lower():
        print(m.id)
