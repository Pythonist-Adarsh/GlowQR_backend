from groq import Groq
import json
import os
import base64
from dotenv import load_dotenv
import time

LAST_RATE_LIMIT_ALERT_TIME = 0

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
    "real estate": {
        "place_word": "agency",
        "visit_word": "consulted",
        "experience_words": ["agent", "property", "deal", "broker", "site visit", "transparent", "registry", "residential", "commercial", "rental", "response time", "follow-up", "documentation turnaround"],
        "avoid_words": ["food", "meal", "dinner", "dish", "haircut", "treatment", "best in the market", "highly recommended service", "smooth and hassle-free experience", "queue", "waiting in line"],
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
- "had breakfast", "had lunch", "had dinner", "went for dinner", "went for lunch" (NEVER mention meal type)
- "indoor seating", "outdoor seating", "sat inside", "sat outside" (NEVER mention seating type)


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
- VERY IMPORTANT: The customer's selected items must be repeated across ALL reviews as instructed. Do NOT avoid repeating the selected item names.

🏪 CATEGORY-AWARE WRITING
Use correct business context:
- Restaurant → food, taste, service, ambience
- CA/Tax → clarity, guidance, smooth process, trust
- Salon/Beauty → staff behavior, hygiene, results
- Retail → product quality, pricing, variety
- Real Estate → professionalism, property genuineness, transparency, site visit, documentation speed
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

📍 LOCAL SEO & KEYWORDS (SUBTLE)
- City name: MAX 1 review only.
- Area/locality: Use in 1-2 reviews.
- Inject 1 soft keyword naturally per review based on category (e.g. "tasty dishes", "smooth process", "clean setup", "genuine property"). 
- DO NOT force keywords, repeat them, or sound like an advertisement. Maintain human tone over SEO.
"""

def get_fallback_review(business_name: str, language: str, index: int, selected_items: list = None) -> str:
    name = business_name or 'this place'
    
    items_str = ", ".join(selected_items) if selected_items else ""

    fallbacks = {
        'english': [
            f"Great experience from start to finish. {name} is worth the visit." + (f" I especially liked the {items_str}." if items_str else ""),
            f"Service was quick and everything was handled professionally. Pretty good overall." + (f" Tried the {items_str} and it was great." if items_str else ""),
            f"Decent place. Was a bit busy when we went but the smooth service made up for the wait." + (f" The {items_str} really stood out." if items_str else ""),
            f"Tried a few things and most were solid. Will probably return again." + (f" Loved the {items_str}." if items_str else ""),
            f"Nice environment. Staff were friendly, helpful, and didn't rush us." + (f" Highly recommend checking out the {items_str}." if items_str else "")
        ],
        'hinglish': [
            f"{name} ne genuinely surprise kar diya. Service achi thi aur price bhi reasonable." + (f" Inka {items_str} zaroor try karna." if items_str else ""),
            f"Thoda wait karna pada but experience worth it tha. Overall sab kuch acha raha." + (f" {items_str} kaafi acha tha." if items_str else ""),
            f"Sab ko yahan aake pasand aaya. Dobara zaroor aana chahenge." + (f" Specially {items_str} ne dil khush kar diya." if items_str else ""),
            f"Quality mein koi compromise nahi. Ek baar try karna chahiye." + (f" {items_str} was amazing." if items_str else ""),
            f"Ambiance acha hai, staff helpful tha. Solid experience raha." + (f" Make sure to ask for {items_str}." if items_str else "")
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
    elif cat_ctx["place_word"] == "agency" and "real estate" in category.lower().replace("_", " "):
        _storyteller_contexts = [
            "to buy a new flat",
            "while looking for a rental property",
            "for a commercial space lease",
            "on a friend's recommendation for property investment",
            "to sell our old property",
            "for a site visit",
            "after seeing their property listings online",
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

    if cat_ctx["place_word"] == "salon":
        _openers = [
            "Finally got the haircut I always wanted...",
            "The stylist really understood what I was looking for...",
            "Such a clean and relaxing atmosphere...",
            "Everyone noticed the change after my visit...",
            "Great quality at a very reasonable price..."
        ]

    if cat_ctx["place_word"] == "gym":
        _openers = [
            "This gym genuinely changed my fitness routine...",
            "The trainers here actually push you in the right way...",
            "Clean equipment, proper AC, no overcrowding...",
            "The energy and crowd here keeps you motivated...",
            "Visible results within weeks of joining..."
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
    items_list = selected_items[:5] if selected_items else []
    services_str = ", ".join(items_list) if items_list else "general experience"
    value_perception = kwargs.get("value_perception", "")

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
- Customer's selected items: {services_str}
- MANDATORY ITEMS RULE: If items are provided above, you MUST naturally mention ALL of them in EVERY SINGLE REVIEW VARIANT. Do NOT just append them as a robotic comma-separated list at the end. Weave them into natural sentences (e.g., 'The [Item 1] was amazing and I really enjoyed the [Item 2]'). Do not skip any item. Do not substitute them.
- Session seed (do not output): {session_id}
- Customer rating: {overall_rating}/5
- Value perception: {value_perception if value_perception else "not specified"} — if specified, mention naturally in exactly 1 review only


{rating_instruction}
- Waiting time context: around 10 minutes — mention naturally in 1 review as a minor imperfection if rating is 4 or below
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
- Customer's selected items: {services_str}
- MANDATORY ITEMS RULE: If items are provided above, you MUST naturally mention ALL of them in EVERY SINGLE REVIEW VARIANT. Do NOT just append them as a robotic comma-separated list at the end. Weave them into natural sentences (e.g., 'The [Item 1] was amazing and I really enjoyed the [Item 2]'). Do not skip any item. Do not substitute them.
- Session seed (do not output): {session_id}
- Customer rating: {overall_rating}/5
- Value perception: {value_perception if value_perception else "not specified"} — if specified, mention naturally in exactly 1 review only
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

    _place = cat_ctx["place_word"]
    _non_dining = _place.lower() not in ["restaurant", "fine dining"]
    print(f"[DEBUG] category={category}, place_word={_place}, non_dining={_non_dining}")

    max_retries = 3
    final_reviews = []
    
    for attempt in range(max_retries):
        try:
            text = ""
            try:
                response = client.chat.completions.create(
                    model="llama-3.1-8b-instant",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.95,
                    max_tokens=1000,
                    timeout=15.0
                )
                text = response.choices[0].message.content
                if text is None:
                    text = ""
                else:
                    text = text.strip()
                if not text:
                    print(f"[DEBUG] Empty text returned! Finish reason: {response.choices[0].finish_reason}, Usage: {response.usage}")
            except Exception as groq_err:
                print(f"[DEBUG] Groq API Failed: {groq_err}")
                together_key = os.environ.get("TOGETHER_API_KEY")
                if together_key:
                    print("[DEBUG] Failing over to Together AI...")
                    import openai
                    together_client = openai.OpenAI(
                        api_key=together_key,
                        base_url="https://api.together.xyz/v1",
                    )
                    response = together_client.chat.completions.create(
                        model="meta-llama/Llama-3.3-70B-Instruct-Turbo",
                        messages=[
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.95,
                        max_tokens=400
                    )
                    text = response.choices[0].message.content.strip()
                else:
                    raise groq_err
            
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

            is_valid = True
            for review in cleaned:
                for item in items_list:
                    if item.lower() not in review.lower():
                        is_valid = False
                        print(f"[DEBUG] Attempt {attempt+1}: Review missing item '{item}': {review[:50]}...")
                        break
                if not is_valid: break
                
            if is_valid and len(cleaned) >= variant_count:
                unique_reviews = set(cleaned)
                if len(unique_reviews) < len(cleaned):
                    print(f"[DEBUG] Attempt {attempt+1}: Found duplicate reviews. Retrying...")
                    is_valid = False

            if not is_valid and attempt < max_retries - 1:
                print(f"[DEBUG] Retrying generation... (Attempt {attempt + 1}/{max_retries})")
                continue
                
            if not is_valid and attempt == max_retries - 1:
                print(f"[CRITICAL WARNING] Review generation failed to include all items or avoid duplicates after {max_retries} attempts.")

            enforced = []
            for review in cleaned:
                fixed = review
                fixed = re.sub(r'\brestaurant\b', _place, fixed, flags=re.IGNORECASE)
                if _non_dining:
                    fixed = re.sub(r'\bdinner kiya\b', f'{_place} visit kiya', fixed, flags=re.IGNORECASE)
                    fixed = re.sub(r'\blunch kiya\b', f'{_place} visit kiya', fixed, flags=re.IGNORECASE)
                    fixed = re.sub(r'\bdinner\b', 'visit', fixed, flags=re.IGNORECASE)
                    fixed = re.sub(r'\blunch\b', 'visit', fixed, flags=re.IGNORECASE)
                enforced.append(fixed)
            cleaned = enforced
            
            while len(cleaned) < variant_count:
                lang = 'hinglish' if (plan == 'premium' and len(cleaned) >= 3) else 'english'
                print("[DEBUG] GROQ_FALLBACK_USED")
                cleaned.append(get_fallback_review(business_name, lang, len(cleaned), selected_items))
                
            final_reviews = cleaned[:variant_count]
            print(f"[DEBUG] GROQ_SUCCESS ({len(cleaned)} AI variants generated)")
            break
            
        except Exception as e:
            print(f"Groq error: {e}")
            if attempt == max_retries - 1:
                if "429" in str(e) or "rate limit" in str(e).lower():
                    global LAST_RATE_LIMIT_ALERT_TIME
                    current_time = time.time()
                    if current_time - LAST_RATE_LIMIT_ALERT_TIME > 3600: # 1 hour throttle
                        try:
                            from backend.services.email_service import send_groq_rate_limit_alert
                            send_groq_rate_limit_alert(business_name, str(e))
                            LAST_RATE_LIMIT_ALERT_TIME = current_time
                        except Exception as email_e:
                            print(f"Failed to send rate limit alert: {email_e}")
                
                print("[DEBUG] GROQ_FALLBACK_USED (Total Groq Failure)")
                fallbacks = [get_fallback_review(business_name, 'hinglish' if (plan == 'premium' and i >= 3) else 'english', i, selected_items) for i in range(variant_count)]
                final_reviews = fallbacks

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
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000
        )
        text = response.choices[0].message.content.strip()
        text = text.replace('```json', '').replace('```', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Groq insights error: {e}")
        return []

async def extract_menu_from_image(file_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    import base64
    images_b64 = []
    try:
        is_pdf = bool(mime_type and ('pdf' in mime_type.lower() or 'octet-stream' in mime_type.lower()))
        if is_pdf:
            try:
                import fitz
                doc = fitz.open(stream=file_bytes, filetype="pdf")
                if len(doc) == 0:
                    raise Exception("Empty PDF")
                for page in doc:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    images_b64.append(base64.b64encode(pix.tobytes("jpeg")).decode('utf-8'))
            except Exception as e:
                print(f"PDF conversion failed: {e}")
                if mime_type and 'pdf' in mime_type.lower():
                    return {
                        "error": "Could not read this PDF — try uploading it as images instead",
                        "menuCategories": [],
                        "highlightDishes": "",
                        "signatureDish": ""
                    }
                else:
                    images_b64 = [base64.b64encode(file_bytes).decode('utf-8')]
        else:
            images_b64 = [base64.b64encode(file_bytes).decode('utf-8')]

        if not images_b64:
            return {"error": "No images found to process", "menuCategories": []}

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

        final_categories = []
        final_signature_dishes = []
        final_highlight_dishes = []
        
        def add_unique_str(collection, item_to_add):
            item_str = str(item_to_add).strip()
            if not item_str: return
            if not any(existing.lower() == item_str.lower() for existing in collection):
                collection.append(item_str)

        for b64_image in images_b64:
            messages_payload = [
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
            ]
            
            try:
                response = client.chat.completions.create(
                    model="meta-llama/llama-4-maverick-17b-128e-instruct",
                    messages=messages_payload,
                    temperature=0.1,
                    max_tokens=2500
                )
            except Exception as e:
                error_str = str(e).lower()
                if "404" in error_str or "does not exist" in error_str or "not found" in error_str:
                    print(f"Maverick failed, falling back to qwen: {e}")
                    response = client.chat.completions.create(
                        model="qwen/qwen3.6-27b",
                        messages=messages_payload,
                        temperature=0.1,
                        max_tokens=2500
                    )
                else:
                    raise e
            
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
                    model="llama-3.1-8b-instant",
                    messages=[{"role": "user", "content": repair_prompt}],
                    temperature=0.1,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                repair_text = repair_response.choices[0].message.content.strip()
                parsed_json = json.loads(repair_text)
            
            sig = parsed_json.get("signatureDish")
            if sig and isinstance(sig, str) and sig.lower() not in ["sample signature", ""]:
                for item in sig.split('\n'):
                    add_unique_str(final_signature_dishes, item)
            
            highlights = parsed_json.get("highlightDishes")
            if highlights and isinstance(highlights, str) and highlights.lower() not in ["sample dish", ""]:
                for item in highlights.split('\n'):
                    add_unique_str(final_highlight_dishes, item)
            
            cats = parsed_json.get("menuCategories", [])
            if isinstance(cats, list):
                for cat in cats:
                    cat_name = cat.get("category", "")
                    if not isinstance(cat_name, str): continue
                    cat_name = cat_name.strip()
                    if not cat_name: continue
                    
                    existing_cat = next((c for c in final_categories if c["category"].lower() == cat_name.lower()), None)
                    if not existing_cat:
                        existing_cat = {"category": cat_name, "items": []}
                        final_categories.append(existing_cat)
                        
                    items = cat.get("items", [])
                    if isinstance(items, list):
                        for item in items:
                            item_name = item.get("name", "")
                            if not isinstance(item_name, str): continue
                            item_name = item_name.strip()
                            if not item_name: continue
                            
                            if not any(i.get("name", "").lower() == item_name.lower() for i in existing_cat["items"]):
                                existing_cat["items"].append(item)

        return {
            "highlightDishes": "\n".join(final_highlight_dishes),
            "signatureDish": "\n".join(final_signature_dishes),
            "menuCategories": final_categories
        }
        
    except Exception as e:
        import traceback
        print(f"Menu Extraction Error: {e}")
        traceback.print_exc()
        return {
            "highlightDishes": "Sample Dish",
            "signatureDish": "Sample Signature",
            "menuCategories": [],
            "error": "Menu scan temporarily unavailable, please try again"
        }
