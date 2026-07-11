import os
import requests
from dotenv import load_dotenv
import json

load_dotenv()

api_key = os.getenv("GOOGLE_PLACES_API_KEY")
url = "https://places.googleapis.com/v1/places:autocomplete"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
}

payload = {
    "input": "Danbam korean food Lucknow",
    "includedRegionCodes": ["IN"],
    "sessionToken": "test-session-1234"
}

try:
    res = requests.post(url, json=payload, headers=headers)
    print("Status:", res.status_code)
    data = res.json()
    print("Data:", json.dumps(data, indent=2))
except Exception as e:
    import traceback
    traceback.print_exc()
