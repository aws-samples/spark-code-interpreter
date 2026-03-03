#!/usr/bin/env python3

import boto3
import json

def test_lambda():
    """Test ray-validation-inline lambda function directly"""
    
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    test_code = """
import ray
ray.init(address="ray://172.31.4.12:10001")

@ray.remote
def hello():
    return "Hello from Ray!"

result = ray.get(hello.remote())
print(f"Result: {result}")
"""
    
    payload = {
        "code": test_code,
        "ray_cluster_ip": "172.31.4.12"
    }
    
    try:
        print("Testing ray-validation-inline lambda function...")
        response = lambda_client.invoke(
            FunctionName='ray-validation-inline',
            Payload=json.dumps(payload)
        )
        
        result = json.loads(response['Payload'].read())
        print(f"Lambda response: {json.dumps(result, indent=2)}")
        
        if result.get('success'):
            print("✅ Lambda function working correctly")
        else:
            print(f"❌ Lambda function failed: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Lambda test failed: {e}")

if __name__ == "__main__":
    test_lambda()
