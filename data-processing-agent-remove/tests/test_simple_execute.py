#!/usr/bin/env python3
"""Test with simple Ray code"""

import requests
import json
import time

def test_simple_execute():
    """Test with very simple Ray code"""
    
    # Simple Ray code that works in lambda
    simple_code = """import ray
print("Hello Ray")
result = 1 + 2
print(f"Result: {result}")"""
    
    payload = {
        "code": simple_code,
        "session_id": f"simple_test_{int(time.time())}"
    }
    
    print("🧪 Testing Simple Ray Code")
    print(f"📝 Code: {simple_code}")
    print(f"🆔 Session: {payload['session_id']}")
    print("-" * 40)
    
    try:
        response = requests.post(
            "http://localhost:8000/execute",
            json=payload,
            timeout=60
        )
        
        print(f"📡 Status: {response.status_code}")
        result = response.json()
        print(f"📋 Response: {json.dumps(result, indent=2)}")
        
        if result.get("success"):
            print("🎉 SUCCESS: New lambda target working!")
        else:
            print(f"⚠️ Failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_simple_execute()
