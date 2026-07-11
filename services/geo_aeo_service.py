import httpx
from bs4 import BeautifulSoup
import re
import json

def analyze_geo_aeo_signals(website_url: str, business_name: str, phone: str, reviews: list, category: str):
    """
    Analyzes a business's website and reviews for GEO/AEO discoverability signals.
    Returns a dict with score and sub-signals breakdown.
    """
    if not website_url:
        return {
            "has_website": False,
            "geo_aeo_score": 0,
            "sub_signals": [
                {"passed": False, "message": "No website found \u2014 this blocks AI-answer-engine discovery entirely."}
            ]
        }

    sub_signals = []
    score = 0
    total_checks = 5  # JSON-LD, FAQ, NAP, Meta, Crawlable text

    try:
        # Fetch HTML with strict timeout and fake User-Agent to avoid basic blocks
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            response = client.get(website_url, headers=headers)
            
        if response.status_code in [403, 401]:
            return {
                "has_website": True,
                "geo_aeo_score": 0,
                "sub_signals": [
                    {"passed": False, "message": "Website blocked automated access (e.g. 403 Forbidden) \u2014 couldn't fully analyze."}
                ]
            }
            
        html = response.text
        soup = BeautifulSoup(html, "html.parser")
        text_content = soup.get_text(separator=' ', strip=True).lower()

        # 1. LocalBusiness Schema
        has_local_business = False
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and "LocalBusiness" in script.string:
                has_local_business = True
                break
        
        if has_local_business:
            score += 20
            sub_signals.append({"passed": True, "message": "LocalBusiness schema.org markup found."})
        else:
            sub_signals.append({"passed": False, "message": "No LocalBusiness schema.org markup found."})

        # 2. FAQ Schema / Visible Q&A
        has_faq = False
        for script in soup.find_all("script", type="application/ld+json"):
            if script.string and "FAQPage" in script.string:
                has_faq = True
                break
        if not has_faq:
            # Fallback heuristic for FAQ
            if "faq" in text_content or "frequently asked questions" in text_content:
                has_faq = True
                
        if has_faq:
            score += 20
            sub_signals.append({"passed": True, "message": "FAQ schema or Q&A formatted content detected."})
        else:
            sub_signals.append({"passed": False, "message": "No FAQ schema or Q&A sections found."})

        # 3. NAP Consistency (Name or Phone check)
        # Simplify business name for matching
        simple_name = re.sub(r'[^a-zA-Z0-9\s]', '', business_name).lower().split()[0]
        has_name = simple_name in text_content
        has_phone = False
        if phone:
            simple_phone = re.sub(r'\D', '', phone)
            if simple_phone and len(simple_phone) >= 10:
                has_phone = simple_phone[-10:] in re.sub(r'\D', '', text_content)
        
        if has_name or has_phone:
            score += 20
            sub_signals.append({"passed": True, "message": "NAP (Name/Phone) consistency verified on website."})
        else:
            sub_signals.append({"passed": False, "message": "NAP mismatch: Couldn't verify Google Business Name/Phone on website text."})

        # 4. Meta Description
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc and meta_desc.get("content") and len(meta_desc.get("content", "")) > 10:
            score += 20
            sub_signals.append({"passed": True, "message": "Descriptive meta tag present for search context."})
        else:
            sub_signals.append({"passed": False, "message": "Missing or empty meta description."})

        # 5. Crawlable Text
        if len(text_content) > 500:
            score += 20
            sub_signals.append({"passed": True, "message": "Rich, crawlable text content found (Not a JS-only blank page)."})
        else:
            sub_signals.append({"passed": False, "message": "Low text content. May be a JS-only Single Page App blocking crawlers."})

    except Exception as e:
        return {
            "has_website": True,
            "geo_aeo_score": 0,
            "sub_signals": [
                {"passed": False, "message": f"Website fetch failed or timed out: {str(e)}"}
            ]
        }
        
    # 6. Review Specificity Signal (Independent of website fetch, but impacts AEO)
    # If the user has some detailed reviews, it boosts their AEO score
    detailed_reviews_count = 0
    generic_words = ["good", "nice", "ok", "okay", "great", "awesome", "bad", "terrible", "love it"]
    
    if reviews:
        for rev in reviews:
            text = rev.get("text", {}).get("text", "").lower()
            if not text:
                continue
            words = text.split()
            # If review is long and not just generic words
            if len(words) > 10 and not all(w in generic_words for w in words[:5]):
                detailed_reviews_count += 1
                
        if detailed_reviews_count >= 2:
            sub_signals.append({"passed": True, "message": f"Reviews are highly specific ({detailed_reviews_count} detailed reviews found)."})
        else:
            sub_signals.append({"passed": False, "message": "Reviews are generic, lacking specific details Answer Engines look for."})
    else:
        sub_signals.append({"passed": False, "message": "No reviews found to extract specificity signals."})

    # Note: Score is out of 100 based on the 5 website checks. 
    # Review specificity acts as an extra insight or can bump the score slightly, but let's keep score capped at 100.

    return {
        "has_website": True,
        "geo_aeo_score": min(score, 100),
        "sub_signals": sub_signals
    }
