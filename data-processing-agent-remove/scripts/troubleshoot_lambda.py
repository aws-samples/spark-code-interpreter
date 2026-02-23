#!/usr/bin/env python3
"""Troubleshoot Lambda network connectivity to Ray cluster"""

import boto3
import json

def troubleshoot_lambda():
    """Test Lambda with detailed network diagnostics"""
    
    # Test code with network diagnostics
    test_code = """
import socket
import requests
import time

def test_connectivity():
    ray_ip = "100.27.32.218"
    ray_port = 8265
    
    print(f"Testing connectivity to Ray cluster at {ray_ip}:{ray_port}")
    
    # Test 1: Basic socket connection
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        result = sock.connect_ex((ray_ip, ray_port))
        sock.close()
        
        if result == 0:
            print(f"✅ Socket connection to {ray_ip}:{ray_port} successful")
        else:
            print(f"❌ Socket connection failed with error code: {result}")
    except Exception as e:
        print(f"❌ Socket test error: {e}")
    
    # Test 2: HTTP request to Ray dashboard
    try:
        response = requests.get(f"http://{ray_ip}:{ray_port}/api/cluster_status", timeout=10)
        print(f"✅ HTTP request successful: {response.status_code}")
        print(f"Response: {response.text[:200]}...")
    except requests.exceptions.ConnectTimeout:
        print("❌ HTTP request timed out")
    except requests.exceptions.ConnectionError as e:
        print(f"❌ HTTP connection error: {e}")
    except Exception as e:
        print(f"❌ HTTP request error: {e}")
    
    # Test 3: DNS resolution
    try:
        import socket
        ip = socket.gethostbyname(ray_ip)
        print(f"✅ DNS resolution: {ray_ip} -> {ip}")
    except Exception as e:
        print(f"❌ DNS resolution error: {e}")
    
    # Test 4: Network interface info
    try:
        import subprocess
        result = subprocess.run(['ip', 'route'], capture_output=True, text=True, timeout=5)
        print(f"Network routes: {result.stdout[:200]}...")
    except:
        print("Could not get network route info")

test_connectivity()
"""
    
    print("🔍 Troubleshooting Lambda Network Connectivity")
    print("=" * 60)
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        "code": test_code,
        "ray_cluster_ip": "100.27.32.218"
    }
    
    try:
        print("🚀 Running network diagnostics in Lambda...")
        
        response = lambda_client.invoke(
            FunctionName='ray-code-validation',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        
        print("📋 Diagnostic Results:")
        print("=" * 40)
        print(json.dumps(result, indent=2))
        
    except Exception as e:
        print(f"❌ Diagnostic test failed: {e}")

if __name__ == "__main__":
    troubleshoot_lambda()
