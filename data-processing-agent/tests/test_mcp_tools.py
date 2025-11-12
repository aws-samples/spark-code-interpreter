#!/usr/bin/env python3

import json
import requests
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

def test_mcp_tools():
    """Test MCP Gateway available tools"""
    
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
    print(f"Init response: {response.status_code}")
    
    if response.status_code != 200:
        print(f"Init failed: {response.text}")
        return
    
    # List available tools
    tools_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    print("Listing available tools...")
    response = make_signed_mcp_request(tools_request)
    print(f"Tools response status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Available tools: {json.dumps(result, indent=2)}")
    else:
        print(f"Tools list failed: {response.text}")

if __name__ == "__main__":
    test_mcp_tools()
