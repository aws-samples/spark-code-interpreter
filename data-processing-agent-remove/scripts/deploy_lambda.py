#!/usr/bin/env python3

import boto3
import zipfile
import os

def deploy_lambda():
    """Deploy updated lambda function"""
    
    # Create zip file with lambda code
    with zipfile.ZipFile('lambda_function.zip', 'w') as zip_file:
        zip_file.write('lambda_function.py')
    
    # Update lambda function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        with open('lambda_function.zip', 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName='ray-code-validation',
                ZipFile=zip_file.read()
            )
        
        print(f"✅ Lambda function updated successfully")
        print(f"   Function ARN: {response['FunctionArn']}")
        print(f"   Last Modified: {response['LastModified']}")
        
        # Clean up
        os.remove('lambda_function.zip')
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update lambda: {e}")
        return False

if __name__ == "__main__":
    deploy_lambda()
