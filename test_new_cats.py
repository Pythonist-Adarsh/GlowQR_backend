import os, requests
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
url = 'https://places.googleapis.com/v1/places:searchNearby'
headers = {'Content-Type': 'application/json', 'X-Goog-Api-Key': api_key, 'X-Goog-FieldMask': 'places.id,places.displayName,places.primaryType'}

def test(cat_name, types):
    payload = {'includedTypes': types, 'maxResultCount': 3, 'locationRestriction': {'circle': {'center': {'latitude': 28.6139, 'longitude': 77.2090}, 'radius': 5000}}}
    res = requests.post(url, json=payload, headers=headers)
    print(f'\n--- {cat_name} ({types}) ---')
    if res.status_code == 200:
        places = res.json().get('places', [])
        for p in places: print(f"- {p.get('displayName', {}).get('text')}: {p.get('primaryType')}")
    else: print(res.text[:100])

test('Food Court', ['food_court'])
test('Artificial Jewellery', ['jewelry_store'])
