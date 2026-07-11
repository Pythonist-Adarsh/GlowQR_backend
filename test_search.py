import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

from services.places_service import autocomplete_search

results = autocomplete_search("Danbam korean food")
print("Results for 'Danbam korean food':")
for r in results:
    print(f"- {r['name']} ({r['address']})")

results = autocomplete_search("McDonalds")
print("\nResults for 'McDonalds':")
for r in results:
    print(f"- {r['name']} ({r['address']})")
