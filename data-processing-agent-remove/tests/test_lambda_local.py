#!/usr/bin/env python3
"""Test Lambda function directly from local machine"""

import boto3
import json

def test_lambda_local():
    """Invoke Lambda function directly from local machine"""
    
    # Sample Ray code
    ray_code = """import ray

ds = ray.data.range(1, 21)
filtered_ds = ds.filter(lambda x: x["id"] % 2 == 0)
result = filtered_ds.sum("id")
print(f"Sum of even numbers 1-20: {result}")"""
    
    print("🧪 Testing Lambda Function from Local Machine")
    print("=" * 60)
    print("📝 Ray Code to Validate:")
    print(ray_code)
    print("=" * 60)
    
    # Lambda client
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    payload = {
        "code": ray_code,
        "ray_cluster_ip": "100.27.32.218"
    }
    
    try:
        print("🚀 Invoking Lambda function directly...")
        
        response = lambda_client.invoke(
            FunctionName='ray-code-validation',
            Payload=json.dumps(payload)
        )
        
        print(f"📊 Status Code: {response['StatusCode']}")
        
        # Read response payload
        result = json.loads(response['Payload'].read())
        
        print("✅ Lambda Response:")
        print("=" * 40)
        print(json.dumps(result, indent=2))
        
        if result.get('success'):
            print("\n🎉 SUCCESS - Ray code validated successfully!")
            if 'job_id' in result:
                print(f"   Job ID: {result['job_id']}")
        else:
            print(f"\n❌ VALIDATION FAILED: {result.get('error')}")
            
    except Exception as e:
        print(f"❌ Lambda invocation failed: {e}")

if __name__ == "__main__":
    test_lambda_local()
