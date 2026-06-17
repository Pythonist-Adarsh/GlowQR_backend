from groq import Groq
import json
import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

CATEGORY_LANGUAGE_MAP = {
    "restaurant": {
        "place_word": "restaurant",
        "visit_word": "dined",
        "experience_words": ["meal", "food", "dish", "dinner", "lunch"],
        "avoid_words": ["appointment", "session", "treatment", "stay"],
    },
    "cafe / coffee shop": {
        "place_word": "cafe",
        "visit_word": "stopped by",
        "experience_words": ["coffee", "brew", "snack", "pastry", "sitting area"],
        "avoid_words": ["dinner", "meal", "appointment", "session", "treatment"],
    },
    "fast food / qsr": {
        "place_word": "place",
        "visit_word": "grabbed a quick bite at",
        "experience_words": ["order", "combo", "quick meal", "takeaway"],
        "avoid_words": ["dinner", "appointment", "session", "treatment"],
    },
    "bar / lounge": {
        "place_word": "lounge",
        "visit_word": "visited",
        "experience_words": ["drinks", "cocktails", "vibe", "music", "crowd"],
        "avoid_words": ["meal", "appointment", "session", "treatment"],
    },
    "bakery / dessert shop": {
        "place_word": "bakery",
        "visit_word": "visited",
        "experience_words": ["dessert", "cake", "pastry", "sweet", "baked goods"],
        "avoid_words": ["dinner", "appointment", "session", "treatment"],
    },
    "food court": {
        "place_word": "food court",
        "visit_word": "visited",
        "experience_words": ["stall", "counter", "food", "order", "variety", "quick bite"],
        "avoid_words": ["dinner reservation", "appointment", "session", "treatment", "restaurant"],
    },
    "fine dining": {
        "place_word": "restaurant",
        "visit_word": "dined",
        "experience_words": ["course", "plating", "ambiance", "wine", "reservation"],
        "avoid_words": ["appointment", "session", "treatment", "quick bite"],
    },
    "food truck": {
        "place_word": "food truck",
        "visit_word": "stopped by",
        "experience_words": ["street food", "quick bite", "fresh off the truck", "order"],
        "avoid_words": ["dinner", "reservation", "appointment", "session", "restaurant"],
    },
    "cloud kitchen": {
        "place_word": "place",
        "visit_word": "ordered from",
        "experience_words": ["delivery", "packaging", "order", "food", "arrived hot"],
        "avoid_words": ["ambiance", "seating", "appointment", "session", "treatment"],
    },
    "salon": {
        "place_word": "salon",
        "visit_word": "visited",
        "experience_words": ["haircut", "styling", "color", "treatment", "stylist", "blow dry"],
        "avoid_words": ["food", "meal", "dinner", "dish", "order"],
    },
    "spa": {
        "place_word": "spa",
        "visit_word": "visited",
        "experience_words": ["massage", "treatment", "relaxing session", "therapist", "ambiance"],
        "avoid_words": ["food", "meal", "dinner", "dish", "order", "haircut"],
    },
    "gym": {
        "place_word": "gym",
        "visit_word": "joined",
        "experience_words": ["equipment", "trainer", "workout", "session", "facilities"],
        "avoid_words": ["food", "meal", "dinner", "dish", "order", "haircut"],
    },
    "retail": {
        "place_word": "store",
        "visit_word": "shopped at",
        "experience_words": ["product", "collection", "staff helped", "variety", "purchase"],
        "avoid_words": ["food", "meal", "dinner", "dish", "appointment", "treatment"],
    },
    "bridal & festive jewellery": {
        "place_word": "store",
        "visit_word": "visited",
        "experience_words": ["collection", "jewellery", "designs", "staff helped", "occasion"],
        "avoid_words": ["food", "meal", "dinner", "dish", "treatment"],
    },
    "hotel": {
        "place_word": "hotel",
        "visit_word": "stayed at",
        "experience_words": ["room", "stay", "check-in", "housekeeping", "facilities"],
        "avoid_words": ["appointment", "session", "haircut", "treatment"],
    },
    "medical": {
        "place_word": "clinic",
        "visit_word": "visited",
        "experience_words": ["doctor", "staff", "consultation", "waiting time", "cleanliness"],
        "avoid_words": ["food", "meal", "dinner", "dish", "haircut"],
    },
    "education": {
        "place_word": "institute",
        "visit_word": "enrolled at",
        "experience_words": ["faculty", "course", "classes", "learning", "environment"],
        "avoid_words": ["food", "meal", "dinner", "dish", "treatment", "haircut"],
    },
    "other": {
        "place_word": "place",
        "visit_word": "visited",
        "experience_words": ["service", "staff", "experience", "quality", "value"],
        "avoid_words": [],
    },
}

def get_category_context(category: str) -> dict:
    if not category:
        return CATEGORY_LANGUAGE_MAP["other"]
    category_lower = category.lower().strip()
    if category_lower in CATEGORY_LANGUAGE_MAP:
        return CATEGORY_LANGUAGE_MAP[category_lower]
    for key in CATEGORY_LANGUAGE_MAP:
        if key in category_lower or category_lower in key:
            return CATEGORY_LANGUAGE_MAP[key]
    return CATEGORY_LANGUAGE_MAP["other"]

SYSTEM_PROMPT = """You are generating Google reviews on behalf of real customers for a local Indian business.

GOAL: Every review must feel like a DIFFERENT real human typed it on their phone after genuinely visiting.

BANNED WORDS — NEVER use these:
amazing, fantastic, outstanding, exceptional, stellar, top-notch, world-class, incredible, superb, awesome, wonderful, brilliant, excellent, perfect, fabulous, "must try", "new favorite", "will definitely come back", "highly recommend", "great place", "best place", "loved it", "so good", "so tasty"

PERSONALITY MATRIX — each review is a different human:
Review 1 → BRIEF & CASUAL: 1-2 short sentences only. Like a busy person leaving a quick note.
Review 2 → STORYTELLER: Mentions occasion or context (birthday, lunch break, date night, came with friends). 3-4 sentences with one small personal detail.
Review 3 → SLIGHTLY CRITICAL but positive overall: Mentions ONE small neutral thing (waited a bit, was crowded, parking was tricky) but still recommends. Most natural-sounding review.
Review 4 → FOOD-FOCUSED: Talks about specific taste/texture/presentation. Does NOT mention city name at all.
Review 5 → SERVICE/VIBE-FOCUSED: Talks about staff, ambiance, seating, speed. Does NOT mention any specific dish.

ANTI-SPAM RULES — Google filter ke liye:
1. City name: mention in MAX 2 out of 5 reviews — never in every review
2. Business name: use in MAX 3 out of 5 reviews — others say "this place" or "they"
3. Dish names: each dish mentioned MAX once across all 5 reviews
4. Sentence starters: all 5 must start with a different word — no two reviews same opening
5. Length variation: mix 1-sentence, 2-sentence, 3-4 sentence reviews — never all same length
6. Zero repeated phrases across the 5 reviews
7. If rating is 4/5 — at least 1 review mentions something slightly imperfect naturally
8. SEO keywords (location/category) only in reviews 4 or 5, woven naturally

CATEGORY-SPECIFIC LANGUAGE — HIGHEST PRIORITY RULE:
- You will receive a place_word in every request indicating the exact business type
- The word "restaurant" must NEVER appear in any review unless place_word is literally "restaurant"
- The words "dinner" and "lunch" must NEVER appear unless place_word is "restaurant" or "fine dining"
- Always use the exact place_word provided — if place_word is "food court", write "food court" everywhere, never "restaurant"
- This rule overrides everything else — no exceptions whatsoever
"""

def get_fallback_review(business_name: str, language: str, index: int) -> str:
    name = business_name or 'this place'
    fallbacks = {
        'english': [
            f"Came here on a whim and left happy. {name} is worth the visit.",
            f"Service was quick and the food was fresh. Pretty good overall.",
            f"Decent spot. Was a bit busy when we went but the food made up for the wait.",
            f"Tried a few things off the menu — most were solid. Will probably stop by again.",
            f"Nice place to hang out. Staff were friendly and didn't rush us."
        ],
        'hinglish': [
            f"{name} ne genuinely surprise kar diya. Khana fresh tha aur price bhi reasonable.",
            f"Service thodi slow thi but khana worth it tha. Overall experience acha raha.",
            f"Friends ke saath gaye the, sab ko pasand aaya. Dobara jaenge.",
            f"Taste mein koi compromise nahi. Ek baar try karna chahiye.",
            f"Ambiance acha hai, staff helpful tha. Solid evening rahi."
        ]
    }
    options = fallbacks.get(language.lower(), fallbacks['english'])
    return options[index % len(options)]

async def generate_reviews(
    business_name: str,
    category: str,
    overall_rating: int,
    selected_items: list[str],
    plan: str = 'trial',
    city: str = None,
    session_id: str = None,
    **kwargs
) -> list[str]:
    
    business_location = city or "their city"
    cat_ctx = get_category_context(category)
    place_word = cat_ctx["place_word"]
    avoid_str = ", ".join(cat_ctx["avoid_words"]) if cat_ctx["avoid_words"] else "none"
    items_list = selected_items[:3] if selected_items else []
    services_str = ", ".join(items_list) if items_list else "general experience"

    if overall_rating == 5:
        rating_instruction = "All reviews are positive. But vary tone — not everyone is equally enthusiastic."
    elif overall_rating == 4:
        rating_instruction = "Reviews are positive but at least 1 must mention a minor imperfection naturally."
    else:
        rating_instruction = "Reviews are mixed. 2-3 positive, 1-2 mentioning specific issues politely."

    if plan == 'premium':
        user_prompt = f"""
Business Details:
- Name: {business_name}
- Category: {category}
- City: {business_location}
- Menu items to reference (use sparingly, max once each): {services_str}
- Session seed (do not output): {session_id}
- Customer rating: {overall_rating}/5

{rating_instruction}

CATEGORY RULES — STRICTLY FOLLOW (NO EXCEPTIONS):
⚠️ OVERRIDE: place_word = "{place_word}" — use this exact word in all reviews, the word "restaurant" is completely forbidden in this entire response unless place_word is restaurant
- This business is a "{category}" — it is a {place_word}
- The word "restaurant" is COMPLETELY BANNED in all reviews unless {place_word} is literally "restaurant"
- The word "dinner" is COMPLETELY BANNED in all reviews unless {place_word} is "restaurant" or "fine dining"
- NEVER use these words in ANY of the reviews: {avoid_str}
- Every review must sound like a real customer of a {place_word} — not a restaurant customer
- SEO phrase in Review 4 must be exactly: "best {place_word} near me"
- SEO phrase in Review 5 must be exactly: "best {place_word} in {business_location}"

Generate exactly 5 reviews following the PERSONALITY MATRIX:
Review 1 → BRIEF & CASUAL (English)
Review 2 → STORYTELLER (English)
Review 3 → SLIGHTLY CRITICAL but recommends (English)
Review 4 → FOOD-FOCUSED, NO city name (Hinglish) — include SEO phrase: "best {place_word} near me" — use "{place_word}" word exactly, never "restaurant"
Review 5 → SERVICE/VIBE-FOCUSED, NO dish names (Hinglish) — include SEO phrase: "best {place_word} in {business_location}" — use "{place_word}" word exactly, never "restaurant"

CHECKLIST before outputting:
- No two reviews start with the same word
- City name in MAX 2 reviews
- Business name in MAX 3 reviews
- No dish mentioned more than once across all 5
- No banned words used
- Lengths vary across all 5

Output ONLY a valid JSON array of exactly 5 strings. No explanation, no markdown:
["review1", "review2", "review3", "review4", "review5"]
"""
        variant_count = 5
    else:
        user_prompt = f"""
Business Details:
- Name: {business_name}
- Category: {category}
- City: {business_location}
- Menu items to reference (use sparingly, max once each): {services_str}
- Session seed (do not output): {session_id}
- Customer rating: {overall_rating}/5

{rating_instruction}

CATEGORY RULES — STRICTLY FOLLOW (NO EXCEPTIONS):
⚠️ OVERRIDE: place_word = "{place_word}" — use this exact word in all reviews, the word "restaurant" is completely forbidden in this entire response unless place_word is restaurant
- This business is a "{category}" — it is a {place_word}
- The word "restaurant" is COMPLETELY BANNED in all reviews unless {place_word} is literally "restaurant"
- The word "dinner" is COMPLETELY BANNED in all reviews unless {place_word} is "restaurant" or "fine dining"
- NEVER use these words in ANY of the reviews: {avoid_str}
- Every review must sound like a real customer of a {place_word} — not a restaurant customer
- SEO phrase in Review 4 must be exactly: "best {place_word} near me"
- SEO phrase in Review 5 must be exactly: "best {place_word} in {business_location}"

Generate exactly 3 reviews following the PERSONALITY MATRIX:
Review 1 → BRIEF & CASUAL (English)
Review 2 → STORYTELLER (English)
Review 3 → SLIGHTLY CRITICAL but positive (English)

CHECKLIST before outputting:
- No two reviews start with the same word
- City name in MAX 2 reviews
- Business name in MAX 3 reviews
- No dish mentioned more than once across all 3
- No banned words used
- Lengths vary across all 3

Output ONLY a valid JSON array of exactly 3 strings. No explanation, no markdown:
["review1", "review2", "review3"]
"""
        variant_count = 3

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.95,
            max_tokens=1800
        )
        text = response.choices[0].message.content.strip()
        
        import re
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        text = text.replace('```json', '').replace('```', '').strip()
        
        try:
            parsed = json.loads(text)
            variants = parsed if isinstance(parsed, list) else []
        except Exception as e:
            print(f"Failed to parse JSON from Groq: {e}\nRaw Text: {text}")
            variants = []
        
        cleaned = [v.strip() for v in variants if isinstance(v, str) and len(v.strip()) > 10]
        
        while len(cleaned) < variant_count:
            lang = 'hinglish' if (plan == 'premium' and len(cleaned) >= 3) else 'english'
            cleaned.append(get_fallback_review(business_name, lang, len(cleaned)))
            
        return cleaned[:variant_count]
        
    except Exception as e:
        print(f"Groq error: {e}")
        return [get_fallback_review(business_name, 'hinglish' if (plan == 'premium' and i >= 3) else 'english', i) for i in range(variant_count)]

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
    try:
        if not mime_type or 'pdf' in mime_type.lower() or 'octet-stream' in mime_type.lower():
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if len(doc) > 0:
                    page = doc[0]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    file_bytes = pix.tobytes("jpeg")
            except Exception as e:
                print(f"PDF conversion skipped/failed: {e}")

        import base64
        b64_image = base64.b64encode(file_bytes).decode('utf-8')
        
        prompt = """Extract all menu items and return ONLY this JSON, no markdown:
{
  "highlightDishes": "string",
  "signatureDish": "string",
  "menuCategories": [
    {
      "category": "string",
      "items": [
        {
          "id": 1,
          "name": "string",
          "emoji": "🍔",
          "price": "string or null"
        }
      ]
    }
  ]
}
Rules: ONLY JSON, no code blocks, clean item names, keep currency symbols, never empty menuCategories."""

        response = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ],
            temperature=0.1,
            max_tokens=2500
        )
        
        text = response.choices[0].message.content.strip()
        
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
        
    except Exception as e:
        import traceback
        print(f"Menu Extraction Error: {e}")
        traceback.print_exc()
        return {
            "highlightDishes": "Sample Dish",
            "signatureDish": "Sample Signature",
            "menuCategories": [],
            "error": str(e)
        }
