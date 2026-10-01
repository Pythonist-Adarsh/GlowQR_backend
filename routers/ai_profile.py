from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from database import get_db
import models
import models_ai
from services.groq_service import client
import json
import logging

router = APIRouter(prefix="/ai-profile", tags=["AI Profile"])

@router.post("/extract")
async def extract_ai_profile(db: Session = Depends(get_db)):
    # House of Aadayein only
    business = db.query(models.Business).filter(models.Business.name.ilike("%House of Aadayein%")).first()
    if not business:
        raise HTTPException(status_code=404, detail="House of Aadayein business not found")
        
    reviews = db.query(models.ScanEvent.review_text).filter(
        models.ScanEvent.business_id == business.id,
        models.ScanEvent.review_text.isnot(None),
        models.ScanEvent.review_text != ''
    ).all()
    
    review_texts = [r[0] for r in reviews]
    if not review_texts:
        raise HTTPException(status_code=400, detail="No reviews found to extract")
        
    combined_reviews = "\n- ".join(review_texts)
    
    prompt = f"""
    You are an expert AI data extractor. Extract rich structured context from the following customer reviews for "House of Aadayein", which is categorized as "{business.category}".
    
    Reviews:
    - {combined_reviews}
    
    Extract specific facts from these reviews. DO NOT FABRICATE ANYTHING. Only use what is present in the reviews.
    Important: When selecting themes for the FAQs, explicitly consider the full business category ("{business.category}"). Ensure the FAQs naturally surface topics like handbags, bridal lehenga rental, and fashion accessories (not just jewellery) IF the underlying reviews actually support those themes. Do not fabricate topics if they are not grounded in real data.
    
    Output ONLY a valid JSON object with the following structure exactly. Do not include markdown blocks or any other text.
    {{
      "dishes_mentioned": ["list of specific products/services mentioned (e.g. bridal lehengas, handbags, jewellery)"],
      "occasions": ["weddings", "celebration", etc.],
      "praise_points": ["staff behavior", "collection variety", "value", etc. with specific details from reviews"],
      "comparisons": ["any comparisons to other places if mentioned"],
      "location_references": ["location or area references"],
      "faqs": [
         {{"q": "Example question 1", "a": "Example answer 1"}},
         {{"q": "Example question 2", "a": "Example answer 2"}},
         {{"q": "Example question 3", "a": "Example answer 3"}},
         {{"q": "Example question 4", "a": "Example answer 4"}},
         {{"q": "Example question 5", "a": "Example answer 5"}}
      ]
    }}
    """
    
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        
        extracted_data = json.loads(text)
        
        faqs = extracted_data.pop("faqs", [])
        
        profile = db.query(models_ai.BusinessAIProfile).filter(models_ai.BusinessAIProfile.business_id == business.id).first()
        if not profile:
            profile = models_ai.BusinessAIProfile(
                business_id=business.id,
                slug=business.slug,
                is_published=True
            )
            db.add(profile)
            
        profile.faq_json = faqs
        profile.structured_facts_json = extracted_data
        db.commit()
        
        return {"success": True, "message": "Extracted facts and FAQs successfully", "faq_count": len(faqs)}
        
    except Exception as e:
        logging.error(f"Error extracting AI profile: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{slug}")
async def get_ai_profile(slug: str, db: Session = Depends(get_db)):
    profile = db.query(models_ai.BusinessAIProfile).filter(
        models_ai.BusinessAIProfile.slug == slug,
        models_ai.BusinessAIProfile.is_published == True
    ).first()
    
    if not profile:
        raise HTTPException(status_code=404, detail="AI profile not found")
        
    business = db.query(models.Business).filter(models.Business.id == profile.business_id).first()
    if not business:
        raise HTTPException(status_code=404, detail="Business not found")
        
    return {
        "business": {
            "name": business.name,
            "category": business.category,
            "address": business.address,
            "area_locality": business.area_locality,
            "city": business.city,
            "state": business.state,
            "pincode": business.pincode,
            "business_hours": business.business_hours,
            "google_review_url": business.google_review_url
        },
        "faq_json": profile.faq_json,
        "structured_facts": profile.structured_facts_json,
        "summary_text": profile.summary_text,
        "last_generated_at": profile.last_generated_at
    }
