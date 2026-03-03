import boto3
import json
import uuid

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

payload = {
    "prompt": "Generate code to create sample data with 3 rows and 2 columns",
    "session_id": f"test-{uuid.uuid4().hex}",
    "execution_platform": "lambda"
}

print("Sending request...")
response = client.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
    runtimeSessionId=payload['session_id'],
    payload=json.dumps(payload)
)

result = response['response'].read().decode('utf-8')
print("\n=== RAW RESPONSE ===")
print(result)
print("\n=== PARSED JSON ===")
try:
    parsed = json.loads(result)
    print(json.dumps(parsed, indent=2))
except Exception as e:
    print(f"Failed to parse: {e}")
