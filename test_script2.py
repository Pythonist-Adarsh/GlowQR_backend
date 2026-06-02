import asyncio
from services.groq_service import extract_menu_from_image

async def test():
    # create a small valid pdf
    from reportlab.pdfgen import canvas
    c = canvas.Canvas("test_valid.pdf")
    c.drawString(100, 750, "Sample Menu")
    c.drawString(100, 730, "Burger - 5")
    c.save()
    
    with open('test_valid.pdf', 'rb') as f:
        res = await extract_menu_from_image(f.read(), 'application/pdf')
        print(res)

asyncio.run(test())
