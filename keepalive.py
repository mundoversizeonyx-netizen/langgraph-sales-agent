import time, requests

SERVICES = [
    "https://evolution-api-xluu.onrender.com/",
    "https://langgraph-sales-agent.onrender.com/api/tenants"
]

while True:
    for url in SERVICES:
        try:
            r = requests.get(url, timeout=10)
            print(f"OK {url} - {r.status_code}")
        except Exception as e:
            print(f"ERROR {url} - {e}")
    time.sleep(600)