#!/usr/bin/env python3

import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from datetime import datetime, timezone

def make_signed_request(url, payload):
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=url,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.post(
        url,
        data=request.body,
        headers=dict(request.headers)
    )
    
    return response

def test_monte_carlo_pi_validation():
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Monte Carlo Pi calculation code using Ray
    monte_carlo_pi_code = """
import ray
import random

@ray.remote
def monte_carlo_sample(num_samples):
    count = 0
    for _ in range(num_samples):
        x = random.uniform(-1, 1)
        y = random.uniform(-1, 1)
        if x*x + y*y <= 1:
            count += 1
    return count

# Initialize Ray
ray.init()

# Number of samples per worker
samples_per_worker = 1000000
num_workers = 4

# Create remote tasks
futures = [monte_carlo_sample.remote(samples_per_worker) for _ in range(num_workers)]

# Get results
results = ray.get(futures)

# Calculate pi
total_samples = samples_per_worker * num_workers
total_inside = sum(results)
pi_estimate = 4.0 * total_inside / total_samples

print(f"Estimated value of pi: {pi_estimate}")
print(f"Actual value of pi: {3.14159265359}")
print(f"Error: {abs(pi_estimate - 3.14159265359)}")
"""

    print("GENERATED MONTE CARLO PI CODE:")
    print("=" * 60)
    print(monte_carlo_pi_code)
    print("=" * 60)
    
    print("\nValidating code via MCP Gateway...")
    
    # Initialize MCP
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "test-client", "version": "1.0.0"}
        }
    }
    
    response = make_signed_request(GATEWAY_URL, init_request)
    if response.status_code != 200:
        print(f"❌ Initialize failed: {response.status_code}")
        return
    
    # Call validation tool
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "ray-validation-inline___validate_ray_code",
            "arguments": {
                "code": monte_carlo_pi_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        }
    }
    
    response = make_signed_request(GATEWAY_URL, tool_call_request)
    
    if response.status_code == 200:
        result = response.json()
        print("✅ VALIDATION RESULT:")
        print(json.dumps(result, indent=2))
        
        if 'result' in result and 'content' in result['result']:
            content = result['result']['content'][0]['text']
            validation_data = json.loads(content)
            if validation_data.get('success'):
                print(f"\n✅ SUCCESS: Code validated and executed on Ray cluster!")
                print(f"Job ID: {validation_data.get('job_id')}")
                print(f"Status: {validation_data.get('status')}")
    else:
        print(f"❌ Validation failed: {response.status_code}")

if __name__ == "__main__":
    test_monte_carlo_pi_validation()
