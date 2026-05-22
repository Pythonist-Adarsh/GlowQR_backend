import asyncio
import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("No API Key")
        return
        
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    print("Calling async generate_content...")
    response = await model.generate_content_async("Hello! Say 'Yes if this works'.")
    print(response.text)

if __name__ == "__main__":
    asyncio.run(main())
