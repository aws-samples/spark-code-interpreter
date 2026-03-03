#!/usr/bin/env python3
"""Test that session is cleared after execution"""

import requests
import time

BASE_URL = "http://localhost:8000"
SESSION_ID = f"test-clear-{int(time.time())}"

print("=" * 80)
print("TEST: Session Clearing After Execution")
print("=" * 80)
print(f"Session ID: {SESSION_ID}\n")

# Step 1: Upload CSV
print("Step 1: Upload CSV")
response = requests.post(
    f"{BASE_URL}/upload-csv",
    json={
        "filename": "test.csv",
        "content": "id,value\n1,100\n2,200\n3,300",
        "session_id": SESSION_ID
    }
)
print(f"  ✅ CSV uploaded: {response.json().get('success')}")
print("  Backend should log: '✅ Uploaded CSV'")

# Step 2: Generate and execute code
print("\nStep 2: Generate code with CSV")
response = requests.post(
    f"{BASE_URL}/generate",
    json={
        "prompt": "Create a dataset with 10 rows",
        "session_id": SESSION_ID
    }
)
result = response.json()
print(f"  ✅ Code generated: {result.get('success')}")
print(f"  Auto-executed: {result.get('auto_executed')}")
print("  Backend should log: '🧹 Cleared session data sources'")

time.sleep(2)

# Step 3: Select tables
print("\nStep 3: Select tables (after CSV should be cleared)")
response = requests.post(
    f"{BASE_URL}/sessions/{SESSION_ID}/select-tables",
    json={
        "tables": [
            {"database": "northwind", "table": "dow_jones"}
        ]
    }
)
print(f"  ✅ Tables selected: {response.json().get('success')}")
print("  Backend should log: 'Current CSV: None' ← CRITICAL CHECK")

# Step 4: Generate code with tables
print("\nStep 4: Generate code with tables")
response = requests.post(
    f"{BASE_URL}/generate",
    json={
        "prompt": "Show first 5 rows from the table",
        "session_id": SESSION_ID
    }
)
result = response.json()
print(f"  ✅ Code generated: {result.get('success')}")

if result.get('success'):
    code = result.get('code', '')
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    # Check if code references CSV or table
    has_csv = 'test.csv' in code or 'uploaded' in code.lower()
    has_table = 'dow_jones' in code or 'northwind' in code
    
    print(f"Code references CSV: {has_csv}")
    print(f"Code references table: {has_table}")
    
    if has_table and not has_csv:
        print("\n✅ SUCCESS: Code uses tables, not CSV")
        print("Session isolation is working correctly!")
    elif has_csv:
        print("\n❌ FAILURE: Code still references CSV from previous prompt")
        print("Session was NOT cleared properly")
        print("\nGenerated code:")
        print(code[:500])
    else:
        print("\n⚠️  WARNING: Code doesn't reference either CSV or table")
else:
    print(f"\n❌ Code generation failed: {result.get('error')}")

print("\n" + "=" * 80)
print("Check backend logs for:")
print("  1. '🧹 Cleared session data sources' after step 2")
print("  2. 'Current CSV: None' in step 3")
print("  3. '📊 Session state' showing CSV: None, Tables: 1 in step 4")
print("=" * 80)
