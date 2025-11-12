#!/usr/bin/env python3

import requests
import json

def test_ray_code_generation():
    """Test Ray code generation after fixing boto3 import"""
    
    # Backend endpoint
    url = "http://localhost:8000/generate"
    
    # Simple test request
    payload = {
        "prompt": "Generate Ray code to calculate the sum of numbers from 1 to 100",
        "session_id": "test-ray-fix-123"
    }
    
    print("Testing Ray code generation...")
    print(f"Request: {payload['prompt']}")
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ SUCCESS: Ray code generation working!")
            print(f"Generated code preview: {result.get('code', 'No code')[:200]}...")
            return True
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timed out")
        return False
    except Exception as e:
        print(f"❌ FAILED: {str(e)}")
        return False

if __name__ == "__main__":
    test_ray_code_generation()
