#!/usr/bin/env python3

import requests
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

MCP_GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'

def make_signed_mcp_request(payload):
    """Make signed request to MCP Gateway"""
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
    
    response = requests.post(
        MCP_GATEWAY_URL,
        data=request.body,
        headers=dict(request.headers),
        timeout=60
    )
    
    return response

def list_all_tools():
    """List all available tools in MCP Gateway"""
    
    # Initialize MCP Gateway
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
    
    print("Initializing MCP Gateway...")
    response = make_signed_mcp_request(init_request)
    if response.status_code != 200:
        print(f"Init failed: {response.text}")
        return None
    
    # List tools
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    print("Listing all available tools...")
    response = make_signed_mcp_request(tools_request)
    
    if response.status_code == 200:
        result = response.json()
        tools = result.get('result', {}).get('tools', [])
        
        print(f"Found {len(tools)} tools:")
        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")
        
        return tools
    else:
        print(f"Failed to list tools: {response.text}")
        return None

def test_new_tool():
    """Test the new ray-code-validation-inline tool"""
    
    # Initialize MCP Gateway
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
    
    # Test new tool
    tool_request = {
        "jsonrpc": "2.0",
        "id": 3,
        "method": "tools/call",
        "params": {
            "name": "ray-code-validation-inline",
            "arguments": {
                "code": "import ray\nray.init(address=\"auto\")\nresult = 1 + 2\nprint(f\"Result: {result}\")",
                "ray_cluster_ip": "172.31.4.12"
            }
        }
    }
    
    print("Testing new tool: ray-code-validation-inline")
    response = make_signed_mcp_request(tool_request)
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Tool response: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"Tool test failed: {response.text}")
        return None

if __name__ == "__main__":
    print("🔍 Listing MCP Gateway Tools")
    print("=" * 40)
    
    tools = list_all_tools()
    
    print("\n" + "=" * 40)
    print("🧪 Testing New Tool")
    
    result = test_new_tool()
    
    if result and 'result' in result:
        content = result['result'].get('content', [{}])[0].get('text', '')
        print(f"\n✅ New tool working! Response: {content}")
    else:
        print(f"\n❌ New tool test failed")
