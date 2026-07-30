import os
import base64
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.environ.get("GROQ_API_KEY")
if not api_key:
    print("No GROQ_API_KEY")
    exit(1)

client = Groq(api_key=api_key)

# Create a tiny 1x1 transparent PNG pixel in base64
tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

try:
    messages_payload = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "What is in this image?"},
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{tiny_png_base64}"
                    }
                }
            ]
        }
    ]
    try:
        response = client.chat.completions.create(
            model="meta-llama/llama-4-maverick-17b-128e-instruct",
            messages=messages_payload,
            temperature=0.2,
            max_tokens=50
        )
    except Exception as e:
        error_str = str(e).lower()
        if "404" in error_str or "does not exist" in error_str or "not found" in error_str:
            print(f"Maverick failed, falling back to qwen: {e}")
            response = client.chat.completions.create(
                model="qwen/qwen3.6-27b",
                messages=messages_payload,
                temperature=0.2,
                max_tokens=50
            )
        else:
            raise e
            
    print("SUCCESS")
    print(response.choices[0].message.content)
except Exception as e:
    print("ERROR:", str(e))
