import os
import requests

def get_places_api_key():
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_PLACES_API_KEY environment variable is missing. Startup aborted.")
    return api_key

def autocomplete_search(query: str, session_token: str = None):
    """
    Search using Google Places API (New) Autocomplete.
    Uses session tokens for free billing.
    """
    api_key = get_places_api_key()

    url = "https://places.googleapis.com/v1/places:autocomplete"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
    }
    
    payload = {
        "input": query,
        "includedRegionCodes": ["IN"]
    }
    if session_token:
        payload["sessionToken"] = session_token
        
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        results = []
        for suggestion in data.get("suggestions", []):
            if "placePrediction" in suggestion:
                pred = suggestion["placePrediction"]
                results.append({
                    "place_id": pred.get("placeId"),
                    "name": pred.get("structuredFormat", {}).get("mainText", {}).get("text", ""),
                    "address": pred.get("structuredFormat", {}).get("secondaryText", {}).get("text", ""),
                    "rating": 0,  # Not requesting Pro fields in Autocomplete
                    "reviews": 0
                })
        return results
    except Exception as e:
        print(f"Places Autocomplete Error: {e}")
        return []

def fetch_place_details(place_id: str, session_token: str = None):
    """
    Fetch exact place details terminating the session token.
    FieldMask uses Pro tier fields only.
    """
    api_key = get_places_api_key()

    url = f"https://places.googleapis.com/v1/places/{place_id}"
    headers = {
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "id,displayName,rating,userRatingCount,formattedAddress,types,businessStatus,currentOpeningHours,photos,websiteUri,location,reviews,nationalPhoneNumber"
    }
    
    # Session token can be passed as a query param for place details in API (New)
    params = {}
    if session_token:
        params["sessionToken"] = session_token
        
    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Places Details Error: {e}")
        return None

def fetch_nearby_competitors(lat: float, lng: float, radius: float, included_types: list):
    """
    Fetch nearby competitors using Nearby Search (New).
    FieldMask uses Pro tier fields only.
    """
    api_key = get_places_api_key()

    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.rating,places.userRatingCount,places.formattedAddress"
    }
    
    payload = {
        "includedTypes": included_types,
        "maxResultCount": 20,
        "locationRestriction": {
            "circle": {
                "center": {
                    "latitude": lat,
                    "longitude": lng
                },
                "radius": radius
            }
        }
    }
    
    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        res.raise_for_status()
        data = res.json()
        return data.get("places", [])
    except Exception as e:
        print(f"Places Nearby Search Error: {e}")
        return []
