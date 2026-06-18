import asyncio
import os
import sys

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.groq_service import extract_menu_from_image

async def main():
    # Create a minimal valid 1x1 GIF or PNG
    import base64
    valid_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    file_bytes = base64.b64decode(valid_png_b64)
        
    res = await extract_menu_from_image(file_bytes, "image/png")
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
