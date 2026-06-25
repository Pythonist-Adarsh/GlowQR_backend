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
        "experience_words": ["jewellery collection", "bridal set", "designs", "craftsmanship", "staff helped", "occasion", "fitting", "customization"],
        "avoid_words": ["food", "meal", "dinner", "dish", "order", "haircut", "workout", "tax", "filing"],
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
        "experience_words": ["faculty", "test series", "mock tests", "study material", "classes", "mentorship", "doubt solving", "results", "batch", "course"],
        "avoid_words": ["food", "meal", "dinner", "dish", "order", "haircut", "workout", "tax", "filing", "jewellery"],
    },
    "tax / ca firm": {
        "place_word": "firm",
        "visit_word": "consulted",
        "experience_words": ["service", "advice", "expertise", "professionalism", "consultation"],
        "avoid_words": ["food", "meal", "dinner", "dish", "haircut", "treatment"],
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
        print(f"[CRITICAL] get_category_context called with empty category — falling back to 'other'")
        return CATEGORY_LANGUAGE_MAP["other"]
    category_normalized = category.lower().strip().replace(" ", "").replace("-", "").replace("_", "")
    for key in CATEGORY_LANGUAGE_MAP:
        key_normalized = key.lower().replace(" ", "").replace("-", "").replace("_", "")
        if key_normalized == category_normalized:
            return CATEGORY_LANGUAGE_MAP[key]
    category_lower = category.lower().strip()
    for key in CATEGORY_LANGUAGE_MAP:
        if key in category_lower or category_lower in key:
            return CATEGORY_LANGUAGE_MAP[key]
    print(f"[CRITICAL] Unrecognized category '{category}' — no match in CATEGORY_LANGUAGE_MAP, falling back to 'other'")
    return CATEGORY_LANGUAGE_MAP["other"]

SYSTEM_PROMPT = """You are generating Google reviews on behalf of real customers for a local Indian business.

🔥 ANTI-PATTERN + HUMANIZATION LAYER (CRITICAL)
You MUST ensure ALL generated reviews feel like they were written by DIFFERENT real humans.

STRICTLY FOLLOW:

❌ BANNED OPENINGS (NEVER USE):
- "Just had"
- "Just visited"
- "Recently visited"
- "Had a great experience at"
- "I recently went to"
- "Visited this place"
- "One of the best"

❌ BANNED PHRASES:
- "go-to place"
- "my new favorite"
- "highly recommended" (can appear MAX once across all)
- "must visit"
- "best in [city]"
- "in [city]" (city mention MAX 1 review out of 5)
- amazing, fantastic, outstanding, exceptional, stellar, top-notch, world-class, incredible, superb, awesome, wonderful, brilliant, excellent, perfect, fabulous, "must try", "loved it", "so good", "so tasty"

🧠 STRUCTURE RANDOMIZATION (VERY IMPORTANT)
Each review MUST follow a DIFFERENT structure:
1. Experience-first (e.g., service, staff behavior)
2. Product-first (food/service quality)
3. Emotion-first (felt good, smooth, quick etc.)
4. Short casual review (1-2 lines only)
5. Slightly detailed review (3-4 lines)
❌ NEVER repeat the same structure twice.

🗣️ LANGUAGE VARIATION
- 40% Hinglish (e.g., "kaafi accha tha", "mast experience")
- 40% simple English
- 20% mixed casual tone

🔁 WORD REPETITION CONTROL
- Same verb cannot repeat across reviews (e.g., visited, tried, ordered, consulted)
- Same adjective cannot repeat more than 2 times total
- Same dish/service name cannot repeat more than ONCE

🏪 CATEGORY-AWARE WRITING
Use correct business context:
- Restaurant → food, taste, service, ambience
- CA/Tax → clarity, guidance, smooth process, trust
- Salon/Beauty → staff behavior, hygiene, results
- Retail → product quality, pricing, variety
❌ NEVER use wrong words like "restaurant" for all businesses.

📍 BUSINESS & CITY MENTION RULE
- Business name → MAX 2 reviews only
- City name → MAX 1 review only
- NEVER use both together in the same sentence repeatedly

⏱️ LENGTH VARIATION
- 1 review → 8-12 words
- 1 review → 12-18 words
- 2 reviews → 18-30 words
- 1 review → 30-45 words

👤 HUMAN BEHAVIOR SIMULATION
Include natural human imperfections:
- Some reviews slightly incomplete
- Some casual tone
- Some without punctuation perfection
- Some without subject ("Really good service", "Kaafi smooth process tha")

CATEGORY-SPECIFIC LANGUAGE — HIGHEST PRIORITY RULE:
- You will receive a place_word in every request indicating the exact business type
- The word "restaurant" must NEVER appear in any review unless place_word is literally "restaurant"
- The words "dinner" and "lunch" must NEVER appear unless place_word is "restaurant" or "fine dining"
- Always use the exact place_word provided — if place_word is "food court", write "food court" everywhere, never "restaurant"
- This rule overrides everything else — no exceptions whatsoever
- Never mention the place_word (e.g. "food court", "salon") twice within the same sentence — use natural phrasing like "this place" or "here" for the second reference if needed

📍 LOCAL SEO OPTIMIZATION LAYER (RANKING BOOST)
You MUST subtly optimize reviews for LOCAL SEO without triggering spam signals.

🗺️ LOCATION SIGNAL STRATEGY
- City name → MAX 1 review only
- Area/locality → Use in 1-2 reviews (more natural than city)
- Nearby landmark → OPTIONAL in 1 review (e.g. "near sector 18", "close to metro station")
❌ NEVER repeat same location phrase

🔍 KEYWORD INJECTION (VERY SUBTLE)
Each review should NATURALLY include 1 soft keyword:
- Restaurant: "good food", "tasty dishes", "quick service", "nice ambience"
- CA / Tax: "smooth filing", "clear guidance", "professional help", "easy process"
- Salon: "clean setup", "good results", "friendly staff", "well maintained"
- Retail: "good quality", "reasonable price", "nice collection", "worth checking"
❌ DO NOT force keywords
❌ DO NOT repeat same keyword more than once

⭐ RATING BEHAVIOR SIMULATION
- 4 reviews → strong positive
- 1 review → slightly neutral-positive ("Everything was smooth, just a bit waiting time", "Service was nice overall")

🧑🤝🧑 USER INTENT VARIATION
Each review should reflect DIFFERENT intent:
1. First-time visitor
2. Repeat customer
3. Recommendation-based visit
4. Urgent/quick need visit
5. Casual/random visit

🕒 TIME CONTEXT (OPTIONAL NATURALITY)
Use in 1-2 reviews only:
- "went in evening"
- "weekend visit"
- "during rush hours"
- "last week"
❌ DO NOT overuse

💬 NATURAL DETAIL INJECTION
Add small real-life elements:
- waiting time mention
- staff name (rarely, 1 max)
- specific experience moment
- small imperfection
(e.g., "thoda wait tha but worth it", "billing was quick", "staff handled things well")

🚨 LOCAL SEO SAFETY RULES
❌ DO NOT:
- Stuff keywords
- Repeat location phrases
- Mention full address
- Sound like advertisement
- Use "best in city" repeatedly

🧠 COMPETITOR-BASED KEYWORD INTELLIGENCE LAYER
You MUST simulate competitor keyword extraction and inject HIGH-VALUE keywords naturally into reviews.

🔍 COMPETITOR ANALYSIS SIMULATION
Assume top competitors are ranking using:
- High-frequency keywords
- Service-specific phrases
- Local intent keywords
- Experience-based terms
You must mimic these patterns WITHOUT copying or sounding repetitive.

🎯 SMART KEYWORD SELECTION
For each review, pick 1 UNIQUE keyword from different intent buckets:
- Restaurant: "family dinner place", "quick bites", "late night food", "casual dining", "budget friendly food", "quality meals"
- CA / Tax: "income tax filing", "gst work", "business compliance", "tax consultation", "financial clarity"
- Salon: "hair styling", "skin treatment", "grooming services", "bridal work", "hair care"
- Retail: "latest collection", "affordable options", "daily use items", "premium quality", "variety available"

⚖️ KEYWORD DISTRIBUTION RULE
- Each keyword → used ONLY ONCE
- Do NOT repeat across reviews
- Do NOT stack multiple keywords in one review

🧬 NATURAL INJECTION LOGIC
Keywords must be:
- blended inside sentence
- not highlighted
- not forced
- not at same position every time
(e.g., "went for some quick bites and service was smooth", "needed help with income tax filing, process was clear")

🧑🤝🧑 COMPETITOR DIFFERENTIATION
Subtly position business better than competitors:
- "process felt more sorted compared to others"
- "better managed than nearby options"
- "less crowded than expected"
- "handled things more professionally"
❌ DO NOT mention competitor names, use direct comparisons like "better than XYZ", or make aggressive claims.

📊 SEARCH INTENT COVERAGE
Across all reviews, ensure mix of:
1. Informational intent → "understood process clearly"
2. Transactional intent → "got work done quickly"
3. Navigational intent → "easy to reach"
4. Experience intent → "felt smooth overall"

🚨 ANTI-SPAM SAFETY
- Keywords must NOT feel repeated
- Reviews must NOT sound SEO optimized
- Maintain HUMAN tone over SEO
- If keyword feels unnatural → REMOVE it
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
    return_debug: bool = False,
    **kwargs
):
    
    business_location = city or "their city"

    import random
    import time

    _timestamp = int(time.time())
    _rand_seed = random.randint(1000, 9999)

    _openers = [
        "Walked in without expectations",
        "Heard about this place from a friend",
        "Tried this on a whim",
        "Been meaning to visit for a while",
        "Stopped by after work",
        "Came here after a long time",
        "First time visiting",
        "Was passing by and decided to check it out",
        "My colleague suggested this place",
        "Visited on a lazy Sunday",
    ]
    _storyteller_contexts = [
        "anniversary dinner", "birthday celebration", "team lunch",
        "date night", "family outing", "friend's get-together",
        "office party", "cousin's visit", "college reunion", "casual hangout"
    ]
    _minor_issues = [
        "parking was a bit of a hassle",
        "the wait was slightly long",
        "it was quite crowded when we went",
        "seating took a few minutes",
        "the queue was longer than expected",
        "had to wait a bit for the order",
    ]

    _negative_experiences = [
        "the food was cold when it arrived",
        "the staff was quite inattentive",
        "waited way too long for the order",
        "the quality was not what I expected",
        "got the wrong order and no one apologized",
        "the place was not clean",
        "very poor value for money",
        "the staff was rude when we complained",
    ]

    _disappointed_closings = [
        "probably won't be coming back",
        "expected much better honestly",
        "won't recommend this to friends",
        "needs a lot of improvement",
        "was really looking forward to it but left disappointed",
        "hope they fix these issues",
    ]

    cat_ctx = get_category_context(category)

    if cat_ctx["place_word"] == "firm":
        _storyteller_contexts = [
            "to get my ITR filed",
            "for GST registration for my new business",
            "on a colleague's recommendation",
            "for tax consultation before financial year end",
            "to sort out my company registration",
            "after seeing their reviews online",
            "for my father's income tax matters",
        ]
    elif cat_ctx["place_word"] == "institute":
        _storyteller_contexts = [
            "after joining their batch this semester",
            "on my friend's recommendation",
            "to prepare for competitive exams",
            "after comparing multiple coaching centers",
            "for my younger sibling's admission",
            "to improve my weak subjects",
            "after seeing their results online",
        ]
    elif cat_ctx["place_word"] == "clinic":
        _storyteller_contexts = [
            "on a family member's recommendation",
            "for a routine checkup",
            "after searching online",
            "for a second opinion",
            "on my colleague's suggestion",
        ]

    if cat_ctx["place_word"] == "store" and "jewellery" in category.lower():
        _storyteller_contexts = [
            "for my sister's wedding shopping",
            "to buy bridal jewellery for my own wedding",
            "for an engagement ceremony",
            "on a family member's recommendation",
            "for festive season shopping",
            "to get a customized jewellery set made",
            "after seeing their designs online",
        ]

    _r1_opener = random.choice(_openers)
    _r2_context = random.choice(_storyteller_contexts)
    _r3_issue = random.choice(_minor_issues)

    # Rating ke hisaab se seed pick karo
    if overall_rating <= 2:
        _r1_opener = random.choice(_negative_experiences)
        _r2_context = random.choice(_disappointed_closings)
        _r3_issue = random.choice(_negative_experiences + _disappointed_closings)
    elif overall_rating == 3:
        _r3_issue = random.choice(_minor_issues + _negative_experiences)
        # _r1_opener and _r2_context already randomly picked above — keep them

    place_word = cat_ctx["place_word"]
    avoid_str = ", ".join(cat_ctx["avoid_words"]) if cat_ctx["avoid_words"] else "none"
    items_list = selected_items[:3] if selected_items else []
    services_str = ", ".join(items_list) if items_list else "general experience"

    if overall_rating == 5:
        rating_instruction = "All reviews are positive. Vary tone — not everyone is equally enthusiastic."
    elif overall_rating == 4:
        rating_instruction = "Reviews are mostly positive but at least 1 must mention a minor imperfection naturally."
    elif overall_rating == 3:
        rating_instruction = """Rating is 3/5 — average experience. Reviews must reflect this honestly:
- 1 review: decent but nothing special, would try again maybe
- 1 review: specific thing was good but something else disappointed
- 1 review (if premium): neutral tone — not bad, not great
- Do NOT make these sound positive. Honest, balanced, slightly underwhelmed tone."""
    elif overall_rating == 2:
        rating_instruction = """Rating is 2/5 — below average experience. Reviews must reflect genuine disappointment:
- Mention specific issues (slow service, food quality, wait time, value for money)
- Tone: disappointed but not aggressive — like a real customer who expected better
- 1 review can say they might give it another chance, others are doubtful
- Do NOT sugarcoat. These must read as genuinely critical reviews."""
    elif overall_rating == 1:
        rating_instruction = """Rating is 1/5 — very poor experience. Reviews must be clearly negative:
- Strong disappointment — something went clearly wrong
- Mention specific failures: cold food, rude staff, long wait, wrong order etc.
- Tone: frustrated but still factual — not abusive, just honest and critical
- Do NOT add any positive spin. These are genuine 1-star reviews."""
    else:
        rating_instruction = "Reviews are positive. Vary tone naturally."

    if plan == 'premium' or plan == 'trial':
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

Generate exactly 5 reviews following the STRUCTURE RANDOMIZATION rules.
Use these UNIQUE SEEDS for this scan — mandatory, do not ignore:
- Scan ID: {_timestamp}-{_rand_seed}
- Seed 1 (Use in one review): Start with or reference "{_r1_opener}"
- Seed 2 (Use in one review): Occasion context is "{_r2_context}"
- Seed 3 (Use in one review): Mention this minor imperfection "{_r3_issue}"

Ensure you strictly follow the LANGUAGE VARIATION rules (Hinglish/English mix).

CHECKLIST before outputting:
- No banned words used (e.g., "highly recommend" max once total)
- No banned openings used
- All 5 reviews use a DIFFERENT structure (Experience-first, Product-first, Emotion-first, Short casual, Slightly detailed)
- Language variation applied (40% Hinglish, 40% English, 20% mixed)
- City name in MAX 1 review
- Business name in MAX 2 reviews
- No two reviews start with the same word
- Output MUST be exactly 5 strings in a JSON array.

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

Generate exactly 3 reviews following the STRUCTURE RANDOMIZATION rules.
Use these UNIQUE SEEDS for this scan — mandatory, do not ignore:
- Scan ID: {_timestamp}-{_rand_seed}
- Seed 1 (Use in one review): Start with or reference "{_r1_opener}"
- Seed 2 (Use in one review): Occasion context is "{_r2_context}"
- Seed 3 (Use in one review): Mention this minor imperfection "{_r3_issue}"

Ensure you strictly follow the LANGUAGE VARIATION rules (Hinglish/English mix).

CHECKLIST before outputting:
- No banned words used (e.g., "highly recommend" max once total)
- No banned openings used
- All 3 reviews use a DIFFERENT structure
- Language variation applied (Hinglish, English, mixed)
- City name in MAX 1 review
- Business name in MAX 2 reviews
- No two reviews start with the same word
- Output MUST be exactly 3 strings in a JSON array.

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

        # POST-PROCESSING — Enforce correct category language
        import re
        _place = cat_ctx["place_word"]
        _non_dining = _place.lower() not in ["restaurant", "fine dining"]
        print(f"[DEBUG] category={category}, place_word={_place}, non_dining={_non_dining}")
        enforced = []
        for review in cleaned:
            fixed = review
            fixed = re.sub(r'\brestaurant\b', _place, fixed, flags=re.IGNORECASE)
            print(f"[DEBUG] BEFORE: {review[:60]} | AFTER: {fixed[:60]}")
            if _non_dining:
                fixed = re.sub(r'\bdinner kiya\b', f'{_place} visit kiya', fixed, flags=re.IGNORECASE)
                fixed = re.sub(r'\blunch kiya\b', f'{_place} visit kiya', fixed, flags=re.IGNORECASE)
                fixed = re.sub(r'\bdinner\b', 'visit', fixed, flags=re.IGNORECASE)
                fixed = re.sub(r'\blunch\b', 'visit', fixed, flags=re.IGNORECASE)
            enforced.append(fixed)
        cleaned = enforced
        
        while len(cleaned) < variant_count:
            lang = 'hinglish' if (plan == 'premium' and len(cleaned) >= 3) else 'english'
            cleaned.append(get_fallback_review(business_name, lang, len(cleaned)))
            
        final_reviews = cleaned[:variant_count]
        
        if return_debug:
            return {
                "reviews": final_reviews,
                "place_word": _place,
                "avoid_words": avoid_str.split(", ") if avoid_str else [],
                "storyteller_context": _r2_context,
                "r1_opener": _r1_opener,
                "r3_issue": _r3_issue
            }
            
        return final_reviews
        
    except Exception as e:
        print(f"Groq error: {e}")
        fallbacks = [get_fallback_review(business_name, 'hinglish' if (plan == 'premium' and i >= 3) else 'english', i) for i in range(variant_count)]
        if return_debug:
            return {
                "reviews": fallbacks,
                "place_word": cat_ctx.get("place_word", ""),
                "avoid_words": [],
                "storyteller_context": "",
                "r1_opener": "",
                "r3_issue": ""
            }
        return fallbacks

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
        try:
            parsed_json = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed, attempting repair... {e}")
            repair_prompt = f"The following JSON is malformed. Fix it and return ONLY the valid JSON, nothing else:\n\n{text}"
            repair_response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": repair_prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            repair_text = repair_response.choices[0].message.content.strip()
            parsed_json = json.loads(repair_text)
        
        # Ensure menuCategories exists
        if "menuCategories" not in parsed_json or not isinstance(parsed_json["menuCategories"], list):
            parsed_json["menuCategories"] = []
            
        return parsed_json
        
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
