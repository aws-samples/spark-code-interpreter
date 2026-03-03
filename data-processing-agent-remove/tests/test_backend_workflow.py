#!/usr/bin/env python3
import requests
import json
import time

# Backend endpoint
url = "http://localhost:8000/spark/generate"

# Sample payload
import uuid
payload = {
    "prompt": "Create a DataFrame with 3 rows: John age 25, Sarah age 30, Mike age 35. Show the data and write to S3.",
    "execution_platform": "lambda",
    "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/",
    "session_id": str(uuid.uuid4())
}

print("🚀 Testing Backend Workflow")
print(f"URL: {url}")
print(f"Payload: {json.dumps(payload, indent=2)}\n")
print("=" * 80)

start_time = time.time()

try:
    response = requests.post(url, json=payload, timeout=300)
    elapsed = time.time() - start_time
    
    print(f"\n✅ Response received in {elapsed:.2f}s")
    print(f"Status Code: {response.status_code}\n")
    
    if response.status_code == 200:
        result = response.json()
        print("📊 Response:")
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            agent_result = result.get("result", {})
            
            # Handle if result is a JSON string
            if isinstance(agent_result, str):
                agent_result = json.loads(agent_result)
            
            if agent_result.get("validated_code"):
                print("\n" + "=" * 80)
                print("📝 VALIDATED CODE:")
                print("=" * 80)
                code = agent_result["validated_code"]
                print(code[:500] + "..." if len(code) > 500 else code)
            
            if agent_result.get("execution_result"):
                print("\n" + "=" * 80)
                print("📊 EXECUTION RESULT:")
                print("=" * 80)
                exec_result = agent_result["execution_result"]
                print(exec_result[:500] + "..." if len(exec_result) > 500 else exec_result)
        else:
            print(f"\n❌ Error: {result.get('error')}")
    else:
        print(f"❌ HTTP Error: {response.text}")
        
except requests.exceptions.ConnectionError:
    print("❌ Error: Backend not running at http://localhost:8000")
    print("\nTo start backend, run:")
    print("  cd /Users/nmurich/strands-agents/agent-core/data-processing-agent/backend")
    print("  conda run -n bedrock-sdk uvicorn main:app --reload")
except Exception as e:
    print(f"❌ Error: {e}")
