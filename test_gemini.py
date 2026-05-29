import requests
import base64
import os
from dotenv import load_dotenv

load_dotenv(override=True)

api_key = os.environ.get("GEMINI_API_KEY")
if not api_key:
    print("NO GEMINI KEY")
    exit(1)

tiny_png_base64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="

url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
payload = {
    "contents": [{
        "parts": [
            {"text": "What is this image?"},
            {"inline_data": {"mime_type": "image/png", "data": tiny_png_base64}}
        ]
    }],
    "generationConfig": {"temperature": 0.2}
}

try:
    res = requests.post(url, json=payload)
    res.raise_for_status()
    print("SUCCESS")
    print(res.json())
except Exception as e:
    print("ERROR", str(e))
    if hasattr(res, 'text'):
        print(res.text)
