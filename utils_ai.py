import httpx
import os
import json

def format_location(area: str, city: str) -> str:
    loc_parts = []
    if area:
        loc_parts.append(area.strip())
    if city:
        c = city.strip()
        if not any(c.lower() in part.lower() for part in loc_parts):
            loc_parts.append(c)
    return ", ".join(loc_parts) if loc_parts else "your area"

async def extract_competitors(text: str) -> list[str]:
    system_prompt = "Return only specific proper-noun brand or shop names explicitly named in the text. If none are explicitly named, return []. Never return generic descriptions. Return strictly a JSON array of strings, max 8, no other text."
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")
    
    llm_text = ""
    try:
        if groq_key:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
        
    if not llm_text and deepinfra_key:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.deepinfra.com/v1/openai/chat/completions",
                    headers={"Authorization": f"Bearer {deepinfra_key}"},
                    json={
                        "model": "meta-llama/Meta-Llama-3-8B-Instruct",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    if not llm_text:
        return []

    llm_text = llm_text.strip()
    if llm_text.startswith("```json"):
        llm_text = llm_text[7:]
    elif llm_text.startswith("```"):
        llm_text = llm_text[3:]
    if llm_text.endswith("```"):
        llm_text = llm_text[:-3]
    
    try:
        parsed = json.loads(llm_text.strip())
        if not isinstance(parsed, list):
            return []
            
        final_list = []
        seen = set()
        blocklist = ["other", "local", "businesses", "stores", "shops", "options", "various", "etc", "and more", "boutiques"]
        
        for item in parsed:
            if not isinstance(item, str): continue
            clean = item.strip().rstrip(":")
            if not clean: continue
            if len(clean) > 40: continue
            if ":" in clean or "(" in clean: continue
            
            lower_clean = clean.lower()
            if any(b in lower_clean for b in blocklist): continue
            if not any(c.isupper() for c in clean): continue
            
            if "house of aadayein" in lower_clean or "aadayein" in lower_clean or "adayein" in lower_clean:
                continue
                
            if lower_clean not in seen:
                seen.add(lower_clean)
                final_list.append(clean)
                
        return final_list
    except json.JSONDecodeError:
        return []

def extract_competitors_sync(text: str) -> list[str]:
    system_prompt = "Return only specific proper-noun brand or shop names explicitly named in the text. If none are explicitly named, return []. Never return generic descriptions. Return strictly a JSON array of strings, max 8, no other text."
    
    groq_key = os.getenv("GROQ_API_KEY")
    deepinfra_key = os.getenv("DEEPINFRA_API_KEY")
    
    llm_text = ""
    try:
        if groq_key:
            with httpx.Client() as client:
                r = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}"},
                    json={
                        "model": "llama3-8b-8192",
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
    except Exception:
        pass
        
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
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                if r.status_code == 200:
                    llm_text = r.json()["choices"][0]["message"]["content"]
        except Exception:
            pass

    if not llm_text:
        return []

    llm_text = llm_text.strip()
    if llm_text.startswith("```json"):
        llm_text = llm_text[7:]
    elif llm_text.startswith("```"):
        llm_text = llm_text[3:]
    if llm_text.endswith("```"):
        llm_text = llm_text[:-3]
    
    try:
        parsed = json.loads(llm_text.strip())
        if not isinstance(parsed, list):
            return []
            
        final_list = []
        seen = set()
        blocklist = ["other", "local", "businesses", "stores", "shops", "options", "various", "etc", "and more", "boutiques"]
        
        for item in parsed:
            if not isinstance(item, str): continue
            clean = item.strip().rstrip(":")
            if not clean: continue
            if len(clean) > 40: continue
            if ":" in clean or "(" in clean: continue
            
            lower_clean = clean.lower()
            if any(b in lower_clean for b in blocklist): continue
            if not any(c.isupper() for c in clean): continue
            
            if "house of aadayein" in lower_clean or "aadayein" in lower_clean or "adayein" in lower_clean:
                continue
                
            if lower_clean not in seen:
                seen.add(lower_clean)
                final_list.append(clean)
                
        return final_list
    except json.JSONDecodeError:
        return []
