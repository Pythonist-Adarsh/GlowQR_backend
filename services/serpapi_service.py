import os
import requests
import re

def fetch_place_details(place_id: str):
    """
    Fetches the current rating and review count from SerpAPI for a Google Maps place ID.
    """
    api_key = os.getenv("SERP_API")
    if not api_key:
        print("SERP_API key not found in environment.")
        return None

    # Extract data_id if place_id is actually a URL
    if place_id.startswith("http"):
        # Match "1s0x...:0x..."
        match = re.search(r'1s(0x[0-9a-fA-F]+:0x[0-9a-fA-F]+)', place_id)
        if match:
            place_id = "!4m2!3m1!1s" + match.group(1)
        else:
            print(f"Could not extract data_id from URL: {place_id}")
            return None
    elif place_id.startswith("0x"):
        place_id = "!4m2!3m1!1s" + place_id

    params = {
        "engine": "google_maps",
        "type": "place",
        "data": place_id,
        "api_key": api_key,
    }

    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        place_results = data.get("place_results", {})
        if not place_results:
            return None
            
        rating = place_results.get("rating")
        reviews = place_results.get("reviews")
        
        if rating is not None and reviews is not None:
            return {
                "google_rating": float(rating),
                "review_count": int(reviews)
            }
        return None
        
    except Exception as e:
        print(f"Error fetching place details for {place_id}: {e}")
        return None
