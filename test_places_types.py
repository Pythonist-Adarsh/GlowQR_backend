import requests

url = "https://places.googleapis.com/v1/places:searchNearby"
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": "dummy",
    "X-Goog-FieldMask": "places.id"
}

types_to_test = [
    "accounting", "finance", "auto_repair", "car_repair", "school", "cram_school", 
    "beauty_salon", "hair_care", "spa", "hotel", "guest_house", "jewelry_store", "costume_jewelry_store", "food_court",
    "gym", "fitness_center", "massage_clinic", "dental_clinic", "dentist", "medical_clinic", "doctor",
    "photography_studio", "photographer"
]

for t in types_to_test:
    payload = {
        "includedTypes": [t],
        "maxResultCount": 1,
        "locationRestriction": {
            "circle": {
                "center": {"latitude": 37.7937, "longitude": -122.3965},
                "radius": 100
            }
        }
    }
    res = requests.post(url, json=payload, headers=headers)
    print(f"{t}: {res.status_code} - {res.text[:100]}")
