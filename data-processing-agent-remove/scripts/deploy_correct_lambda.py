#!/usr/bin/env python3

import boto3
import zipfile
import os
import json

def create_lambda():
    """Create ray-validation-inline lambda function for MCP Gateway"""
    
    # Create zip file with lambda code
    with zipfile.ZipFile('lambda_function.zip', 'w') as zip_file:
        zip_file.write('lambda_function.py')
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        # Check if function exists
        try:
            lambda_client.get_function(FunctionName='ray-validation-inline')
            print("Function exists, updating...")
            
            with open('lambda_function.zip', 'rb') as zip_file:
                response = lambda_client.update_function_code(
                    FunctionName='ray-validation-inline',
                    ZipFile=zip_file.read()
                )
        except lambda_client.exceptions.ResourceNotFoundException:
            print("Function doesn't exist, creating...")
            
            with open('lambda_function.zip', 'rb') as zip_file:
                response = lambda_client.create_function(
                    FunctionName='ray-validation-inline',
                    Runtime='python3.9',
                    Role='arn:aws:iam::260005718447:role/RayValidationLambdaRole',
                    Handler='lambda_function.lambda_handler',
                    Code={'ZipFile': zip_file.read()},
                    Description='Ray code validation for MCP Gateway',
                    Timeout=300
                )
        
        print(f"✅ Lambda function ray-validation-inline ready")
        print(f"   Function ARN: {response['FunctionArn']}")
        
        # Clean up
        os.remove('lambda_function.zip')
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create/update lambda: {e}")
        return False

if __name__ == "__main__":
    create_lambda()
