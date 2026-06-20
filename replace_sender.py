import re

with open(r'd:\glowQR\backend\services\email_service.py', 'r', encoding='utf-8') as f:
    c = f.read()

c = re.sub(r'"from":\s*".*?"', '"from": "GlowQR <hello@glowqr.com>"', c)
c = re.sub(r"'from':\s*'.*?'", "'from': 'GlowQR <hello@glowqr.com>'", c)
c = re.sub(r"'from':\s*SENDER", "'from': 'GlowQR <hello@glowqr.com>'", c)
c = re.sub(r"SENDER\s*=\s*'.*?'", "SENDER = 'GlowQR <hello@glowqr.com>'", c)

with open(r'd:\glowQR\backend\services\email_service.py', 'w', encoding='utf-8') as f:
    f.write(c)

print("Replacement done.")
