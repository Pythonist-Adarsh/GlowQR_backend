with open('services/groq_service.py', 'r', encoding='utf-8') as f:
    data = f.read()

target = "    try:\n        response = client.chat.completions.create("
replacement = """    if previous_reviews:
        user_msg += "\\n\\nCRITICAL INSTRUCTION: Do NOT generate any review that is identical or highly similar to the following recent reviews from this business:\\n"
        for pr in previous_reviews[:5]:
            user_msg += f"- \\"{pr}\\"\\n"
        user_msg += "\\nThe generated reviews MUST be completely unique and fresh."

    try:
        response = client.chat.completions.create("""

if target in data:
    data = data.replace(target, replacement)
    with open('services/groq_service.py', 'w', encoding='utf-8') as f:
        f.write(data)
    print("Patched groq_service.py")
else:
    print("Target not found")
