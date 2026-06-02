import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv(override=True)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
models = client.models.list()
for m in models.data:
    if 'vision' in m.id.lower():
        print(m.id)
