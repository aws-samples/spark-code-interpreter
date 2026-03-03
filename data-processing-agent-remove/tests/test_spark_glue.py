#!/usr/bin/env python3
"""Test Spark code generation with Glue table"""
import requests
import json
import uuid

# Generate session ID
session_id = f"test-session-{uuid.uuid4().hex}"

# Test payload
payload = {
    "prompt": "find top 10 transactions by closing price",
    "session_id": session_id,
    "framework": "spark",
    "selected_tables": [
        {
            "database": "northwind",
            "table": "nasdaq"
        }
    ],
    "execution_platform": "lambda"
}

print(f"🧪 Testing Spark code generation with Glue table")
print(f"📋 Session ID: {session_id}")
print(f"📊 Table: northwind.nasdaq")
print(f"💬 Prompt: {payload['prompt']}")
print(f"\n⏳ Calling backend endpoint...")

try:
    response = requests.post(
        "http://localhost:8000/spark/generate",
        json=payload,
        timeout=1300  # 21+ minutes
    )
    
    print(f"\n✅ Response Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n📦 Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print(f"\n✅ SUCCESS!")
            if "result" in result and "spark_code" in result["result"]:
                print(f"\n📝 Generated Spark Code:")
                print("=" * 80)
                print(result["result"]["spark_code"])
                print("=" * 80)
        else:
            print(f"\n❌ FAILED: {result.get('error', 'Unknown error')}")
    else:
        print(f"\n❌ HTTP Error: {response.text}")
        
except requests.exceptions.Timeout:
    print(f"\n⏱️ Request timed out after 21 minutes")
except Exception as e:
    print(f"\n❌ Error: {e}")
