from services.geo_aeo_service import analyze_geo_aeo_signals

url = "https://example.com"
reviews = [
    {"text": {"text": "The jewelry collection is absolutely stunning. I bought a bridal set for my sister and the craftsmanship was amazing."}},
    {"text": {"text": "Very good service, nice place."}}
]
result = analyze_geo_aeo_signals(url, "Example Domain", "9999999999", reviews, "Jewellery")

import json
print(json.dumps(result, indent=2))
