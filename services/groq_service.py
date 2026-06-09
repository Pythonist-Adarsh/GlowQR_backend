from groq import Groq
import json
import os
import base64
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are generating Google reviews on behalf of real customers 
for a local Indian business. 

Your goal is to write reviews that:
1. Sound 100% human — like a real customer typed it on 
   their phone after visiting
2. Are unique every single time — never repeat phrases, 
   structure, or sentence patterns
3. Include natural SEO signals — location, service, 
   category — woven into the review as a human would 
   mention them, not as keywords
4. Pass Google's review authenticity filters
5. Help the business rank locally on Google Maps

STRICT RULES:
- Never use: amazing, fantastic, outstanding, exceptional, 
  stellar, top-notch, world-class, incredible, superb
- Never start all reviews with "I visited" or "I went"
- Vary sentence length — mix short and long sentences
- Include small specific details (time of day, occasion, 
  what they bought, staff name if given, wait time)
- Each review must feel like a DIFFERENT person wrote it
  with a different personality and writing style

Business details you will receive:
- business_name
- business_category  
- business_location (city/area)
- specific_services (if provided)
- session_id (use as randomness seed — never output this)
"""

def get_fallback_review(business_name: str, language: str, index: int) -> str:
    name = business_name or 'this place'
    fallbacks = {
        'english': [
            f"Really enjoyed my time at {name}. Everything was good. Will be back.",
            f"Good experience at {name}. Food and service were solid.",
            f"Visited {name} recently. Nice ambiance and most of what we tried was pretty good.",
            f"A solid choice for dining out. {name} has good portions and fair prices.",
            f"Enjoyed the meal at {name}. Would visit again when in the area."
        ],
        'hinglish': [
            f"{name} mein experience kaafi theek raha. Khana acha tha.",
            f"{name} mein khana decent tha. Service bhi achi thi.",
            f"Sach mein, {name} ne disappoint nahi kiya. Khana solid tha.",
            f"Maza aaya {name} aakar. Worth the price.",
            f"{name} theek hai, try kar sakte ho."
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
    services_str = ", ".join(selected_items) if selected_items else "general service"

    if plan == 'premium':
        user_prompt = f"""
Business Details:
- business_name: {business_name}
- business_category: {category}
- business_location: {business_location}
- specific_services: {services_str}
- session_id: {session_id}

Generate exactly 5 reviews based on an overall rating of {overall_rating}/5.

MIX REQUIRED:
REVIEW 1, 2, 3 — Normal English
- Simple, friendly, easy to understand
- Written for Indian readers — short sentences
- Conversational tone like texting a friend

REVIEW 4 — Hinglish (Hindi + English mix)
- Natural mix like Indian people actually talk
- MUST include local SEO phrase: "best {category} near me"

REVIEW 5 — Hinglish (Hindi + English mix)  
- MUST include location-based SEO phrase: "best {category} in {business_location}"

Output ONLY a JSON array of exactly 5 strings:
["review 1 text", "review 2 text", "review 3 text", "review 4 text", "review 5 text"]
"""
        variant_count = 5
    else:
        user_prompt = f"""
Business Details:
- business_name: {business_name}
- business_category: {category}
- business_location: {business_location}
- specific_services: {services_str}
- session_id: {session_id}

Generate exactly 5 reviews based on an overall rating of {overall_rating}/5.

ALL 5 REVIEWS — Normal English
- Simple, friendly, easy to understand
- Written for Indian readers — short sentences
- Conversational tone like texting a friend

Output ONLY a JSON array of exactly 5 strings:
["review 1 text", "review 2 text", "review 3 text", "review 4 text", "review 5 text"]
"""
        variant_count = 5

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,
            max_tokens=1500
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
