#!/usr/bin/env python3
import requests
import json

print("🧪 Testing Glue Data Catalog Integration\n")

# Test 1: List databases
print("1. Testing database listing...")
resp = requests.get("http://localhost:8000/glue/databases")
result = resp.json()
print(f"   Success: {result.get('success')}")
print(f"   Databases found: {len(result.get('databases', []))}")

# Test 2: Upload CSV
print("\n2. Testing CSV upload...")
csv_content = "id,value\n1,100\n2,200"
resp = requests.post(
    "http://localhost:8000/upload-csv",
    json={"filename": "test.csv", "content": csv_content, "session_id": "gluetest"}
)
csv_result = resp.json()
print(f"   CSV uploaded: {csv_result.get('success')}")
print(f"   S3 path: {csv_result.get('s3_path')}")

# Test 3: Generate code with CSV only
print("\n3. Testing code generation with CSV...")
resp = requests.post(
    "http://localhost:8000/generate",
    json={"prompt": "Read the CSV and show statistics", "session_id": "gluetest"},
    timeout=90
)
gen_result = resp.json()
print(f"   Success: {gen_result.get('success')}")
print(f"   Iterations: {gen_result.get('iterations')}")
print(f"   Code contains CSV path: {'s3://' in gen_result.get('code', '')}")

# Test 4: Execute generated code
print("\n4. Testing code execution...")
resp = requests.post(
    "http://localhost:8000/execute",
    json={"code": gen_result['code'], "session_id": "gluetest"},
    timeout=90
)
exec_result = resp.json()
print(f"   Execution success: {exec_result.get('success')}")
print(f"   Output preview: {exec_result.get('result', '')[:100]}")

print("\n✅ All tests completed!")
print("\nNote: To test with actual Glue tables, create tables in AWS Glue Data Catalog")
print("and they will appear in the dropdown on the left panel of the UI.")
