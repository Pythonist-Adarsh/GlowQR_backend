import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GOOGLE_PLACES_API_KEY")
url = "https://places.googleapis.com/v1/places:autocomplete"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
}
payload = {
    "input": "House of Aadayein",
    "regionCode": "IN",
    "sessionToken": "f47ac10b-58cc-4372-a567-0e02b2c3d479"
}
try:
    res = requests.post(url, json=payload, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    import traceback
    traceback.print_exc()
