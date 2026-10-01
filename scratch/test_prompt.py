import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import models, database
from services.groq_service import client

db = database.SessionLocal()
business = db.query(models.Business).filter(models.Business.name.ilike('%House of Aadayein%')).first()
reviews = db.query(models.ScanEvent.review_text).filter(
    models.ScanEvent.business_id == business.id, 
    models.ScanEvent.review_text.isnot(None), 
    models.ScanEvent.review_text != ''
).all()
review_texts = [r[0] for r in reviews]
combined_reviews = '\n- '.join(review_texts)

prompt = f"""
You are an expert AI data extractor. Extract rich structured context from the following customer reviews for "House of Aadayein", which is categorized as "{business.category}".

Reviews:
- {combined_reviews}

Extract specific facts from these reviews. DO NOT FABRICATE ANYTHING. Only use what is present in the reviews.
Important: When selecting themes for the FAQs, explicitly consider the full business category ("{business.category}"). Ensure the FAQs naturally surface topics like handbags, bridal lehenga rental, and fashion accessories (not just jewellery) IF the underlying reviews actually support those themes. Do not fabricate topics if they are not grounded in real data.

Output JSON with the following structure exactly:
{{
  "dishes_mentioned": ["list of specific products/services mentioned (e.g. bridal lehengas, handbags, jewellery)"],
  "occasions": ["weddings", "celebration", etc.],
  "praise_points": ["staff behavior", "collection variety", "value", etc. with specific details from reviews"],
  "comparisons": ["any comparisons to other places if mentioned"],
  "location_references": ["location or area references"],
  "faqs": [
     {{"q": "What is House of Aadayein known for?", "a": "Specific answer grounded in facts..."}},
     ... generate exactly 5 FAQ-style Q&A pairs in this format grounded in the extracted facts covering various services like rental and accessories if present ...
  ]
}}
"""

print(f"Prompting AI with category: {business.category}...")
res = client.chat.completions.create(
    model='openai/gpt-oss-20b', 
    messages=[{'role': 'user', 'content': prompt}], 
    response_format={'type': 'json_object'}, 
    temperature=0.3, 
    max_tokens=1500
)

output_json = json.loads(res.choices[0].message.content)
print(json.dumps(output_json['faqs'], indent=2))
