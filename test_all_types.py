import os, requests, re
from dotenv import load_dotenv
load_dotenv()
api_key = os.getenv('GOOGLE_PLACES_API_KEY')
url = 'https://places.googleapis.com/v1/places:searchNearby'
headers = {'Content-Type': 'application/json', 'X-Goog-Api-Key': api_key, 'X-Goog-FieldMask': 'places.id'}

with open('routers/health_check.py', 'r') as f:
    content = f.read()

types_found = set(re.findall(r'"([a-z_]+)"', content))

valid_types = []
for t in types_found:
    if t in ["id", "rating", "userRatingCount", "location", "latitude", "longitude", "places", "id", "status"]: continue
    payload = {'includedTypes': [t], 'maxResultCount': 1, 'locationRestriction': {'circle': {'center': {'latitude': 37.7937, 'longitude': -122.3965}, 'radius': 100}}}
    res = requests.post(url, json=payload, headers=headers)
    if 'INVALID_ARGUMENT' not in res.text:
        valid_types.append(t)
        print(f'VALID: {t}')
    else:
        print(f'INVALID: {t}')

print('\nList of all valid types found in the file:')
print(sorted(valid_types))
