import requests, json

BASE = "https://co-teacher-wuza.onrender.com"

print("Testing POST /api/execute with real prompt...")
try:
    r = requests.post(f"{BASE}/api/execute",
                      json={"prompt": "What are ADHD strategies?"},
                      timeout=180)
    print(f"HTTP {r.status_code}")
    d = r.json()
    print(f"status: {d.get('status')}")
    print(f"error: {d.get('error')}")
    print(f"response preview: {str(d.get('response',''))[:300]}")
    steps = d.get("steps", [])
    print(f"steps count: {len(steps)}")
    for i, s in enumerate(steps[:5]):
        print(f"  step {i+1}: module={s.get('module')}")
except Exception as e:
    print(f"ERROR: {e}")

print()
print("Testing POST /api/execute with empty prompt...")
try:
    r2 = requests.post(f"{BASE}/api/execute",
                       json={"prompt": ""},
                       timeout=30)
    d2 = r2.json()
    print(f"status: {d2.get('status')}")
    print(f"error: {d2.get('error')}")
    print(f"response (should be null/None): {repr(d2.get('response'))}")
except Exception as e:
    print(f"ERROR: {e}")
