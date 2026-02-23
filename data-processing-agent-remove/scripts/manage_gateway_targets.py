#!/usr/bin/env python3

import boto3
import json

def get_bedrock_agent_client():
    """Get Bedrock Agent client"""
    return boto3.client('bedrock-agent', region_name='us-east-1')

def list_gateway_targets():
    """List existing gateway targets"""
    client = get_bedrock_agent_client()
    
    try:
        # Try different operations to find gateway management
        operations = [
            'list_gateways',
            'get_gateway', 
            'list_lambda_targets'
        ]
        
        for op in operations:
            if hasattr(client, op):
                print(f"Found operation: {op}")
            else:
                print(f"Operation not found: {op}")
                
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("🔍 Checking available Bedrock Agent operations...")
    
    client = get_bedrock_agent_client()
    
    # List all available operations
    operations = [attr for attr in dir(client) if not attr.startswith('_')]
    gateway_ops = [op for op in operations if 'gateway' in op.lower()]
    
    print(f"Gateway-related operations: {gateway_ops}")
    
    # Check if we can find gateway information
    try:
        # Try to get gateway info using different approaches
        print("\n🔍 Attempting to find gateway configuration...")
        
        # Check if there are any gateway-related operations
        for op in gateway_ops:
            print(f"Available gateway operation: {op}")
            
    except Exception as e:
        print(f"Error exploring operations: {e}")

if __name__ == "__main__":
    main()
