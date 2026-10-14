import os
import httpx
import asyncio
import re
from typing import Dict, Any
from utils_ai import extract_competitors_sync
from openai import AsyncOpenAI
import traceback

async def extract_competitors_async(text: str) -> list[str]:
    """Run sync extractor in thread pool."""
    return await asyncio.to_thread(extract_competitors_sync, text)


async def check_engine_gemini(query: str) -> Dict[str, Any]:
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        return {"error": "GEMINI_API_KEY not configured", "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_api_key}",
                json={"contents": [{"parts": [{"text": query}]}]},
                timeout=25.0
            )
            if response.status_code == 200:
                data = response.json()
                text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")

                mentioned = "house of aadayein" in text.lower() or "house of adayein" in text.lower() or "aadayein" in text.lower()

                # Always extract competitors (even when mentioned, to capture co-mentions)
                competitor_mentioned = "N/A"
                if text:
                    print(f"[AI Visibility][gemini] query='{query}' | mentioned={mentioned} | text_len={len(text)}")
                    comp_list = await extract_competitors_async(text)
                    if comp_list:
                        competitor_mentioned = ", ".join(comp_list)
                        print(f"[AI Visibility][gemini] query='{query}' | competitors: {comp_list}")
                    else:
                        competitor_mentioned = "No specific brands named"
                        print(f"[AI Visibility][gemini] query='{query}' | no competitors extracted")

                return {
                    "mentioned": mentioned,
                    "raw_text": text,
                    "sources": [],
                    "competitors_raw": competitor_mentioned,
                    "sourced_from_us": False
                }
            else:
                return {"error": f"API Error: {response.status_code}", "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}
    except Exception as e:
        print(f"Gemini error: {traceback.format_exc()}")
        return {"error": str(e), "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}


async def check_engine_chatgpt(query: str) -> Dict[str, Any]:
    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        return {"error": "OPENAI_API_KEY not configured", "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}

    model = os.getenv("OPENAI_VISIBILITY_MODEL", "gpt-4o-mini")

    try:
        client = AsyncOpenAI(api_key=openai_api_key)

        response = await client.responses.create(
            model=model,
            input=query,
            tools=[
                {
                    "type": "web_search",
                    "user_location": {
                        "type": "approximate",
                        "country": "IN",
                        "region": "Uttar Pradesh",
                        "city": "Lucknow"
                    }
                }
            ]
        )

        text = getattr(response, "output_text", "")
        if not text and hasattr(response, "output"):
            text = str(response.output)

        # --- Source extraction ---
        sources = []
        if hasattr(response, "citations"):
            for citation in response.citations:
                if hasattr(citation, "url"):
                    sources.append(citation.url)

        # Walk output items for web_search_call results
        if hasattr(response, "output") and isinstance(response.output, list):
            for item in response.output:
                if hasattr(item, "type") and item.type == "web_search_call":
                    if hasattr(item, "results"):
                        for r in item.results:
                            if hasattr(r, "url"):
                                sources.append(r.url)
                if hasattr(item, "annotations"):
                    for ann in item.annotations:
                        if hasattr(ann, "url"):
                            sources.append(ann.url)

        # Regex fallback for URLs
        if not sources and text:
            urls = re.findall(r'(https?://[^\s)\]]+)', text)
            sources.extend(urls)

        # Deduplicate and extract domains
        seen_sources = set()
        deduped_sources = []
        for s in sources:
            if s not in seen_sources:
                seen_sources.add(s)
                deduped_sources.append(s)

        mentioned = "house of aadayein" in text.lower() or "house of adayein" in text.lower() or "aadayein" in text.lower()

        # Always extract competitors
        competitor_mentioned = "N/A"
        if text:
            print(f"[AI Visibility][chatgpt] query='{query}' | mentioned={mentioned} | text_len={len(text)}")
            comp_list = await extract_competitors_async(text)
            if comp_list:
                competitor_mentioned = ", ".join(comp_list)
                print(f"[AI Visibility][chatgpt] query='{query}' | competitors: {comp_list}")
            else:
                competitor_mentioned = "No specific brands named"
                print(f"[AI Visibility][chatgpt] query='{query}' | no competitors extracted")

        sourced_from_us = any(
            any(d in str(s).lower() for d in ["glowqr.com", "instagram.com", "maps.google"])
            for s in deduped_sources
        )

        return {
            "mentioned": mentioned,
            "raw_text": text,
            "sources": deduped_sources,
            "competitors_raw": competitor_mentioned,
            "sourced_from_us": sourced_from_us
        }

    except Exception as e:
        print(f"ChatGPT error: {traceback.format_exc()}")
        return {"error": str(e), "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}


async def check_engine(engine: str, query: str) -> Dict[str, Any]:
    for attempt in range(2):  # 1 retry
        if engine == "gemini":
            res = await check_engine_gemini(query)
        elif engine == "chatgpt":
            res = await check_engine_chatgpt(query)
        else:
            return {"error": f"Unknown engine: {engine}"}

        if "error" not in res:
            return res

        # Error happened, wait slightly before retry
        if attempt == 0:
            await asyncio.sleep(1)

    return res  # Return error from final attempt
