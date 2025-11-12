#!/usr/bin/env python3

import requests
import json
import boto3
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone

# Gateway configuration
GATEWAY_ID = "ray-validation-gateway-e9r35gofyj"
GATEWAY_BASE_URL = f"https://{GATEWAY_ID}.gateway.bedrock-agentcore.us-east-1.amazonaws.com"

def make_signed_request(method, url, data=None):
    """Make signed request to AgentCore Gateway"""
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

def list_lambda_targets():
    """List existing lambda targets"""
    url = f"{GATEWAY_BASE_URL}/targets"
    
    print(f"📋 Listing lambda targets from: {url}")
    response = make_signed_request('GET', url)
    
    print(f"Response status: {response.status_code}")
    if response.status_code == 200:
        targets = response.json()
        print(f"Existing targets: {json.dumps(targets, indent=2)}")
        return targets
    else:
        print(f"Error response: {response.text}")
        return None

def create_lambda_target():
    """Create new lambda target for ray-validation-inline"""
    url = f"{GATEWAY_BASE_URL}/targets"
    
    # Lambda target configuration
    target_config = {
        "name": "ray-validation-inline",
        "type": "lambda",
        "configuration": {
            "functionArn": "arn:aws:lambda:us-east-1:260005718447:function:ray-validation-inline",
            "authenticationMethod": "API_KEY"
        }
    }
    
    print(f"🎯 Creating lambda target: {target_config['name']}")
    print(f"Target config: {json.dumps(target_config, indent=2)}")
    
    response = make_signed_request('POST', url, target_config)
    
    print(f"Response status: {response.status_code}")
    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Successfully created lambda target!")
        print(f"Response: {json.dumps(result, indent=2)}")
        return result
    else:
        print(f"❌ Failed to create lambda target")
        print(f"Error response: {response.text}")
        return None

def main():
    print("🚀 AgentCore Gateway Lambda Target Management")
    print("=" * 50)
    
    # List existing targets first
    existing_targets = list_lambda_targets()
    
    print("\n" + "-" * 50)
    
    # Create new lambda target
    new_target = create_lambda_target()
    
    if new_target:
        print(f"\n✅ Lambda target 'ray-validation-inline' created successfully!")
    else:
        print(f"\n❌ Failed to create lambda target")

if __name__ == "__main__":
    main()
