#!/usr/bin/env python3
import boto3
import json
import time

client = boto3.client('bedrock-agentcore', region_name='us-east-1')

agent_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR'

payload = {
    "prompt": "Generate a sample dataframe with 2 rows (Alice age 34, Bob age 45) and write to S3",
    "session_id": f"test-{int(time.time())}",
    "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/",
    "execution_platform": "lambda"
}

print("🚀 Testing Spark Supervisor Agent")
print(f"Payload: {json.dumps(payload, indent=2)}\n")

try:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=agent_arn,
        payload=json.dumps(payload)
    )
    
    print("Response keys:", response.keys())
    print("Full response:", json.dumps(response, indent=2, default=str))
    
    result = json.loads(response.get('payload', response.get('outputDocument', '{}')))
    print("\n✅ Response received:")
    print(json.dumps(result, indent=2))
    
    if result.get('validated_code'):
        print("\n📝 Validated Code:")
        code = result['validated_code']
        print(code[:500] + "..." if len(code) > 500 else code)
    
    if result.get('execution_result'):
        print("\n📊 Execution Result:")
        exec_result = result['execution_result']
        print(exec_result[:500] + "..." if len(exec_result) > 500 else exec_result)
        
except Exception as e:
    print(f"❌ Error: {e}")
