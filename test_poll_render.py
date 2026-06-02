import time
import requests

url = "https://glowqr.onrender.com/api/onboarding/extract-menu"
for i in range(10):
    print(f"Attempt {i+1}...")
    with open("test.png", "rb") as f:
        files = {"file": ("test.png", f, "image/png")}
        response = requests.post(url, files=files)
        data = response.json()
        print(data)
        if "error" in data or "Dish1" in data.get("highlightDishes", ""):
            print("NEW DEPLOYMENT DETECTED!")
            break
    time.sleep(20)
