#!/usr/bin/env python3
"""Check MCP Gateway targets and create new one if needed"""

import boto3
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

def list_mcp_tools():
    """List available tools in MCP Gateway"""
    
    print("🔍 Checking MCP Gateway Tools")
    print("=" * 40)
    
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    try:
        # Initialize MCP
        init_payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "tool-checker", "version": "1.0.0"}
            }
        }
        
        response = make_signed_request(gateway_url, init_payload)
        print(f"📡 Initialize: {response.status_code}")
        
        if response.status_code != 200:
            print(f"❌ Init failed: {response.text}")
            return
        
        # List tools
        list_payload = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        response = make_signed_request(gateway_url, list_payload)
        print(f"📋 List tools: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Available tools:")
            
            if 'result' in result and 'tools' in result['result']:
                tools = result['result']['tools']
                for tool in tools:
                    name = tool.get('name', 'Unknown')
                    description = tool.get('description', 'No description')
                    print(f"   🔧 {name}")
                    print(f"      {description}")
                    
                # Check for our target
                target_names = [tool.get('name') for tool in tools]
                if 'ray-code-validation-inline___validate_ray_code' in target_names:
                    print("\n✅ Found ray-code-validation-inline target!")
                elif 'ray-validation-inline___validate_ray_code' in target_names:
                    print("\n⚠️ Found old ray-validation-inline target")
                else:
                    print("\n❌ Target not found in available tools")
            else:
                print(f"❌ Unexpected response: {result}")
        else:
            print(f"❌ List failed: {response.text}")
            
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
    list_mcp_tools()
