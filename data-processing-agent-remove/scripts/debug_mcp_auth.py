#!/usr/bin/env python3
"""Debug MCP Gateway authentication"""

import boto3
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

def debug_mcp_auth():
    """Debug MCP Gateway authentication and authorization"""
    
    print("🔍 Debugging MCP Gateway Authentication")
    print("=" * 50)
    
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Get current credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    print(f"📋 Current AWS Credentials:")
    print(f"   Access Key: {credentials.access_key[:10]}...")
    print(f"   Region: us-east-1")
    print(f"   Gateway URL: {gateway_url}")
    
    # Test 1: Initialize MCP
    print(f"\n🧪 Test 1: MCP Initialize")
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "clientInfo": {"name": "debug-client", "version": "1.0.0"}
        }
    }
    
    # Create signed request
    request = AWSRequest(
        method='POST',
        url=gateway_url,
        data=json.dumps(init_request),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    print(f"   Request Headers: {dict(request.headers)}")
    
    response = requests.post(
        gateway_url,
        data=request.body,
        headers=dict(request.headers),
        timeout=30
    )
    
    print(f"   Response Status: {response.status_code}")
    print(f"   Response Headers: {dict(response.headers)}")
    print(f"   Response Body: {response.text}")
    
    if response.status_code != 200:
        print(f"❌ Authentication failed at initialize step")
        return
    
    # Test 2: List tools
    print(f"\n🧪 Test 2: List Tools")
    list_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    request = AWSRequest(
        method='POST',
        url=gateway_url,
        data=json.dumps(list_request),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.post(
        gateway_url,
        data=request.body,
        headers=dict(request.headers),
        timeout=30
    )
    
    print(f"   Response Status: {response.status_code}")
    print(f"   Response Body: {response.text}")
    
    if response.status_code == 200:
        result = response.json()
        if 'result' in result and 'tools' in result['result']:
            tools = result['result']['tools']
            print(f"   Available Tools: {len(tools)}")
            for tool in tools:
                print(f"      - {tool.get('name')}")
                
            # Check if our target exists
            target_names = [tool.get('name') for tool in tools]
            if 'ray-code-validation-inline___validate_ray_code' in target_names:
                print(f"   ✅ Target 'ray-code-validation-inline___validate_ray_code' found")
            else:
                print(f"   ❌ Target 'ray-code-validation-inline___validate_ray_code' NOT found")
                print(f"   Available targets: {target_names}")

if __name__ == "__main__":
    debug_mcp_auth()
