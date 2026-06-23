import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("SERP_API")

place_id = "ChIJIzjXSgBZmTkRO0TuHgHrtec"

# Test 3: google_maps_reviews engine with place_id
print("Test 3: google_maps_reviews engine")
res3 = requests.get("https://serpapi.com/search", params={
    "engine": "google_maps_reviews",
    "place_id": place_id,
    "api_key": api_key,
}).json()

place_info = res3.get("place_info", {})
print("Rating:", place_info.get("rating"))
print("Reviews:", place_info.get("reviews"))
