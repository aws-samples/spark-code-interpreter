#!/usr/bin/env python3

import boto3
import json

def create_lambda_tool():
    """Create lambda tool in AgentCore Gateway"""
    
    # Use bedrock-agentcore client
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    gateway_id = "ray-validation-gateway-e9r35gofyj"
    
    # Lambda tool configuration
    tool_config = {
        "toolName": "ray-validation-inline___validate_ray_code",
        "description": "Validates Ray code by executing it on a remote Ray cluster",
        "lambdaFunction": {
            "functionArn": "arn:aws:lambda:us-east-1:260005718447:function:ray-validation-inline"
        },
        "inputSchema": {
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
        # Try different operation names based on documentation
        operations_to_try = [
            'create_tool',
            'add_lambda_tool', 
            'create_lambda_target',
            'register_lambda_function'
        ]
        
        for op_name in operations_to_try:
            if hasattr(client, op_name):
                print(f"Found operation: {op_name}")
                try:
                    result = getattr(client, op_name)(
                        gatewayId=gateway_id,
                        **tool_config
                    )
                    print(f"✅ Successfully created lambda tool using {op_name}")
                    print(f"Result: {json.dumps(result, indent=2)}")
                    return result
                except Exception as e:
                    print(f"Error with {op_name}: {e}")
            else:
                print(f"Operation not found: {op_name}")
        
        # If no operations found, list available operations
        print("\nAvailable operations:")
        operations = [attr for attr in dir(client) if not attr.startswith('_') and callable(getattr(client, attr))]
        for op in sorted(operations):
            print(f"  {op}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    create_lambda_tool()
