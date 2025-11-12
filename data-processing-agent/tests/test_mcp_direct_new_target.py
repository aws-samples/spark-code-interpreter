#!/usr/bin/env python3
"""Test MCP Gateway directly with new lambda target"""

import boto3
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

def test_mcp_gateway_direct():
    """Test MCP Gateway with new ray-code-validation-inline target"""
    
    print("🔗 Testing MCP Gateway with New Lambda Target")
    print("=" * 50)
    
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Test code
    test_code = """import ray
ray.init(address="auto")
result = sum([1, 2, 3])
print(f"Sum: {result}")"""
    
    print(f"🎯 Target: ray-code-validation-inline___validate_ray_code")
    print(f"📝 Test code: {test_code.replace(chr(10), ' | ')}")
    print("-" * 50)
    
    try:
        # Initialize MCP
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        
        response = make_signed_request(gateway_url, init_payload)
        print(f"📡 Initialize: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Init failed: {response.text}")
            return
        
        # Call validation tool with new target name
        tool_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": "ray-code-validation-inline___validate_ray_code",
                "arguments": {
                    "code": test_code,
                    "ray_cluster_ip": "172.31.4.12"
                }
            }
        }
        
        response = make_signed_request(gateway_url, tool_payload)
        print(f"🔧 Tool call: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Response: {json.dumps(result, indent=2)}")
            
            if 'result' in result and 'content' in result['result']:
                content = result['result']['content'][0]['text']
                print(f"📋 Content: {content}")
                
                try:
                    validation_data = json.loads(content)
                    if validation_data.get('success'):
                        print("🎉 SUCCESS: New lambda target working!")
                    else:
                        print(f"⚠️ Validation failed: {validation_data.get('error')}")
                except json.JSONDecodeError:
                    print(f"❌ Invalid JSON in response: {content}")
            else:
                print(f"❌ Unexpected response structure")
        else:
            print(f"❌ Tool call failed: {response.text}")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def make_signed_request(url, payload):
    """Make signed request to MCP Gateway"""
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
    
    return requests.post(
        url,
        data=request.body,
        headers=dict(request.headers),
        timeout=30
    )

if __name__ == "__main__":
    test_mcp_gateway_direct()
