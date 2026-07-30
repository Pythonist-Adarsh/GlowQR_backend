import os
import asyncio
from PIL import Image, ImageDraw, ImageFont
import io
import sys
# Make sure we can import from backend
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.groq_service import extract_menu_from_image

async def run_test():
    # 1. Test with Photo
    print("--- Testing Photo ---")
    img = Image.new('RGB', (400, 400), color='white')
    d = ImageDraw.Draw(img)
    d.text((10,10), "Menu", fill=(0,0,0))
    d.text((10,50), "Burger - $5", fill=(0,0,0))
    d.text((10,90), "Fries - $3", fill=(0,0,0))
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    img_bytes = img_byte_arr.getvalue()
    
    res = await extract_menu_from_image(img_bytes, mime_type="image/jpeg")
    import json
    print(json.dumps(res, indent=2))
    
    # 2. Test with PDF
    print("\n--- Testing PDF ---")
    pdf_path = r"d:\glowQR\fast.pdf"
    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()
        
        res2 = await extract_menu_from_image(pdf_bytes, mime_type="application/pdf")
        print(json.dumps(res2, indent=2))
    else:
        print(f"PDF not found at {pdf_path}")

if __name__ == "__main__":
    asyncio.run(run_test())
