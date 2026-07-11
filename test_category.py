import os
from dotenv import load_dotenv

load_dotenv()
from services.places_service import fetch_place_details, fetch_nearby_competitors

place_id = "ChIJ06MInu7jmzkR2GKWiEcchfQ"
target_data = fetch_place_details(place_id)
if not target_data:
    print("Could not fetch target data")
    exit(1)

location = target_data.get("location", {})
lat = location.get("latitude")
lng = location.get("longitude")
print(f"Location: {lat}, {lng}")

included_types = ["jewelry_store"]
competitors = fetch_nearby_competitors(lat, lng, 4000.0, included_types)

print(f"Competitors fetched: {len(competitors)}")
for comp in competitors:
    print(f"- {comp.get('displayName', {}).get('text')}")
