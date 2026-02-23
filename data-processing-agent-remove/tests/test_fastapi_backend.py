#!/usr/bin/env python3
"""Test the updated FastAPI backend with Supervisor Agent Runtime"""

import requests
import json
import time

def test_fastapi_backend():
    """Test the FastAPI backend with new architecture"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Updated FastAPI Backend")
    print("=" * 60)
    
    # Test 1: Health check
    print("1️⃣ Testing health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            health_data = response.json()
            print("   ✅ Health check passed")
            print(f"   Supervisor ARN: {health_data.get('supervisor_agent_arn')}")
            print(f"   Ray Cluster IP: {health_data.get('ray_cluster_ip')}")
        else:
            print(f"   ❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ❌ Health check error: {e}")
        return False
    
    # Test 2: Root endpoint
    print("\n2️⃣ Testing root endpoint...")
    try:
        response = requests.get(f"{base_url}/")
        if response.status_code == 200:
            root_data = response.json()
            print("   ✅ Root endpoint working")
            print(f"   Architecture: {root_data.get('architecture')}")
        else:
            print(f"   ❌ Root endpoint failed: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Root endpoint error: {e}")
    
    # Test 3: Code generation
    print("\n3️⃣ Testing code generation...")
    try:
        payload = {
            "prompt": "Generate Ray code to calculate the sum of numbers 1 to 5"
        }
        
        print(f"   Request: {payload['prompt']}")
        
        response = requests.post(
            f"{base_url}/generate-code",
            json=payload,
            timeout=120  # 2 minutes timeout
        )
        
        if response.status_code == 200:
            result = response.json()
            print("   ✅ Code generation successful")
            print(f"   Session ID: {result.get('session_id')}")
            print(f"   Success: {result.get('success')}")
            
            if result.get('code'):
                print("   Generated Code:")
                print("   " + "=" * 40)
                for line in result['code'].split('\n')[:10]:  # Show first 10 lines
                    print(f"   {line}")
                if len(result['code'].split('\n')) > 10:
                    print("   ... (truncated)")
                print("   " + "=" * 40)
            
            if result.get('error'):
                print(f"   Error: {result.get('error')}")
                
        else:
            print(f"   ❌ Code generation failed: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Code generation error: {e}")
    
    print("\n" + "=" * 60)
    print("🎯 Architecture Flow Tested:")
    print("   User Request → FastAPI → Supervisor Runtime → Code Gen + MCP Gateway")
    print("=" * 60)

if __name__ == "__main__":
    test_fastapi_backend()
