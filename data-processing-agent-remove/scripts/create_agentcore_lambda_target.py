#!/usr/bin/env python3

import boto3
from agentcore_gateway import Gateway

def create_lambda_target():
    """Create lambda target using AgentCore Gateway SDK"""
    
    # Initialize Gateway client
    gateway = Gateway(
        gateway_id="ray-validation-gateway-e9r35gofyj",
        region="us-east-1"
    )
    
    # Lambda function configuration
    lambda_config = {
        "function_arn": "arn:aws:lambda:us-east-1:260005718447:function:ray-validation-inline",
        "tool_name": "ray-validation-inline___validate_ray_code",
        "description": "Validates Ray code by executing it on a remote Ray cluster",
        "input_schema": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "The Ray code to validate and execute"
                },
                "ray_cluster_ip": {
                    "type": "string", 
                    "description": "IP address of the Ray cluster to execute code on"
                }
            },
            "required": ["code"]
        }
    }
    
    try:
        # Create lambda tool
        result = gateway.create_lambda_tool(**lambda_config)
        print(f"✅ Successfully created lambda target: {lambda_config['tool_name']}")
        print(f"Result: {result}")
        return result
        
    except Exception as e:
        print(f"❌ Error creating lambda target: {e}")
        return None

if __name__ == "__main__":
    create_lambda_target()
