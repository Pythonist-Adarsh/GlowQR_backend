import re
import json

text = """{
  "highlightDishes": "Kirkure Items\nBurger Hub\nPizza\nPasta",
  "signatureDish": "Kirkure Paneer Momos",
  "menuCategories": [
    {
      "category": "Kirkure Items",
      "items": [
        {
          "name": "Kirkure Paneer Momos",
          "emoji": "🥟",
          "price": "140"
        },
        {
          "name": "Kirkure Chaap",
          "emoji": "🍔",
          "price": "140"
        }
      ]
    },
    {
      "category": "Burger Hub",
      "items": [
        {
          "name": "Aloo Tikki Burger",
          "emoji": "🍔",
          "price": "40"
        },
        {
          "name": "Veg. Patty Burger",
          "emoji": "🍔",
          "price": "50"
        """

def parse_partial_json(text):
    final_cats = []
    
    # 1. Highlights and Signature
    highlights = ""
    sig = ""
    h_match = re.search(r'"highlightDishes"\s*:\s*"([^"]*)"', text)
    if h_match: highlights = h_match.group(1).replace('\\n', '\n')
    
    s_match = re.search(r'"signatureDish"\s*:\s*"([^"]*)"', text)
    if s_match: sig = s_match.group(1).replace('\\n', '\n')

    # 2. Categories
    # We find all occurrences of "category": "NAME"
    # To get the items for this category, we take the substring until the next "category": or end of string.
    cat_matches = list(re.finditer(r'"category"\s*:\s*"([^"]+)"', text))
    
    for i, match in enumerate(cat_matches):
        cat_name = match.group(1)
        start_idx = match.end()
        end_idx = cat_matches[i+1].start() if i + 1 < len(cat_matches) else len(text)
        
        cat_content = text[start_idx:end_idx]
        
        # 3. Items inside category
        items = []
        # Find all item blocks. We can just regex the properties.
        # But order might change, or some properties might be missing.
        # It's safer to find each { ... } block inside the items array.
        item_blocks = re.finditer(r'\{\s*"name".*?(?=\}|\Z)', cat_content, re.DOTALL)
        for ib_match in item_blocks:
            ib_text = ib_match.group(0) + "}" # Add } just to help regexes if needed, though we can just search inside ib_text
            
            name_m = re.search(r'"name"\s*:\s*"([^"]+)"', ib_text)
            emoji_m = re.search(r'"emoji"\s*:\s*"([^"]+)"', ib_text)
            price_m = re.search(r'"price"\s*:\s*("[^"]*"|null|\d+)', ib_text)
            
            if name_m:
                name = name_m.group(1)
                emoji = emoji_m.group(1) if emoji_m else "🍔"
                price_raw = price_m.group(1) if price_m else "null"
                if price_raw == 'null': price = None
                else: price = price_raw.strip('"')
                
                items.append({
                    "name": name,
                    "emoji": emoji,
                    "price": price
                })
        
        final_cats.append({
            "category": cat_name,
            "items": items
        })
        
    return highlights, sig, final_cats

print(json.dumps(parse_partial_json(text), indent=2))
