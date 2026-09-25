import os, json, base64
import asyncio
from dotenv import load_dotenv
load_dotenv(override=True)
from groq import Groq
import fitz

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

async def test_chunk():
    pdf_path = r"d:\glowQR\fast.pdf"
    images_b64 = []
    with open(pdf_path, "rb") as f:
        doc = fitz.open(stream=f.read(), filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            images_b64.append(base64.b64encode(pix.tobytes("jpeg")).decode('utf-8'))
            
    b64_image = images_b64[0]
    
    prompt = """Extract all menu items and return ONLY this JSON, no markdown:
{
  "h": "string (highlight dishes)",
  "s": "string (signature dish)",
  "c": [
    {
      "c": "string (category name)",
      "i": [
        {
          "n": "string (item name)",
          "e": "🍔",
          "p": "string (price)"
        }
      ]
    }
  ]
}
Rules: ONLY JSON, no code blocks, clean item names, keep currency symbols."""

    extracted_cats = []
    pass_num = 0
    
    while pass_num < 4:
        pass_num += 1
        current_prompt = prompt
        if extracted_cats:
            current_prompt += f"\n\nIMPORTANT: You have already completely extracted these categories: {', '.join(extracted_cats)}. Skip them and ONLY extract the remaining categories from the image."
        
        print(f"--- Pass {pass_num} ---")
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}},
                            {"type": "text", "text": current_prompt}
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=900,
                response_format={"type": "json_object"},
                timeout=30.0
            )
        except Exception as e:
            print("API Error:", e)
            break
            
        text = response.choices[0].message.content.strip()
        finish_reason = response.choices[0].finish_reason
        print(f"Finish Reason: {finish_reason}")
        print(f"Text Length: {len(text)}")
        
        if finish_reason == "length":
            repair_prompt = f"The following JSON is malformed. Fix it and return ONLY the valid JSON, nothing else:\n\n{text}"
            try:
                repair_response = client.chat.completions.create(
                    model="openai/gpt-oss-20b",
                    messages=[{"role": "user", "content": repair_prompt}],
                    temperature=0.1,
                    max_tokens=1500,
                    response_format={"type": "json_object"}
                )
                text = repair_response.choices[0].message.content.strip()
            except Exception as e:
                print("Repair Error:", e)
            
        try:
            parsed = json.loads(text)
            cats = parsed.get("c", [])
            for cat in cats:
                cat_name = cat.get("c", "")
                if cat_name and cat_name not in extracted_cats:
                    extracted_cats.append(cat_name)
                    print(f"Extracted category: {cat_name} with {len(cat.get('i', []))} items")
        except Exception as e:
            print("Error parsing JSON", e)
            
        if finish_reason != "length":
            break
            
asyncio.run(test_chunk())
