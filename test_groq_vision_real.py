import os
import base64
import requests
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.environ.get("GROQ_API_KEY")
client = Groq(api_key=api_key)

# Real menu image
url = "https://marketplace.canva.com/EAFaFUz4aKo/2/0/1131w/canva-yellow-abstract-cooking-fire-free-logo-JmYWTjUsE-Q.jpg"
response = requests.get(url)
base64_image = base64.b64encode(response.content).decode('utf-8')

prompt = """Extract the menu items from this image.
Format the output EXACTLY as this JSON structure:
{
    "highlightDishes": "Dish1",
    "signatureDish": "Best Dish",
    "menuCategories": [
    {
        "category": "Category Name",
        "items": [
        { "id": 1, "name": "Item Name", "emoji": "🍔", "price": "₹200" }
        ]
    }
    ]
}
Return ONLY valid JSON.
"""

try:
    response = client.chat.completions.create(
        model="meta-llama/llama-4-scout-17b-16e-instruct",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{base64_image}"
                        }
                    }
                ]
            }
        ],
        temperature=0.2,
        max_tokens=1500,
        response_format={"type": "json_object"}
    )
    print("SUCCESS")
    print(response.choices[0].message.content)
except Exception as e:
    print("ERROR:", str(e))
