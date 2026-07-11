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

    # If place_id is a raw Google Place ID (ChIJ...)
    if place_id.startswith("ChIJ"):
        params = {
            "engine": "google_maps_reviews",
            "place_id": place_id,
            "api_key": api_key,
        }
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            place_info = data.get("place_info", {})
            rating = place_info.get("rating")
            reviews = place_info.get("reviews")
            
            if rating is not None and reviews is not None:
                return {
                    "google_rating": float(rating),
                    "review_count": int(reviews)
                }
            return None
        except Exception as e:
            print(f"Error fetching place details (reviews engine) for {place_id}: {e}")
            return None

    # Original logic for data_id / URLs
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

def search_places(query: str, lat: float = None, lng: float = None):
    """
    Search for places matching the query using SerpAPI google_maps.
    """
    api_key = os.getenv("SERP_API")
    if not api_key:
        return []
        
    params = {
        "engine": "google_maps",
        "q": query,
        "api_key": api_key,
    }
    
    if lat and lng:
        params["ll"] = f"@{lat},{lng},14z"
        
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        local_results = data.get("local_results", [])
        place_results = data.get("place_results", {})
        
        # Sometimes it returns a direct place_results if exact match
        if place_results and "title" in place_results:
            return [{
                "place_id": place_results.get("place_id", ""),
                "name": place_results.get("title", ""),
                "address": place_results.get("address", ""),
                "rating": place_results.get("rating", 0),
                "reviews": place_results.get("reviews", 0),
                "thumbnail": place_results.get("thumbnail", ""),
                "data_id": place_results.get("data_id", "")
            }]
            
        return [{
            "place_id": r.get("place_id", ""),
            "name": r.get("title", ""),
            "address": r.get("address", ""),
            "rating": r.get("rating", 0),
            "reviews": r.get("reviews", 0),
            "thumbnail": r.get("thumbnail", ""),
            "data_id": r.get("data_id", "")
        } for r in local_results[:5]]
        
    except Exception as e:
        print(f"Error searching places: {e}")
        return []

def fetch_competitors(category: str, location: str):
    """
    Fetch competitors for a given category and location.
    e.g., category="Cafe", location="Mumbai" -> q="Cafe in Mumbai"
    """
    api_key = os.getenv("SERP_API")
    if not api_key:
        return []
        
    query = f"{category} in {location}"
    params = {
        "engine": "google_maps",
        "q": query,
        "api_key": api_key,
    }
    
    try:
        response = requests.get("https://serpapi.com/search", params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        local_results = data.get("local_results", [])
        
        return [{
            "place_id": r.get("place_id", ""),
            "name": r.get("title", ""),
            "rating": r.get("rating", 0),
            "reviews": r.get("reviews", 0),
        } for r in local_results[:10] if r.get("rating") and r.get("reviews")]
        
    except Exception as e:
        print(f"Error fetching competitors: {e}")
        return []
