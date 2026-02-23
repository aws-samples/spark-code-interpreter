#!/usr/bin/env python3

import requests
import json

def test_direct_backend():
    """Test backend with simple Ray code"""
    
    # Simple Ray code that should work
    ray_code = """
import ray

# Initialize Ray
ray.init(address="auto")

@ray.remote
def add(a, b):
    return a + b

# Execute the addition
result = ray.get(add.remote(1, 2))
print(f"Result: {result}")
"""
    
    # Test backend directly
    backend_url = "http://localhost:8000/execute"
    payload = {
        "code": ray_code.strip(),
        "session_id": "test_session_12345678901234567890123456789012345"
    }
    
    print("Testing backend directly...")
    response = requests.post(backend_url, json=payload)
    print(f"Backend response: {response.status_code}")
    print(f"Response: {response.json()}")

def test_frontend():
    """Test frontend execution"""
    
    # Test frontend
    frontend_url = "http://localhost:3000"
    print(f"\nFrontend should be available at: {frontend_url}")
    print("You can test the complete flow by:")
    print("1. Opening the frontend in a browser")
    print("2. Entering: Generate Ray code to add 1 and 2")
    print("3. Clicking Execute")

if __name__ == "__main__":
    test_direct_backend()
    test_frontend()
