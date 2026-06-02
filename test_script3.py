import asyncio
from services.groq_service import extract_menu_from_image

async def test():
    with open('test_valid.pdf', 'rb') as f:
        res = await extract_menu_from_image(f.read(), 'application/pdf')
        print(res)

asyncio.run(test())
