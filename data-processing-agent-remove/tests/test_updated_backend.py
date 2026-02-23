#!/usr/bin/env python3

import requests
import json
import time

def test_updated_backend():
    """Test the updated backend with frontend-compatible endpoints"""
    
    BASE_URL = "http://localhost:8000"
    
    print("🧪 TESTING UPDATED BACKEND")
    print("=" * 60)
    
    # Test health endpoint
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✅ Health check passed")
            health_data = response.json()
            print(f"   Status: {health_data['status']}")
        else:
            print("❌ Health check failed")
            return False
    except Exception as e:
        print(f"❌ Backend not running: {e}")
        print("💡 Start backend with: cd backend && python main.py")
        return False
    
    # Test code generation endpoint
    print("\n🔧 Testing /generate endpoint...")
    try:
        generate_payload = {
            "prompt": "generate ray code to calculate sum of numbers 1 to 10",
            "session_id": f"test_session_{int(time.time())}"
        }
        
        response = requests.post(f"{BASE_URL}/generate", json=generate_payload)
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ Code generation successful")
                print(f"   Generated code length: {len(result['code'])} characters")
                generated_code = result['code']
            else:
                print(f"❌ Code generation failed: {result['error']}")
                return False
        else:
            print(f"❌ Generate endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Generate test failed: {e}")
        return False
    
    # Test code execution endpoint
    print("\n🚀 Testing /execute endpoint...")
    try:
        execute_payload = {
            "code": generated_code,
            "session_id": f"test_exec_{int(time.time())}"
        }
        
        response = requests.post(f"{BASE_URL}/execute", json=execute_payload)
        if response.status_code == 200:
            result = response.json()
            if result['success']:
                print("✅ Code execution successful")
                print(f"   Output: {result['output']}")
                print(f"   Job ID: {result.get('job_id', 'N/A')}")
            else:
                print(f"❌ Code execution failed: {result['error']}")
                return False
        else:
            print(f"❌ Execute endpoint failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Execute test failed: {e}")
        return False
    
    print("\n🎉 ALL TESTS PASSED!")
    print("✅ Backend is ready for frontend integration")
    return True

if __name__ == "__main__":
    success = test_updated_backend()
    exit(0 if success else 1)
