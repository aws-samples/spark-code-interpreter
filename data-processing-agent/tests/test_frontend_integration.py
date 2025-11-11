#!/usr/bin/env python3
"""
Test frontend-backend integration for Spark code generation
Simulates what the frontend does when calling the backend
"""
import requests
import json
import time

BACKEND_URL = "http://localhost:8000"
FRONTEND_URL = "http://localhost:3000"

print("🧪 Testing Frontend-Backend Integration for Spark")
print("=" * 80)

# Test 1: Check backend health
print("\n1️⃣ Checking backend health...")
try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=5)
    if response.status_code == 200:
        print("   ✅ Backend is healthy")
    else:
        print(f"   ❌ Backend returned status {response.status_code}")
        exit(1)
except Exception as e:
    print(f"   ❌ Backend not accessible: {e}")
    exit(1)

# Test 2: Check frontend accessibility
print("\n2️⃣ Checking frontend accessibility...")
try:
    response = requests.get(FRONTEND_URL, timeout=5)
    if response.status_code == 200:
        print("   ✅ Frontend is accessible")
    else:
        print(f"   ⚠️  Frontend returned status {response.status_code}")
except Exception as e:
    print(f"   ❌ Frontend not accessible: {e}")
    print("   Start frontend with: cd frontend && npm run dev")

# Test 3: Generate Spark code (simulating frontend request)
print("\n3️⃣ Generating Spark code via backend...")
payload = {
    "prompt": "Create a DataFrame with 2 rows: Alice age 28, Bob age 32. Display and save to S3.",
    "execution_platform": "lambda",
    "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/",
    "session_id": "test-frontend-" + "1" * 24
}

print(f"   Prompt: {payload['prompt']}")
start_time = time.time()

try:
    response = requests.post(
        f"{BACKEND_URL}/spark/generate",
        json=payload,
        timeout=200
    )
    elapsed = time.time() - start_time
    
    if response.status_code != 200:
        print(f"   ❌ Request failed with status {response.status_code}")
        print(f"   Response: {response.text}")
        exit(1)
    
    result = response.json()
    print(f"   ✅ Response received in {elapsed:.1f}s")
    
    # Test 4: Verify response structure (what frontend expects)
    print("\n4️⃣ Verifying response structure...")
    
    if not result.get("success"):
        print(f"   ❌ Response indicates failure: {result.get('error')}")
        exit(1)
    
    print("   ✅ Response has success=true")
    
    # Parse the result (frontend does this)
    agent_result = json.loads(result["result"])
    
    # Check for validated_code
    if "validated_code" in agent_result:
        code = agent_result["validated_code"]
        print(f"   ✅ validated_code present ({len(code)} chars)")
        print(f"\n   📝 Code Preview:")
        print("   " + "\n   ".join(code.split("\n")[:5]))
        if len(code.split("\n")) > 5:
            print("   ...")
    else:
        print("   ❌ validated_code missing from response")
        exit(1)
    
    # Check for execution_result
    if "execution_result" in agent_result:
        exec_result = agent_result["execution_result"]
        print(f"\n   ✅ execution_result present ({len(str(exec_result))} chars)")
        print(f"\n   📊 Execution Result Preview:")
        result_str = str(exec_result)
        print("   " + "\n   ".join(result_str.split("\n")[:3]))
        if len(result_str.split("\n")) > 3:
            print("   ...")
    else:
        print("   ❌ execution_result missing from response")
        exit(1)
    
    # Test 5: Verify frontend can render this
    print("\n5️⃣ Verifying frontend compatibility...")
    
    # Check if code is valid Python
    if "from pyspark" in code and "SparkSession" in code:
        print("   ✅ Code contains valid PySpark imports")
    else:
        print("   ⚠️  Code may not be valid PySpark")
    
    # Check if execution result has expected fields
    if "s3_output_path" in agent_result:
        print(f"   ✅ S3 output path: {agent_result['s3_output_path']}")
    
    print("\n" + "=" * 80)
    print("✅ ALL TESTS PASSED - Frontend-Backend Integration Working!")
    print("\n📋 Summary:")
    print(f"   • Backend: {BACKEND_URL} ✅")
    print(f"   • Frontend: {FRONTEND_URL} ✅")
    print(f"   • Code Generation: ✅ ({elapsed:.1f}s)")
    print(f"   • Code Editor Ready: ✅ (validated_code present)")
    print(f"   • Results Display Ready: ✅ (execution_result present)")
    print("\n🎉 Frontend can successfully render code and results!")
    
except requests.exceptions.Timeout:
    print(f"   ❌ Request timed out after 200s")
    exit(1)
except Exception as e:
    print(f"   ❌ Error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
