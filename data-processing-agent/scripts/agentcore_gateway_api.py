#!/usr/bin/env python3

import requests
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

def make_signed_gateway_request(method, url, data=None):
    """Make signed request to AgentCore Gateway management API"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method=method,
        url=url,
        data=json.dumps(data) if data else None,
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.request(
        method=method,
        url=url,
        data=request.body,
        headers=dict(request.headers),
        timeout=60
    )
    
    return response

def create_lambda_target_agentcore():
    """Create lambda target using AgentCore Gateway management API"""
    
    gateway_id = "ray-validation-gateway-e9r35gofyj"
    
    # Try the management API endpoint structure
    management_url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/gateways/{gateway_id}/lambda-targets"
    
    # Lambda target configuration based on documentation
    target_config = {
        "targetName": "ray-validation-inline",
        "lambdaFunctionArn": "arn:aws:lambda:us-east-1:260005718447:function:ray-validation-inline",
        "authenticationConfiguration": {
            "type": "API_KEY"
        }
    }
    
    print(f"🎯 Creating lambda target via AgentCore management API")
    print(f"URL: {management_url}")
    print(f"Config: {json.dumps(target_config, indent=2)}")
    
    response = make_signed_gateway_request('POST', management_url, target_config)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code in [200, 201]:
        print("✅ Lambda target created successfully!")
        return response.json()
    else:
        print("❌ Failed to create lambda target")
        return None

def list_lambda_targets_agentcore():
    """List lambda targets using AgentCore management API"""
    
    gateway_id = "ray-validation-gateway-e9r35gofyj"
    management_url = f"https://bedrock-agentcore.us-east-1.amazonaws.com/gateways/{gateway_id}/lambda-targets"
    
    print(f"📋 Listing lambda targets via AgentCore management API")
    print(f"URL: {management_url}")
    
    response = make_signed_gateway_request('GET', management_url)
    
    print(f"Response status: {response.status_code}")
    print(f"Response: {response.text}")
    
    if response.status_code == 200:
        return response.json()
    else:
        return None

def main():
    print("🚀 AgentCore Gateway Lambda Target Management")
    print("=" * 60)
    
    # List existing targets
    print("\n1. Listing existing lambda targets...")
    existing = list_lambda_targets_agentcore()
    
    print("\n" + "-" * 60)
    
    # Create new lambda target
    print("\n2. Creating new lambda target...")
    result = create_lambda_target_agentcore()
    
    if result:
        print(f"\n✅ Successfully created lambda target for ray-validation-inline!")
    else:
        print(f"\n❌ Failed to create lambda target")

if __name__ == "__main__":
    main()
