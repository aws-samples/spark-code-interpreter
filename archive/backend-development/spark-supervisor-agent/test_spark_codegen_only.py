"""Test Spark code generation only (no execution)"""
import boto3
import json
import uuid

# Create client with longer timeout
client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(read_timeout=180)
)

# Generate session ID
session_id = f'test-spark-codegen-{uuid.uuid4().hex}'

# Prepare payload - just ask for code generation
payload = {
    'prompt': 'Generate Spark code to calculate average sales by region from s3://spark-data-025523569182-us-east-1/sample_sales.csv',
    'session_id': session_id
}

print(f'🚀 Testing Spark Code Generation')
print(f'Session ID: {session_id}')
print(f'Prompt: {payload["prompt"]}')
print()

try:
    # Invoke agent
    response = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-EZPQeDGCjR',
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    # Read response
    result = response['response'].read().decode('utf-8')
    print('✅ Response received!')
    print('='*80)
    print(result)
    print('='*80)
    
except Exception as e:
    print(f'❌ Error: {e}')
