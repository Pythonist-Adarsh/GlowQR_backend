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
    "regionCode": "IN"
}
try:
    res = requests.post(url, json=payload, headers=headers)
    print("Status:", res.status_code)
    data = res.json()
    print("Data:", data)
    
    results = []
    for suggestion in data.get("suggestions", []):
        if "placePrediction" in suggestion:
            pred = suggestion["placePrediction"]
            
            # Simulate the backend parsing logic
            sf = pred.get("structuredFormat", {})
            st = sf.get("secondaryText", {}) if sf.get("secondaryText") is not None else {}
            
            # Let's see if our exact original line fails
            original_address = pred.get("structuredFormat", {}).get("secondaryText", {}).get("text", "")
            
            results.append({
                "place_id": pred.get("placeId"),
                "name": pred.get("structuredFormat", {}).get("mainText", {}).get("text", ""),
                "address": original_address,
                "rating": 0,
                "reviews": 0
            })
    print("Parsed Results:", results)
except Exception as e:
    import traceback
    traceback.print_exc()
