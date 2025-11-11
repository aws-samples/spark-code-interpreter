#!/usr/bin/env python3
import requests
import time

payload = {
    "prompt": "Show top 5 rows",
    "session_id": f"test-glue-{int(time.time())}",
    "framework": "spark",
    "selected_tables": [{"database": "default", "table": "nyc_taxi_data"}]
}

print(f"Testing Glue table: {payload['session_id']}")
response = requests.post("http://localhost:8000/spark/generate", json=payload, timeout=120)
print(f"Status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"Success: {result.get('success')}")
    print(f"Platform: {result.get('execution_platform')}")
else:
    print(f"Error: {response.text[:300]}")
