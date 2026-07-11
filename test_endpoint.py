import requests
import json

url = "https://glowqr.onrender.com/api/health-check/search"
payload = {
    "query": "House of Aadayein",
    "session_token": "test-token"
}
headers = {
    "Content-Type": "application/json"
}
try:
    res = requests.post(url, json=payload, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.text)
except Exception as e:
    print("Error:", e)
