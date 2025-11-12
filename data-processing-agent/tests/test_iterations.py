#!/usr/bin/env python3
import requests
import time

print("🧪 Testing Iterative Code Validation\n")

# Test 1: Simple code (should pass on first try)
print("Test 1: Simple dataset creation")
resp = requests.post(
    "http://localhost:8000/generate",
    json={"prompt": "Create 100 rows and count them", "session_id": "test1"},
    timeout=60
)
result = resp.json()
print(f"  Success: {result.get('success')}")
print(f"  Iterations: {result.get('iterations')}")
print(f"  Code length: {len(result.get('code', ''))}")

# Test 2: CSV with map operation
print("\nTest 2: CSV with map operation")
csv_resp = requests.post(
    "http://localhost:8000/upload-csv",
    json={"filename": "data.csv", "content": "name,age\nAlice,30\nBob,25", "session_id": "test2"},
    timeout=10
)
print(f"  CSV uploaded: {csv_resp.json().get('s3_path')}")

resp = requests.post(
    "http://localhost:8000/generate",
    json={"prompt": "Read CSV and add 5 to each age", "session_id": "test2"},
    timeout=90
)
result = resp.json()
print(f"  Success: {result.get('success')}")
print(f"  Iterations: {result.get('iterations')}")

# Test 3: Execute the generated code
print("\nTest 3: Execute validated code")
if result.get('success'):
    exec_resp = requests.post(
        "http://localhost:8000/execute",
        json={"code": result['code'], "session_id": "test2"},
        timeout=60
    )
    exec_result = exec_resp.json()
    print(f"  Execution success: {exec_result.get('success')}")
    print(f"  Output preview: {exec_result.get('result', '')[:150]}")

print("\n✅ All tests completed!")
