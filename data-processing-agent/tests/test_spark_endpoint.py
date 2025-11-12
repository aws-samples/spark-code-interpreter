#!/usr/bin/env python3
import requests
import json
import time

url = "http://localhost:8000/spark/generate"
payload = {
    "prompt": "Show first 5 rows",
    "session_id": "test-endpoint-123",
    "s3_input_path": "s3://spark-data-260005718447-us-east-1/test.csv",
    "execution_platform": "lambda"
}

print(f"🔍 Testing Spark /generate endpoint")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\n" + "="*80 + "\n")

start_time = time.time()
try:
    response = requests.post(url, json=payload, timeout=90)
    elapsed = time.time() - start_time
    
    print(f"⏱️  Response time: {elapsed:.2f}s")
    print(f"📊 Status code: {response.status_code}")
    print("\n" + "="*80 + "\n")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS - Response JSON:")
        print(json.dumps(result, indent=2))
        
        # Check what's in the result
        if result.get("success"):
            print("\n" + "="*80 + "\n")
            print("🎯 Analyzing result structure:")
            print(f"  - success: {result.get('success')}")
            print(f"  - framework: {result.get('framework')}")
            print(f"  - result type: {type(result.get('result'))}")
            
            if isinstance(result.get('result'), str):
                print(f"  - result length: {len(result.get('result'))} chars")
                print(f"  - result preview: {result.get('result')[:200]}...")
            elif isinstance(result.get('result'), dict):
                print(f"  - result keys: {list(result.get('result').keys())}")
    else:
        print(f"❌ ERROR - Status {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    elapsed = time.time() - start_time
    print(f"⏱️  TIMEOUT after {elapsed:.2f}s")
except Exception as e:
    elapsed = time.time() - start_time
    print(f"❌ ERROR after {elapsed:.2f}s: {e}")
    import traceback
    traceback.print_exc()
