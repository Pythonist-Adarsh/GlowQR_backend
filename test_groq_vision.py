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
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
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
        ],
        temperature=0.2,
        max_tokens=50
    )
    print("SUCCESS")
    print(response.choices[0].message.content)
except Exception as e:
    print("ERROR:", str(e))
