#!/usr/bin/env python3
import boto3
import json
import uuid

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

agent_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9'
session_id = f"test-codegen-{uuid.uuid4().hex}"

payload = {
    'prompt': 'Generate simple Python code to print hello world',
    'session_id': session_id
}

try:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        qualifier='DEFAULT',
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    result = response['response'].read().decode('utf-8')
    print(f"✅ Success!")
    print(f"Response: {result}")
except Exception as e:
    print(f"❌ Error: {e}")
