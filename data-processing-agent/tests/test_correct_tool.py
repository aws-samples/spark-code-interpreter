#!/usr/bin/env python3

import requests
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

MCP_GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'

def make_signed_mcp_request(payload):
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=MCP_GATEWAY_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    return requests.post(MCP_GATEWAY_URL, data=request.body, headers=dict(request.headers), timeout=60)

def test_new_tool():
    # Initialize
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
    
    response = make_signed_mcp_request(init_request)
    if response.status_code != 200:
        return None
    
    # Test new tool with correct name
    tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ray-code-validation-inline___validate_ray_code",
            "arguments": {
                "code": "import ray\nray.init(address=\"auto\")\nresult = 1 + 2\nprint(f\"Result: {result}\")",
                "ray_cluster_ip": "172.31.4.12"
            }
        }
    }
    
    print("Testing: ray-code-validation-inline___validate_ray_code")
    response = make_signed_mcp_request(tool_request)
    
    print(f"Status: {response.status_code}")
    result = response.json()
    print(f"Response: {json.dumps(result, indent=2)}")
    
    if 'result' in result and 'content' in result['result']:
        content = result['result']['content'][0]['text']
        print(f"Content: {content}")
        return content
    
    return None

if __name__ == "__main__":
    test_new_tool()
