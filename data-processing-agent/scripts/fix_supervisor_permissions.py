#!/usr/bin/env python3

import boto3
import json

def add_mcp_gateway_permissions():
    """Add MCP Gateway permissions to supervisor agent runtime role"""
    
    iam = boto3.client('iam', region_name='us-east-1')
    role_name = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-5130eca7b1"
    
    # Additional policy for MCP Gateway access
    mcp_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "MCPGatewayAccess",
                "Effect": "Allow",
                "Action": [
                    "bedrock-agentcore:InvokeGateway",
                    "bedrock-agentcore:GetGateway",
                    "bedrock-agentcore:ListGateways",
                    "bedrock-agentcore:GetGatewayTarget",
                    "bedrock-agentcore:ListGatewayTargets"
                ],
                "Resource": [
                    "arn:aws:bedrock-agentcore:us-east-1:260005718447:gateway/*"
                ]
            }
        ]
    }
    
    try:
        # Add the MCP Gateway policy as an inline policy
        response = iam.put_role_policy(
            RoleName=role_name,
            PolicyName="MCPGatewayAccessPolicy",
            PolicyDocument=json.dumps(mcp_policy)
        )
        
        print("✅ Successfully added MCP Gateway permissions to supervisor agent role")
        print(f"   Role: {role_name}")
        print(f"   Policy: MCPGatewayAccessPolicy")
        
        # List all policies to confirm
        policies = iam.list_role_policies(RoleName=role_name)
        print(f"\n📋 Current inline policies:")
        for policy_name in policies['PolicyNames']:
            print(f"   - {policy_name}")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to add MCP Gateway permissions: {e}")
        return False

if __name__ == "__main__":
    success = add_mcp_gateway_permissions()
    exit(0 if success else 1)
