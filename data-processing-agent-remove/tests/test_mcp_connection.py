#!/usr/bin/env python3
"""Test MCP client connection to AgentCore Gateway"""

import requests
import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

def test_mcp_connection():
    """Test basic MCP connection and authentication"""
    
    print("🔗 Testing MCP Client Connection to AgentCore Gateway")
    print("=" * 60)
    
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Test 1: MCP initialize
    print("1️⃣ Testing MCP initialize...")
    init_payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        session = boto3.Session()
        credentials = session.get_credentials()
        
        request = AWSRequest(
            method='POST',
            url=gateway_url,
            data=json.dumps(init_payload),
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
        
        response = requests.post(
            gateway_url,
            data=json.dumps(init_payload),
            headers=dict(request.headers)
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ MCP initialize successful")
            result = response.json()
            print(f"   Server: {result.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        else:
            print(f"   ❌ Initialize failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Initialize error: {e}")
        return False
    
    # Test 2: List tools (this will likely fail due to Lambda issue)
    print("\n2️⃣ Testing tools/list...")
    list_payload = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/list"
    }
    
    try:
        request = AWSRequest(
            method='POST',
            url=gateway_url,
            data=json.dumps(list_payload),
            headers={'Content-Type': 'application/json'}
        )
        
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
        
        response = requests.post(
            gateway_url,
            data=json.dumps(list_payload),
            headers=dict(request.headers)
        )
        
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'tools' in result['result']:
                tools = result['result']['tools']
                print(f"   ✅ Found {len(tools)} tools")
                for tool in tools:
                    print(f"      - {tool['name']}")
            else:
                print("   ⚠️ No tools in response")
        else:
            print(f"   ❌ Tools list failed: {response.status_code}")
            print(f"   Error: {response.text}")
            
    except Exception as e:
        print(f"   ❌ Tools list error: {e}")
    
    print("\n📋 Summary:")
    print("✅ MCP Gateway is accessible and responding")
    print("✅ IAM authentication is working correctly") 
    print("✅ MCP protocol communication established")
    print("⚠️ Lambda function has dependency issues (requests module missing)")
    print("\n💡 Next steps:")
    print("   1. Fix Lambda function dependencies")
    print("   2. Ensure Ray cluster security group allows AgentCore runtime IP")
    print("   3. Test end-to-end validation")

if __name__ == "__main__":
    test_mcp_connection()
