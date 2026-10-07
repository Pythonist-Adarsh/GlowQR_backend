import os
import httpx
import asyncio
from typing import Dict, Any
from utils_ai import extract_competitors_sync
from openai import AsyncOpenAI
import traceback

async def extract_competitors_async(text: str) -> list[str]:
    # Run sync version in thread pool for now to avoid blocking
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
                
                mentioned = "house of aadayein" in text.lower() or "house of adayein" in text.lower()
                competitor_mentioned = "N/A"
                if not mentioned and text:
                    comp_list = await extract_competitors_async(text)
                    if comp_list:
                        competitor_mentioned = ", ".join(comp_list)
                    else:
                        competitor_mentioned = "No specific brands named"
                        
                # Gemini doesn't currently return sources in this exact API call structure by default without grounding
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
            
        sources = []
        # Attempt to extract citations/sources from the response object if available
        if hasattr(response, "citations"):
            for citation in response.citations:
                if hasattr(citation, "url"):
                    sources.append(citation.url)
        elif hasattr(response, "tools_output") or hasattr(response, "web_search_results"):
            # sometimes sources are in metadata
            pass
            
        # Fallback to regex extraction of URLs from text if no official sources found
        import re
        if not sources and text:
            urls = re.findall(r'(https?://[^\s)\]]+)', text)
            sources.extend(urls)
            
        mentioned = "house of aadayein" in text.lower() or "house of adayein" in text.lower() or "aadayein" in text.lower()
        
        competitor_mentioned = "N/A"
        if not mentioned and text:
            comp_list = await extract_competitors_async(text)
            if comp_list:
                competitor_mentioned = ", ".join(comp_list)
            else:
                competitor_mentioned = "No specific brands named"
                
        sourced_from_us = False
        for source in sources:
            source_lower = str(source).lower()
            if "glowqr.com" in source_lower or "instagram.com" in source_lower or "maps.google" in source_lower:
                sourced_from_us = True
                
        return {
            "mentioned": mentioned,
            "raw_text": text,
            "sources": sources,
            "competitors_raw": competitor_mentioned,
            "sourced_from_us": sourced_from_us
        }
            
    except Exception as e:
        print(f"ChatGPT error: {traceback.format_exc()}")
        return {"error": str(e), "mentioned": False, "raw_text": "", "sources": [], "competitors_raw": "N/A", "sourced_from_us": False}

async def check_engine(engine: str, query: str) -> Dict[str, Any]:
    for attempt in range(2): # 1 retry
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
            
    return res # Return error from final attempt
