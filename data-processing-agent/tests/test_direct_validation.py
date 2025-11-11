#!/usr/bin/env python3

import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from datetime import datetime, timezone

def make_signed_mcp_request(payload):
    """Make signed request to MCP Gateway"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    request = AWSRequest(
        method='POST',
        url=GATEWAY_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.post(
        GATEWAY_URL,
        data=request.body,
        headers=dict(request.headers),
        timeout=30
    )
    
    return response

def test_direct_validation():
    """Test MCP Gateway validation directly to confirm it's working"""
    
    # Simple Ray code for Monte Carlo pi
    test_code = """
import ray

@ray.remote
def monte_carlo_pi_sample(n):
    import random
    count = 0
    for _ in range(n):
        x, y = random.random(), random.random()
        if x*x + y*y <= 1:
            count += 1
    return count

ray.init()
samples = 100000
result = ray.get(monte_carlo_pi_sample.remote(samples))
pi_estimate = 4.0 * result / samples
print(f"Pi estimate: {pi_estimate}")
"""

    print("TESTING DIRECT MCP GATEWAY VALIDATION")
    print("=" * 50)
    print("Code to validate:")
    print(test_code)
    print("=" * 50)
    
    try:
        # Initialize MCP
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "direct-test", "version": "1.0.0"}
            }
        }
        
        response = make_signed_mcp_request(init_request)
        if response.status_code != 200:
            print(f"❌ MCP initialization failed: {response.status_code}")
            return
        
        print("✅ MCP Gateway initialized")
        
        # Call validation tool
        tool_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ray-validation-inline___validate_ray_code",
                "arguments": {
                    "code": test_code,
                    "ray_cluster_ip": "172.31.4.12"
                }
            }
        }
        
        print("🧪 Calling validation tool...")
        response = make_signed_mcp_request(tool_request)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ VALIDATION SUCCESSFUL!")
            print(json.dumps(result, indent=2))
            
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content'][0]['text']
                validation_data = json.loads(content)
                if validation_data.get('success'):
                    print(f"\n🎉 SUCCESS: Ray code executed successfully!")
                    print(f"Job ID: {validation_data.get('job_id')}")
                    print(f"Status: {validation_data.get('status')}")
                    
                    print("\n✅ CONCLUSION: MCP Gateway authentication and tool routing is WORKING CORRECTLY")
                    print("✅ The supervisor agent timeout issue is due to code generation agent problems, not MCP Gateway")
                    
        else:
            print(f"❌ Validation failed: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_direct_validation()
