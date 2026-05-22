import os
import json
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

def test_extract():
    file_bytes = open("d:/glowQR/fast.pdf", "rb").read()
    
    api_key = os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = """
    You are an expert menu data extractor. Extract the menu items from the following restaurant menu PDF.
    Format the output EXACTLY as this JSON structure:
    {
      "highlightDishes": "Dish1\\nDish2\\nDish3\\nDish4",
      "signatureDish": "Best Dish",
      "menuCategories": [
        {
          "category": "Category Name",
          "items": [
            { "id": 1, "name": "Item Name", "emoji": "🍔", "price": "₹200" }
          ]
        }
      ],
      "menuItems": [
        { "id": 1, "name": "Item Name", "emoji": "🍔" }
      ]
    }
    
    Rules:
    - 'highlightDishes' should be a string of 3-4 popular dishes separated by newlines.
    - 'signatureDish' should be one standout dish.
    - 'menuCategories' groups items by their category (e.g., Starters, Mains, Chinese, Pizza).
    - 'menuItems' is a flat list of ALL items (just id, name, and emoji).
    - Ensure all 'id' fields are unique integers across the entire menu.
    - Generate appropriate emojis for each dish.
    - Return ONLY valid JSON, do not wrap in markdown like ```json.
    """
    
    print("Calling Gemini 2.5 Flash with PDF inline...")
    try:
        response = model.generate_content([
            prompt,
            {
                "mime_type": "application/pdf",
                "data": file_bytes
            }
        ])
        json_text = response.text.strip()
        print(f"Raw response: {json_text[:200]}...")
        if json_text.startswith("```json"):
            json_text = json_text[7:-3]
        elif json_text.startswith("```"):
            json_text = json_text[3:-3]
            
        menu_data = json.loads(json_text)
        print("Success! JSON parsed.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_extract()
