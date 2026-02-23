#!/usr/bin/env python3
"""Test Bedrock model access"""
import boto3

model_id = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
region = "us-east-1"

print(f"🧪 Testing Bedrock model access")
print(f"📋 Model: {model_id}")
print(f"🌍 Region: {region}")

try:
    client = boto3.client('bedrock-runtime', region_name=region)
    
    response = client.converse(
        modelId=model_id,
        messages=[
            {
                "role": "user",
                "content": [{"text": "Say hello"}]
            }
        ]
    )
    
    print(f"\n✅ Model is accessible!")
    print(f"📝 Response: {response['output']['message']['content'][0]['text']}")
    
except Exception as e:
    print(f"\n❌ Error accessing model: {e}")
    print(f"\n🔍 Error type: {type(e).__name__}")
