import os
with open('routers/analytics.py', 'r', encoding='utf-8') as f:
    data = f.read()

target = """        "conversion_rate": int(google_posts / total_reviews * 100) if total_reviews > 0 else 0,
        "food_rating": 4.6,
        "food_pct": 92,
        "service_rating": 2.8,
        "service_pct": 56,
        "env_rating": 3.5,
        "env_pct": 70,"""

replacement = """        "conversion_rate": int(google_posts / total_reviews * 100) if total_reviews > 0 else 0,
        "food_rating": round(sum(s.food_rating for s in rated_scans if s.food_rating) / sum(1 for s in rated_scans if s.food_rating) if sum(1 for s in rated_scans if s.food_rating) > 0 else 0, 1),
        "food_pct": int(sum(s.food_rating for s in rated_scans if s.food_rating) / sum(1 for s in rated_scans if s.food_rating) / 5 * 100 if sum(1 for s in rated_scans if s.food_rating) > 0 else 0),
        "service_rating": round(sum(s.service_rating for s in rated_scans if s.service_rating) / sum(1 for s in rated_scans if s.service_rating) if sum(1 for s in rated_scans if s.service_rating) > 0 else 0, 1),
        "service_pct": int(sum(s.service_rating for s in rated_scans if s.service_rating) / sum(1 for s in rated_scans if s.service_rating) / 5 * 100 if sum(1 for s in rated_scans if s.service_rating) > 0 else 0),
        "env_rating": round(sum(s.atmosphere_rating for s in rated_scans if s.atmosphere_rating) / sum(1 for s in rated_scans if s.atmosphere_rating) if sum(1 for s in rated_scans if s.atmosphere_rating) > 0 else 0, 1),
        "env_pct": int(sum(s.atmosphere_rating for s in rated_scans if s.atmosphere_rating) / sum(1 for s in rated_scans if s.atmosphere_rating) / 5 * 100 if sum(1 for s in rated_scans if s.atmosphere_rating) > 0 else 0),"""

if target in data:
    data = data.replace(target, replacement)
    with open('routers/analytics.py', 'w', encoding='utf-8') as f:
        f.write(data)
    print("Patched send_weekly_summary")
else:
    print("Target not found")
