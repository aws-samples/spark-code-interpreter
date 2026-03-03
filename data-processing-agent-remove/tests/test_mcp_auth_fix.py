#!/usr/bin/env python3

import boto3
import json
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests
from datetime import datetime

def test_mcp_gateway_with_sigv4():
    """Test MCP Gateway with proper AWS SigV4 authentication"""
    
    # Gateway configuration
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    print("🔧 Testing MCP Gateway with proper AWS SigV4 authentication...")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Using AWS credentials: {credentials.access_key[:10]}...")
    
    # Create MCP initialization request
    mcp_init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        # Create AWS request for signing
        request = AWSRequest(
            method='POST',
            url=GATEWAY_URL,
            data=json.dumps(mcp_init_request),
            headers={
                'Content-Type': 'application/json',
                'X-Amz-Date': datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
            }
        )
        
        # Sign the request
        SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
        
        print("✅ Request signed with SigV4")
        print(f"Authorization header: {request.headers.get('Authorization', 'None')[:50]}...")
        
        # Make the request
        response = requests.post(
            GATEWAY_URL,
            data=request.body,
            headers=dict(request.headers)
        )
        
        print(f"Response status: {response.status_code}")
        print(f"Response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            print("✅ SUCCESS: MCP Gateway authentication working")
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
        else:
            print(f"❌ ERROR: Status {response.status_code}")
            print(f"Response body: {response.text}")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mcp_gateway_with_sigv4()
