import os
import httpx
import json
import re
from collections import Counter

def format_location(area: str, city: str) -> str:
    loc_parts = []
    if area:
        loc_parts.append(area.strip())
    if city:
        c = city.strip()
        if not any(c.lower() in part.lower() for part in loc_parts):
            loc_parts.append(c)
    return ", ".join(loc_parts) if loc_parts else "your area"


# ---------------------------------------------------------------------------
# Shared filter / extraction helpers
# ---------------------------------------------------------------------------
AADAYEIN_ALIASES = {"house of aadayein", "house of adayein", "aadayein", "adayein"}

# Only block truly generic words — NOT "shops/stores" since brand names can end with them
BLOCKLIST = {"other", "local", "businesses", "options", "various", "etc", "and more", "boutiques", "many", "several"}

def _is_aadayein(name: str) -> bool:
    lower = name.lower()
    return any(alias in lower for alias in AADAYEIN_ALIASES)

def _filter_names(raw_list: list) -> list:
    """Apply dedup + blocklist + basic quality filters to a raw name list."""
    final_list = []
    seen: set[str] = set()
    for item in raw_list:
        if not isinstance(item, str):
            continue
        clean = item.strip().rstrip(":")
        if not clean or len(clean) > 50:
            continue
        if "(" in clean:
            continue
        lower_clean = clean.lower()
        if any(b in lower_clean for b in BLOCKLIST):
            continue
        if not any(c.isupper() for c in clean):
            continue
        if _is_aadayein(clean):
            continue
        if lower_clean not in seen:
            seen.add(lower_clean)
            final_list.append(clean)
    return final_list


def _parse_llm_json(llm_text: str) -> list:
    """Strip markdown fences and parse a JSON list from LLM output."""
    text = llm_text.strip()
    # Strip markdown fences
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return parsed
        return []
    except json.JSONDecodeError:
        # Try to find JSON array anywhere in the text
        match = re.search(r'\[.*?\]', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
        return []


def _call_llm_sync(text: str, system_prompt: str) -> str:
    """Try Groq then DeepInfra synchronously. Returns raw LLM text or ''."""
    groq_key = os.getenv("GROQ_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")
    llm_text = ""

    if groq_key:
        try:
            with httpx.Client() as client:
                r = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text[:3000]}  # truncate to avoid token overflow
                        ],
                        "temperature": 0.1
                    },
                    timeout=12.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[Competitors] Groq HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Competitors] Groq exception: {e}")

    if not llm_text and deepinfra_key:
        try:
            with httpx.Client() as client:
                r = client.post(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    headers={"Authorization": f"Bearer {deepinfra_key}"},
                    json={
                        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text[:3000]}
                        ],
                        "temperature": 0.1
                    },
                    timeout=12.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
                else:
                    print(f"[Competitors] DeepInfra HTTP {r.status_code}: {r.text[:200]}")
        except Exception as e:
            print(f"[Competitors] DeepInfra exception: {e}")

    return llm_text


COMPETITOR_SYSTEM_PROMPT = (
    "You are a named-entity extractor. "
    "From the text below, extract ONLY specific proper-noun business/brand/shop names that are explicitly mentioned. "
    "Do NOT include generic phrases like 'local shops', 'various stores', headings, or descriptions. "
    "Return strictly a JSON array of strings (max 10). If none found, return []. No other text."
)


def extract_competitors_sync(text: str) -> list[str]:
    """Extract competitor brand names from a single answer text. Logs input/output."""
    if not text or not text.strip():
        print("[Competitors] extract_competitors_sync called with empty text, skipping.")
        return []

    preview = text[:120].replace('\n', ' ')
    print(f"[Competitors] Extracting from text ({len(text)} chars): '{preview}...'")

    llm_text = _call_llm_sync(text, COMPETITOR_SYSTEM_PROMPT)

    if not llm_text:
        print("[Competitors] No LLM response (no GROQ_API_KEY / DEEPINFRA_API_KEY?). Falling back to regex NER.")
        # Regex fallback: find capitalized multi-word phrases (Title Case) that look like brand names
        names = re.findall(r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)+)\b', text)
        raw_list = list(dict.fromkeys(names))  # deduplicate preserving order
        filtered = _filter_names(raw_list)
        print(f"[Competitors] Regex fallback found: {filtered}")
        return filtered

    raw_list = _parse_llm_json(llm_text)
    print(f"[Competitors] LLM raw output: {llm_text[:300]!r}")
    print(f"[Competitors] Parsed list ({len(raw_list)}): {raw_list}")

    filtered = _filter_names(raw_list)
    print(f"[Competitors] After filter ({len(filtered)}): {filtered}")
    return filtered


async def extract_competitors(text: str) -> list[str]:
    """Async wrapper — runs sync version in thread pool."""
    import asyncio
    return await asyncio.to_thread(extract_competitors_sync, text)


def merge_competitor_counts(logs) -> list[dict]:
    """
    Merge competitor mentions across ALL queries and both engines.
    Returns list of {name, count, total_answers} sorted by count desc.
    """
    counter: Counter = Counter()
    total_answers = 0

    for log in logs:
        comp_raw = log.competitor_mentioned or ""
        if comp_raw in ("N/A", "No specific brands named", ""):
            total_answers += 1
            continue
        total_answers += 1
        for name in comp_raw.split(", "):
            name = name.strip()
            if name and not _is_aadayein(name):
                counter[name] += 1

    return [
        {"name": name, "count": count, "total_answers": total_answers}
        for name, count in counter.most_common(10)
    ]
