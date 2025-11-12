#!/usr/bin/env python3
"""Test /validate endpoint with sample Ray code"""

import requests
import json
import time

def test_validate_endpoint():
    """Test /validate endpoint calling supervisor agent"""
    
    print("🧪 Testing Backend /validate Endpoint")
    print("=" * 50)
    
    # Sample Ray code
    sample_code = """import ray
ray.init(address="auto")

# Simple computation
data = [1, 2, 3, 4, 5]
ds = ray.data.from_items(data)
result = ds.map(lambda x: x * 2).sum()
print(f"Result: {result}")
"""
    
    # Test payload
    payload = {
        "code": sample_code,
        "session_id": f"validate_test_{int(time.time())}"
    }
    
    print(f"📝 Sample Ray Code:")
    print(sample_code)
    print(f"🆔 Session ID: {payload['session_id']}")
    print("-" * 50)
    
    try:
        print("⏳ Making /validate request...")
        
        response = requests.post(
            "http://localhost:8000/validate",
            json=payload,
            timeout=120
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Validate Response:")
            print(json.dumps(result, indent=2))
            
            # Check validation result
            if result.get("success"):
                print("\n🎉 SUCCESS: Code validated successfully!")
                if "VALIDATED" in str(result.get("output", "")):
                    print("✅ MCP Gateway validation working!")
            else:
                print(f"\n⚠️ Validation failed: {result.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_validate_endpoint()
