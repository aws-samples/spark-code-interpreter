#!/usr/bin/env python3
"""Direct check of session state"""

import requests
import time

BASE_URL = "http://localhost:8000"
SESSION_ID = f"check-{int(time.time())}"

print("Testing session isolation...\n")

# 1. Upload CSV
print("1. Uploading CSV...")
r = requests.post(f"{BASE_URL}/upload-csv", json={
    "filename": "test.csv",
    "content": "id,val\n1,10\n2,20",
    "session_id": SESSION_ID
})
print(f"   Response: {r.status_code}")

# 2. Check what agent sees
print("\n2. Checking what agent sees (with CSV)...")
r = requests.post(f"{BASE_URL}/generate", json={
    "prompt": "Show me the data",
    "session_id": SESSION_ID
})
result = r.json()
print(f"   Success: {result.get('success')}")
print(f"   CSV used: {result.get('csv_file_used')}")

# Wait for execution
time.sleep(3)

# 3. Check session state by trying to generate again
print("\n3. Checking session after execution...")
r = requests.post(f"{BASE_URL}/generate", json={
    "prompt": "Create 5 rows",
    "session_id": SESSION_ID
})
result = r.json()
print(f"   Success: {result.get('success')}")
print(f"   CSV used: {result.get('csv_file_used')}")

if result.get('csv_file_used'):
    print("\n❌ FAIL: CSV still in session after execution")
else:
    print("\n✅ PASS: CSV cleared from session")

print("\nCheck backend logs for:")
print("  - '🧹 Cleared session data sources' messages")
print("  - '📊 Session state' showing CSV: None on second generation")
