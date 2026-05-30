from groq import Groq
import json
import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

BANNED_PATTERNS = [
    "highly recommend", "must visit", "must try", "hidden gem",
    "best in", "highly suggest", "10/10", "5 stars",
    "outstanding service", "exceptional", "world-class", "phenomenal",
    "culinary journey", "gastronomic experience", "delightful ambiance",
    "impeccable service", "exquisite", "delectable",
]

POSITIVE_WORD_POOL = [
    "solid", "decent", "pretty good", "good", "nice", "enjoyable",
    "satisfying", "well-made", "flavorful", "tasty", "fresh",
    "worth it", "would return", "comes back", "recommend to friends",
    "liked it", "quite good", "not bad at all"
]

HINGLISH_FILLER_POOL = [
    "yaar", "bhai", "sach mein", "honestly", "ek dum",
    "bilkul", "sahi mein", "theek hai", "mast", "solid",
    "acha tha", "maja aaya", "time waste nahi tha"
]

SYSTEM_PROMPT_FREE = """You write authentic Google reviews for Indian local businesses.
You help customers express their genuine experience in words.

HARD RULES (never break these):
- No Reviews will be same for business at condition  
- No hashtags (#) anywhere
- No emojis anywhere  
- No promotional language ("must visit", "best in city", "hidden gem")
- No superlatives unless customer gave 5 stars ("best", "amazing" only for 5★)
- Never mention discounts, offers, or free items
- Never use the phrase "highly recommend" — too generic, Google flags it
- Maximum 1 mention of business name per review
- Reviews must sound like a real customer wrote them on their phone

QUALITY FLOOR for free tier:
- 2-3 sentences only
- Mention 1-2 dishes from what customer selected
- Include overall rating sentiment naturally
- Generic enough to feel real but specific enough to be useful"""

SYSTEM_PROMPT_BASIC = """You write authentic Google reviews for Indian local businesses.
You help customers express their genuine dining/service experience in words.
You write like real Indians write reviews — not like a marketing brochure.

HARD RULES:
- No hashtags (#) anywhere
- No emojis anywhere
- No "highly recommend" (too templated)
- No "hidden gem", "must visit", "best kept secret"
- No mentions of discounts or free items
- Business name appears maximum ONCE and naturally
- Never start two variants with the same word
- No perfect grammar — slight natural imperfections are good
  ("The food were really good" is more human than "The food was exceptional")

INDIAN AUTHENTICITY RULES:
- People say "the food" not "the cuisine"
- People say "staff" or "service" not "personnel" or "hospitality"  
- People reference specific context: "came with family", "office lunch", "quick bite"
- Price consciousness is real: "worth the price", "a bit expensive but quality mila"
- Real complaints even in good reviews: "parking thoda mushkil tha but khana acha tha"
- Indian naming: "didi", "bhaiya" for staff mentions (if service is mentioned)

SEO RULES (natural insertion, never forced):
- Include city OR area name once if it fits naturally
  GOOD: "Best biryani I've had in Hazratganj"
  BAD: "Best biryani in Lucknow Hazratganj Uttar Pradesh"
- Include category keyword once naturally
  GOOD: "This cafe has become my go-to"
  BAD: "This restaurant cafe eatery in Lucknow"
"""

SYSTEM_PROMPT_PREMIUM = """You are an expert at writing authentic Indian customer reviews for Google Maps.
You understand how real Indians write reviews — the mixture of pride, directness,
price-consciousness, and community trust that defines Indian consumer voice.

Your reviews help genuine customers articulate their real experience.

ABSOLUTE RULES (Google spam detection avoidance):
1. No hashtags. No emojis. No exclamation marks more than once per review.
2. Never use: "highly recommend", "hidden gem", "must try", "best in the city",
   "mind-blowing", "outstanding", "exceptional", "5 stars" (they're already giving stars)
3. Business name appears ONCE maximum. Naturally. Never in first sentence.
4. No keyword clusters: never write "[city] [area] [category] [business name]" near each other
5. Every review must have at least ONE specific detail only that customer could know
   (the dish they ordered, the seating, the wait, the occasion)
6. No copy-paste feel: each of the 5 variants must open differently, end differently,
   and use different vocabulary to describe similar experiences

HUMAN IMPERFECTION RULES (critical for authenticity):
- Occasionally use "the food were" instead of "was" (Indian English pattern)
- Use "only" as filler: "It was good only", "Service was fast only"
- Use "na" or "nahi" in Hinglish: "bilkul theek hai na"
- Varying sentence length: mix short punchy sentences with longer ones
- Occasional topic shift: "Food was great. Parking is a nightmare though."

INDIAN CONTEXT RULES:
- Reference occasion: "anniversary dinner", "team lunch", "family outing on Sunday"
- Price relativity: "₹400 per head is fair for this area"
- Comparison awareness: "Better than [vague comparison, no competitor names]"
- Trust signals: mention if a friend/colleague recommended (makes it social proof)
- Staff interaction: "the waiter was helpful" or "bhaiya ne suggest kiya [dish]"

SEO STRATEGY (built-in naturally):
Primary keyword (use in 2-3 of 5 variants):
  → [category] in [city/area]  e.g. "cafe in Gomti Nagar"
  
Secondary keyword (use in 1-2 variants):
  → [signature_dish] / [cuisine_speciality]  
  
Long-tail (use in 1 variant only):
  → "[meal_type] place in [area]"  e.g. "good lunch spot in Hazratganj"

ROTATION RULE:
The 5 variants must use these 5 different openers (one each):
  1. Occasion-based: "Came here for [meal_type/occasion]..."
  2. Item-first: "The [dish] here is..."  
  3. Verdict-first: "[Positive/Mixed adjective] experience at [business]..."
  4. Comparison: "Finally found a [category] that..."
  5. Context: "Been meaning to try this place..."
"""

rating_guidance_map = {
    5: """Overall 5/5: Customer loved it. All aspects were positive.
          Use: warmth, genuine satisfaction, clear return intent.
          Avoid: over-the-top superlatives. Specificity > enthusiasm.""",
    
    4: """Overall 4/5: Good experience with minor room for improvement.
          Use: praise the highlight, note one thing that could be better (gently).
          Structure: 'Great [X], though [Y] could improve. Would return for [Z].'
          This pattern is most trusted by Google — balanced reviews get more helpful votes.""",
    
    3: """Overall 3/5: Mixed. Something was good, something wasn't.
          Use: honest mixed tone. Don't sugarcoat but don't be harsh.
          This still goes to Google (3★ is okay). 
          Structure: '[Positive aspect] tha/was good. [Negative aspect] could improve.'
          End neutrally — no strong return intent, no strong rejection."""
}

def build_free_prompt(business_data, customer_data, selected_items):
    return f"""
Customer visited: {business_data.get('name')} in {business_data.get('city') or 'their city'}
They ordered: {', '.join(selected_items[:2])}
Overall rating: {customer_data.get('overall_rating', 4)}/5
Language: English

Generate 3 short (2-3 sentence) Google review drafts.
Each must sound like a different person wrote it.
Base the sentiment on the {customer_data.get('overall_rating', 4)}/5 rating.

Return ONLY a JSON object with a 'reviews' array containing the 3 strings. Like this: {{"reviews": ["rev1", "rev2", "rev3"]}}
"""

def build_basic_prompt(business_data, customer_data, selected_items, language):
    area_locality = business_data.get('area', '')
    city = business_data.get('city', '')
    return f"""
Business: {business_data.get('name')}
Location: {area_locality or city}
Type: {business_data.get('category', 'business')}
Customer context:
  - Ordered: {', '.join(selected_items)}
  - Meal: {customer_data.get('meal_type') or 'not specified'}  
  - Spent: {customer_data.get('price_range') or 'not specified'} per person
  - Seating: {customer_data.get('seating_type') or 'not specified'}
  - Wait time: {customer_data.get('wait_time') or 'not specified'}
Ratings given:
  - Overall: {customer_data.get('overall_rating', 4)}/5
  {f"- Food: {customer_data.get('food_rating')}/5" if customer_data.get('food_rating') else ''}
  {f"- Service: {customer_data.get('service_rating')}/5" if customer_data.get('service_rating') else ''}
  {f"- Atmosphere: {customer_data.get('atmosphere_rating')}/5" if customer_data.get('atmosphere_rating') else ''}
Language: {language}

Generate 3 Google review drafts.
Rules:
- Each variant must have a DIFFERENT OPENING (no variant starts with same word)
- Reflect the actual ratings — if service was 2/5, don't praise the service
- 3-4 sentences each
- Include {area_locality or city} naturally in ONE variant only
- Tone variety: Variant 1=casual, Variant 2=detailed, Variant 3=brief

Return ONLY a JSON object with a 'reviews' array containing the 3 strings. Like this: {{"reviews": ["rev1", "rev2", "rev3"]}}
"""

def build_premium_prompt(business_data, customer_data, selected_items, language, rating_guidance):
    area_locality = business_data.get('area', '')
    city = business_data.get('city', '')
    return f"""
Business: {business_data.get('name')}
Location: {area_locality}, {city}
Business type: {business_data.get('category', 'business')}
Cuisine: not specified
Tagline: {business_data.get('tagline') or 'not specified'}
Signature dish: {business_data.get('signature_dish') or 'not specified'}

Customer's full experience:
  - Ordered: {', '.join(selected_items)}
  - Meal occasion: {customer_data.get('meal_type') or 'not specified'}
  - Seating: {customer_data.get('seating_type') or 'dine-in'}  
  - Spent: {customer_data.get('price_range') or 'not specified'} per person
  - Wait time: {customer_data.get('wait_time') or 'normal'}

Ratings (use these to calibrate sentiment — don't mention numbers):
  - Overall: {customer_data.get('overall_rating', 4)}/5
  {f"- Food quality: {customer_data.get('food_rating')}/5" if customer_data.get('food_rating') else ''}
  {f"- Service: {customer_data.get('service_rating')}/5" if customer_data.get('service_rating') else ''}
  {f"- Atmosphere: {customer_data.get('atmosphere_rating')}/5" if customer_data.get('atmosphere_rating') else ''}

Language: {language}

RATING GUIDANCE:
{rating_guidance}

Generate 5 Google review drafts.
Each opener must be from a different category:
  1. occasion-based, 2. item-first, 3. verdict-first, 4. comparison, 5. context

Vary length: 2 short (2-3 sentences), 2 medium (3-4 sentences), 1 longer (4-5 sentences)
Include location keyword ({area_locality or city}) in exactly 2 of the 5 reviews — naturally.
Include {business_data.get('signature_dish') or (selected_items[0] if selected_items else 'the food')} in at least 3 reviews.

Return ONLY a JSON object with a 'reviews' array containing EXACTLY 5 strings. Like this: {{"reviews": ["rev1", "rev2", "rev3", "rev4", "rev5"]}}
"""

def get_fallback_review(business_data: dict, rating: int, language: str) -> str:
    name = business_data.get('name', 'this place')
    fallbacks = {
        5: {
            'english': f"Really enjoyed my time at {name}. Food and service both were good. Will be back.",
            'hindi': f"{name} mein khana bahut acha tha. Service bhi theek rahi. Dobara zaroor aayenge.",
            'hinglish': f"Sach mein, {name} ne disappoint nahi kiya. Khana solid tha. Recommend karunga."
        },
        4: {
            'english': f"Good experience at {name}. Food was well made. Minor things could improve but overall satisfied.",
            'hindi': f"{name} mein experience kaafi theek raha. Khana acha tha. Kuch cheezein aur better ho sakti hain.",
            'hinglish': f"{name} mein khana decent tha. Service thodi slow thi but overall theek raha."
        },
        3: {
            'english': f"Mixed experience at {name}. Some things were good, others need work.",
            'hindi': f"{name} mein kuch cheezein achi thi, kuch nahi. Average experience raha.",
            'hinglish': f"{name} okay tha. Na bahut acha, na bahut bura. Try kar sakte ho."
        }
    }
    rating_key = 5 if rating >= 5 else (4 if rating >= 4 else 3)
    lang_key = language.lower() if language.lower() in fallbacks[rating_key] else 'english'
    return fallbacks[rating_key][lang_key]

async def generate_reviews(
    business_name: str,
    category: str,
    tagline: str | None,
    overall_rating: int,
    food_rating: int | None,
    service_rating: int | None,
    atmosphere_rating: int | None,
    selected_items: list[str],
    signature_dish: str | None,
    meal_type: str | None,
    price_range: str | None,
    language: str,
    variant_count: int,
    plan: str = 'trial',
    seating_type: str = None,
    wait_time: str = None,
    city: str = ""
) -> list[str]:
    
    business_data = {
        'name': business_name,
        'category': category,
        'tagline': tagline,
        'signature_dish': signature_dish,
        'city': city,
        'area': ''
    }
    customer_data = {
        'overall_rating': overall_rating,
        'food_rating': food_rating,
        'service_rating': service_rating,
        'atmosphere_rating': atmosphere_rating,
        'meal_type': meal_type,
        'price_range': price_range,
        'seating_type': seating_type,
        'wait_time': wait_time,
        'selected_items': selected_items,
        'language': language
    }
    
    config = {
        'trial':   { 'variants': 1, 'max_items': 2, 'temp': 0.7, 'max_tokens': 600 },
        'basic':   { 'variants': 3, 'max_items': 5, 'temp': 0.85, 'max_tokens': 900 },
        'premium': { 'variants': 5, 'max_items': 10, 'temp': 0.9, 'max_tokens': 1500 },
    }
    cfg = config.get(plan, config['trial'])
    
    overall = customer_data.get('overall_rating', 4)
    rating_guidance = rating_guidance_map.get(overall, rating_guidance_map[4])
    
    if food_rating and food_rating <= 2:
        rating_guidance += " Do not mention food positively."
    if service_rating and service_rating <= 2:
        rating_guidance += " Do not mention service positively — keep neutral or omit."
    if atmosphere_rating and atmosphere_rating <= 2:
        rating_guidance += " Do not mention ambiance or atmosphere."
    
    system_prompts = {
        'trial': SYSTEM_PROMPT_FREE,
        'basic': SYSTEM_PROMPT_BASIC,
        'premium': SYSTEM_PROMPT_PREMIUM
    }
    system = system_prompts.get(plan, SYSTEM_PROMPT_FREE)
    
    selected_items = customer_data.get('selected_items', [])[:cfg['max_items']]
    language = customer_data.get('language', 'english')
    
    if plan == 'trial':
        user_msg = build_free_prompt(business_data, customer_data, selected_items)
    elif plan == 'basic':
        user_msg = build_basic_prompt(business_data, customer_data, selected_items, language)
    else:
        user_msg = build_premium_prompt(business_data, customer_data, selected_items, language, rating_guidance)
    
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg}
            ],
            temperature=cfg['temp'],
            max_tokens=cfg['max_tokens']
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        try:
            parsed = json.loads(text)
            variants = parsed.get('reviews', []) if isinstance(parsed, dict) else parsed
            if not isinstance(variants, list):
                variants = []
        except Exception as e:
            print(f"Failed to parse JSON from Groq: {e}\nRaw Text: {text}")
            variants = []
        
        cleaned = []
        for v in variants[:cfg['variants']]:
            for banned in BANNED_PATTERNS:
                v = v.replace(banned, '').replace(banned.capitalize(), '')
            v = v.strip()
            if len(v) > 20: 
                cleaned.append(v)
        
        while len(cleaned) < cfg['variants']:
            cleaned.append(get_fallback_review(business_data, overall, language))
            
        return cleaned[:cfg['variants']]
        
    except Exception as e:
        print(f"Groq error: {e}")
        return [get_fallback_review(business_data, overall, language) for _ in range(cfg['variants'])]

async def generate_business_insights(data: dict) -> list[dict]:
    prompt = f"""You are a business advisor for Indian local businesses. Be specific and data-driven.

Business: {data.get('name')} ({data.get('category')}) in {data.get('city', 'India')}
Data: Last 90 days

Rating averages (out of 5):
Overall: {data.get('avg_overall', 0)}, Food: {data.get('avg_food', 0)}, 
Service: {data.get('avg_service', 0)}, Atmosphere: {data.get('avg_atmosphere', 0)}

Worst time slots: {json.dumps(data.get('worst_slots', []))}
Negative keywords: {', '.join(data.get('negative_keywords', []))}
Top items: {', '.join(data.get('top_items', []))}
Funnel: Scan->Open {data.get('scan_to_open', 0)}%, Open->Copy {data.get('open_to_copy', 0)}%

Return ONLY JSON array (3-5 insights). Structure:
[{{"severity":"red|yellow|green","area":"string","problem":"string","evidence":"string","action":"string"}}]"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1500
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Groq insights error: {e}")
        return []

async def extract_menu_from_image(file_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    prompt = """You are an expert menu data extractor. Extract the menu items from the attached image/document.
Format the output EXACTLY as this JSON structure:
{
    "highlightDishes": "Dish1\\nDish2\\nDish3\\nDish4",
    "signatureDish": "Best Dish",
    "menuCategories": [
    {
        "category": "Category Name",
        "items": [
        { "id": 1, "name": "Item Name", "emoji": "🍔", "price": "₹200" }
        ]
    }
    ]
}

Rules:
- 'highlightDishes' should be a string of 3-4 popular dishes separated by newlines.
- 'signatureDish' should be one standout dish.
- 'menuCategories' groups items by their category (e.g., Starters, Mains).
- Ensure all 'id' fields are unique integers across the entire menu.
- Generate appropriate emojis for each dish.
- Return ONLY valid JSON, do not wrap in markdown like ```json.
"""
    try:
        if mime_type == "application/pdf":
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            text_content = ""
            for page in doc:
                text_content += page.get_text() + "\n"
            
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Here is the text extracted from the menu PDF:\n\n{text_content}"}
                ],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
        else:
            base64_image = base64.b64encode(file_bytes).decode('utf-8')
            response = client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.2,
                max_tokens=1500
            )
            
        text = response.choices[0].message.content.strip()
        
        # Try to find JSON block using regex if the model is chatty
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Groq Extraction error: {e}")
        return {
            "highlightDishes": "Sample Dish",
            "signatureDish": "Sample Signature",
            "menuCategories": []
        }
