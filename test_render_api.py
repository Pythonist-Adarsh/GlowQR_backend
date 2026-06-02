import requests

url = "https://glowqr.onrender.com/api/onboarding/extract-menu"
with open("test.png", "rb") as f:
    files = {"file": ("test.png", f, "image/png")}
    response = requests.post(url, files=files)
    print(response.status_code)
    print(response.json())
