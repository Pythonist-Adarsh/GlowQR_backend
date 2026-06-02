import asyncio
from services.groq_service import extract_menu_from_image

async def test():
    with open('test.png', 'wb') as f:
        f.write(b'fake png data just to test api error')
    
    with open('test.png', 'rb') as f:
        res = await extract_menu_from_image(f.read(), 'image/png')
        print(res)

asyncio.run(test())
