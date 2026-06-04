import re

with open('d:/glowQR/backend/routers/analytics.py', 'r', encoding='utf-8') as f:
    content = f.read()

target = '''all_reviews_query = db.query(models.ScanEvent).filter('''
replacement = '''      all_reviews_query = db.query(models.ScanEvent).filter('''

content = content.replace(target, replacement)

with open('d:/glowQR/backend/routers/analytics.py', 'w', encoding='utf-8') as f:
    f.write(content)
