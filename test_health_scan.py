import requests

print("Testing search...")
res1 = requests.post("http://localhost:8000/api/health-check/search", json={"query": "Aadish Cafe Mumbai"})
print("Search status:", res1.status_code)
if res1.status_code == 200:
    data = res1.json()
    print("Search results:", data.get("results", [])[:1])
    if data.get("results"):
        place_id = data["results"][0]["place_id"]
        print("Testing scan for place_id:", place_id)
        res2 = requests.post("http://localhost:8000/api/health-check/scan", json={"place_id": place_id})
        print("Scan status:", res2.status_code)
        if res2.status_code == 200:
            scan_data = res2.json()
            print("Scan data:", scan_data)
            
            # Test Lead Capture
            scan_id = scan_data["scan_id"]
            print("Testing capture lead for scan_id:", scan_id)
            res3 = requests.post("http://localhost:8000/api/health-check/capture-lead", json={"scan_id": scan_id, "email": "test@test.com"})
            print("Capture status:", res3.status_code)
