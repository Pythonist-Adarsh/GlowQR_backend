import re

with open('d:/glowQR/backend/routers/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacement = '''
    all_reviews_query = db.query(models.ScanEvent).filter(
        models.ScanEvent.business_id == business.id,
        models.ScanEvent.overall_rating != None
    ).order_by(models.ScanEvent.scanned_at.desc()).all()
    
    formatted_reviews = []
    for r in all_reviews_query:
        formatted_reviews.append({
            "id": r.id,
            "overall_rating": r.overall_rating,
            "food_rating": r.food_rating,
            "service_rating": r.service_rating,
            "atmosphere_rating": r.atmosphere_rating,
            "selected_items": r.selected_items,
            "review_text": r.review_text,
            "redirected_to_google": r.redirected_to_google,
            "created_at": r.scanned_at.isoformat() if r.scanned_at else None
        })

    return {
        "total_scans": total,
        "total_redirects": redirects,
        "conversion_rate": round(conv_rate, 1),
        "google_rating": round(avg_rating, 1),
        "reviews_this_month": reviews_this_month,
        "ratings_split": ratings_split,
        "all_reviews": formatted_reviews,
        "recent_reviews": formatted_reviews[:5]
    }
'''

content = re.sub(r'    return \{\s*"total_scans": total,.*?\n    \}', replacement.strip(), content, flags=re.DOTALL)

with open('d:/glowQR/backend/routers/analytics.py', 'w', encoding='utf-8') as f:
    f.write(content)
