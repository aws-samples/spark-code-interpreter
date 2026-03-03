"""Test execute flow with sample Python file"""

import boto3
import json
import uuid

SUPERVISOR_AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'

# Read sample file
with open('../samples/monte_carlo_pi.py', 'r') as f:
    code = f.read()

print("Testing EXECUTE_ONLY flow")
print(f"Code length: {len(code)} characters")
print(f"First 100 chars: {code[:100]}")
print("=" * 60)

agentcore_client = boto3.client(
    'bedrock-agentcore',
    region_name='us-east-1',
    config=boto3.session.Config(read_timeout=300, connect_timeout=60)
)

session_id = f"test-exec-{uuid.uuid4().hex}"

# Simulate backend's execute flow
payload = {
    "prompt": f"EXECUTE_ONLY: Run this code and return the execution output:\n\n{code}",
    "ray_cluster_ip": "172.31.4.12"
}

print(f"Prompt length: {len(payload['prompt'])} characters")
print(f"Prompt first 200 chars: {payload['prompt'][:200]}")
print("=" * 60)

try:
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=SUPERVISOR_AGENT_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    response_body = response["response"].read()
    if response_body:
        try:
            result = json.loads(response_body.decode("utf-8"))
            result_str = str(result) if not isinstance(result, str) else result
        except json.JSONDecodeError:
            result_str = response_body.decode("utf-8")
    else:
        result_str = "No response"
    
    print("\n✅ Response:")
    print("=" * 60)
    print(result_str)
    print("=" * 60)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
