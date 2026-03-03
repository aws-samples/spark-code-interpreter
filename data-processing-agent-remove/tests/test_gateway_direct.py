#!/usr/bin/env python3
"""Direct test of AgentCore Gateway and Lambda validation"""

import boto3
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def test_gateway_direct():
    """Test MCP Gateway directly via HTTP endpoint"""
    
    # Sample Ray code
    ray_code = """import ray

ds = ray.data.range(21)
filtered_ds = ds.filter(lambda x: x["id"] % 2 == 0)
result = filtered_ds.sum("id")
print(f"Sum of even numbers 1-20: {result}")"""
    
    print("🧪 Testing AgentCore Gateway Direct Validation")
    print("=" * 60)
    print("📝 Ray Code to Validate:")
    print(ray_code)
    print("=" * 60)
    
    # Gateway URL
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # MCP request payload
    mcp_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "ray-validation-inline___validate_ray_code",
            "arguments": {
                "code": ray_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        }
    }
    
    try:
        print("🚀 Calling AgentCore Gateway via HTTP...")
        
        # Get AWS credentials for signing
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Create signed request
        request = AWSRequest(
            method='POST',
            url=gateway_url,
            data=json.dumps(mcp_payload),
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
        
        # Make request
        response = requests.post(
            gateway_url,
            data=json.dumps(mcp_payload),
            headers=dict(request.headers)
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print("✅ Gateway Response:")
        print("=" * 40)
        
        if response.status_code == 200:
            result = response.json()
            print(json.dumps(result, indent=2))
            
            # Check MCP response
            if 'result' in result and not result['result'].get('isError', True):
                content = result['result']['content'][0]['text']
                validation_result = json.loads(content)
                if validation_result.get('success'):
                    print("\n🎉 SUCCESS - Ray code validated successfully!")
                    if 'job_id' in validation_result:
                        print(f"   Job ID: {validation_result['job_id']}")
                        print(f"   Status: {validation_result['status']}")
                else:
                    print(f"\n❌ VALIDATION FAILED: {validation_result.get('error')}")
            else:
                print("\n❓ Unexpected response format")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Gateway call failed: {e}")

if __name__ == "__main__":
    test_gateway_direct()
