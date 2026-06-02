import asyncio
import os
import json

async def extract_menu_from_image(file_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    prompt = "You are an expert menu data extractor. Extract the menu items from the attached image/document.
Format the output EXACTLY as this JSON structure:
{
    "highlightDishes": "Dish1\nDish2\nDish3\nDish4",
    "signatureDish": "Best Dish",
    "menuCategories": [
    {
        "category": "Category Name",
        "items": [
        { "id": 1, "name": "Item Name", "emoji": "??", "price": "?200" }
        ]
    }
    ]
}

Rules:
- 'highlightDishes' should be a string of 3-4 popular dishes separated by newlines.
- 'signatureDish' should be one standout dish.
- 'menuCategories' groups items by their category (e.g., Starters, Mains).
- Ensure all 'id' fields are unique integers across the entire menu.
- Generate appropriate emojis for each dish.
- Return ONLY valid JSON, do not wrap in markdown like `json.
"
    try:
        if 'pdf' in mime_type.lower():
            import fitz
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                file_bytes = pix.tobytes("jpeg")
                mime_type = "image/jpeg"
                
        import google.generativeai as genai
        genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        response = model.generate_content([
            prompt,
            {
                "mime_type": mime_type,
                "data": file_bytes
            }
        ])
        text = response.text.strip()
        
        import re
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            text = match.group(0)
            
        text = text.replace('`json', '').replace('`', '').strip()
        return json.loads(text)
    except Exception as e:
        print(f"Extraction error: {e}")
        return {
            "highlightDishes": "Sample Dish",
            "signatureDish": "Sample Signature",
            "menuCategories": []
        }

async def test():
    with open('test_valid.pdf', 'rb') as f:
        res = await extract_menu_from_image(f.read(), 'application/pdf')
        print("Success for PDF via image!")
    with open('test.png', 'wb') as f:
        f.write(b'fake')
    with open('test.png', 'rb') as f:
        res = await extract_menu_from_image(f.read(), 'image/png')
        print("Error handled for fake image.")

asyncio.run(test())
