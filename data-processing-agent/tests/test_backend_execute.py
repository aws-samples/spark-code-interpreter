#!/usr/bin/env python3
"""Test FastAPI backend /execute endpoint with sample Ray code"""

import requests
import json
import time

def test_execute_endpoint():
    """Test /execute endpoint with sample Ray code"""
    
    print("🧪 Testing FastAPI Backend /execute Endpoint")
    print("=" * 50)
    
    # Backend URL
    backend_url = "http://localhost:8000"
    
    # Sample Ray code
    sample_code = """import ray
ray.init(address="auto")

# Create simple dataset
data = [1, 2, 3, 4, 5]
ds = ray.data.from_items(data)

# Transform and sum
result = ds.map(lambda x: x * 2).sum()
print(f"Result: {result}")
"""
    
    # Test payload
    payload = {
        "code": sample_code,
        "session_id": f"test_execute_{int(time.time())}"
    }
    
    print(f"📝 Sample Ray Code:")
    print(sample_code)
    print(f"🆔 Session ID: {payload['session_id']}")
    print("-" * 50)
    
    try:
        print("⏳ Making /execute request...")
        
        response = requests.post(
            f"{backend_url}/execute",
            json=payload,
            timeout=120
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Execute Response:")
            print(json.dumps(result, indent=2))
            
            # Check if validation was successful
            if result.get("success"):
                print("\n🎉 SUCCESS: Code executed successfully!")
                if "VALIDATED" in str(result):
                    print("✅ Code was validated using new lambda target!")
            else:
                print(f"\n⚠️ Execution failed: {result.get('error', 'Unknown error')}")
                
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out (this may be normal for first call)")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_execute_endpoint()
