#!/usr/bin/env python3

import boto3
import json
from botocore.exceptions import ClientError

def get_agentcore_client():
    """Get AgentCore client"""
    return boto3.client('bedrock-agentcore', region_name='us-east-1')

def list_lambda_targets(gateway_id):
    """List existing lambda targets"""
    client = get_agentcore_client()
    
    try:
        # Use the gateway management API to list targets
        response = client.list_actors(
            gatewayIdentifier=gateway_id
        )
        return response
    except Exception as e:
        print(f"Error listing targets: {e}")
        return None

def create_lambda_target(gateway_id, target_name, lambda_function_arn):
    """Create new lambda target"""
    client = get_agentcore_client()
    
    target_config = {
        "name": target_name,
        "type": "lambda",
        "configuration": {
            "functionArn": lambda_function_arn,
            "authenticationMethod": "API_KEY"
        }
    }
    
    try:
        response = client.create_actor(
            gatewayIdentifier=gateway_id,
            actorConfiguration=target_config
        )
        return response
    except Exception as e:
        print(f"Error creating lambda target: {e}")
        return None

def main():
    gateway_id = "ray-validation-gateway-e9r35gofyj"
    
    # List existing targets
    print("📋 Listing existing lambda targets...")
    existing_targets = list_lambda_targets(gateway_id)
    if existing_targets:
        print(f"Existing targets: {json.dumps(existing_targets, indent=2)}")
    
    # Create new lambda target for ray-validation-inline
    lambda_arn = "arn:aws:lambda:us-east-1:260005718447:function:ray-validation-inline"
    target_name = "ray-validation-inline"
    
    print(f"\n🎯 Creating lambda target for {target_name}...")
    result = create_lambda_target(gateway_id, target_name, lambda_arn)
    
    if result:
        print(f"✅ Successfully created lambda target: {target_name}")
        print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"❌ Failed to create lambda target: {target_name}")

if __name__ == "__main__":
    main()
