#!/usr/bin/env python3
"""List available tools in AgentCore Gateway"""

import boto3
import json
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def list_gateway_tools():
    """List available tools in MCP Gateway"""
    
    print("🔍 Listing AgentCore Gateway Tools")
    print("=" * 50)
    
    # Gateway URL
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # MCP tools/list request
    mcp_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    try:
        print("🚀 Calling Gateway tools/list...")
        
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
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Available Tools:")
            print("=" * 30)
            print(json.dumps(result, indent=2))
            
            if 'result' in result and 'tools' in result['result']:
                tools = result['result']['tools']
                print(f"\n📋 Found {len(tools)} tools:")
                for tool in tools:
                    print(f"   - {tool['name']}: {tool.get('description', 'No description')}")
            else:
                print("No tools found in response")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"❌ Gateway call failed: {e}")

if __name__ == "__main__":
    list_gateway_tools()
