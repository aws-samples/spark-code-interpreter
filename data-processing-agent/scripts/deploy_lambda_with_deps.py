#!/usr/bin/env python3

import boto3
import zipfile
import os
import subprocess
import tempfile
import shutil

def deploy_lambda_with_deps():
    """Deploy lambda with requests dependency"""
    
    # Create temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Install requests to temp directory
        subprocess.run([
            'pip', 'install', 'requests', '-t', temp_dir
        ], check=True)
        
        # Copy lambda function
        shutil.copy('lambda_function.py', temp_dir)
        
        # Create zip file
        zip_path = 'lambda_with_deps.zip'
        with zipfile.ZipFile(zip_path, 'w') as zip_file:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arc_name = os.path.relpath(file_path, temp_dir)
                    zip_file.write(file_path, arc_name)
    
    # Update lambda function
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    try:
        with open(zip_path, 'rb') as zip_file:
            response = lambda_client.update_function_code(
                FunctionName='ray-validation-inline',
                ZipFile=zip_file.read()
            )
        
        print(f"✅ Lambda function updated with dependencies")
        print(f"   Function ARN: {response['FunctionArn']}")
        
        # Clean up
        os.remove(zip_path)
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to update lambda: {e}")
        return False

if __name__ == "__main__":
    deploy_lambda_with_deps()
