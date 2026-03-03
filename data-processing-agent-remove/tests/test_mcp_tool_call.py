#!/usr/bin/env python3

import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from datetime import datetime, timezone

def make_signed_request(url, payload):
    """Make a signed request to MCP Gateway"""
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

def test_mcp_tool_call():
    """Test MCP Gateway tool call with proper authentication"""
    
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    print("🔧 Testing MCP Gateway tool call...")
    
    # Step 1: Initialize
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
        print(f"❌ Initialize failed: {response.status_code} - {response.text}")
        return
    
    print("✅ MCP Gateway initialized")
    
    # Step 2: List tools
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    response = make_signed_request(GATEWAY_URL, list_tools_request)
    if response.status_code != 200:
        print(f"❌ List tools failed: {response.status_code} - {response.text}")
        return
    
    tools_result = response.json()
    print(f"✅ Found tools: {json.dumps(tools_result, indent=2)}")
    
    # Step 3: Call validate_ray_code tool
    test_code = """
import ray

@ray.remote
def square(x):
    return x * x

result = ray.get(square.remote(7))
print(f"Square of 7: {result}")
"""
    
    tool_call_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ray-validation-inline___validate_ray_code",
            "arguments": {
                "code": test_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        }
    }
    
    print(f"🧪 Calling validate_ray_code tool...")
    print(f"Code to validate: {len(test_code)} characters")
    
    response = make_signed_request(GATEWAY_URL, tool_call_request)
    
    print(f"Tool call response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    
    if response.status_code == 200:
        result = response.json()
        print("✅ SUCCESS: Tool call completed")
        print(f"Result: {json.dumps(result, indent=2)}")
        
        # Check if Lambda was invoked successfully
        if 'result' in result and 'content' in result['result']:
            content = result['result']['content']
            if isinstance(content, list) and len(content) > 0:
                text_content = content[0].get('text', '')
                if 'succeeded' in text_content.lower() or 'success' in text_content.lower():
                    print("✅ SUCCESS: Ray code validation succeeded on cluster")
                elif 'error' in text_content.lower() or 'failed' in text_content.lower():
                    print("❌ WARNING: Ray code validation failed")
                else:
                    print(f"ℹ️  INFO: Validation result: {text_content}")
    else:
        print(f"❌ ERROR: Tool call failed")
        print(f"Response body: {response.text}")

if __name__ == "__main__":
    test_mcp_tool_call()
