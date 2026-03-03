#!/usr/bin/env python3

import boto3
import zipfile
import os
import json

def deploy_lambda_with_vpc():
    """Deploy lambda function with VPC configuration"""
    
    # Create deployment package
    zip_filename = 'ray-validation-inline.zip'
    
    with zipfile.ZipFile(zip_filename, 'w') as zip_file:
        zip_file.write('lambda_function.py')
        
        # Add requests library
        import requests
        requests_path = requests.__file__.replace('__init__.py', '')
        for root, dirs, files in os.walk(requests_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(requests_path))
                    zip_file.write(file_path, arcname)
    
    # Read the zip file
    with open(zip_filename, 'rb') as zip_file:
        zip_content = zip_file.read()
    
    # Deploy lambda
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # VPC configuration from existing ray-code-validation function
    vpc_config = {
        'SubnetIds': [
            'subnet-0ffcc9c369d011e54',
            'subnet-04c2c799482ddc064'
        ],
        'SecurityGroupIds': [
            'sg-098a735e14f9f2953'
        ]
    }
    
    try:
        # Update existing function with VPC config
        response = lambda_client.update_function_configuration(
            FunctionName='ray-validation-inline',
            VpcConfig=vpc_config,
            Timeout=300,
            MemorySize=256
        )
        print(f"✅ Updated lambda function VPC configuration")
        print(f"   VPC ID: {response.get('VpcConfig', {}).get('VpcId')}")
        print(f"   Subnets: {response.get('VpcConfig', {}).get('SubnetIds')}")
        print(f"   Security Groups: {response.get('VpcConfig', {}).get('SecurityGroupIds')}")
        
    except Exception as e:
        print(f"❌ Error updating lambda: {e}")
    
    # Clean up
    os.remove(zip_filename)

if __name__ == "__main__":
    deploy_lambda_with_vpc()
