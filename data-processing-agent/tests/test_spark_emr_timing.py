#!/usr/bin/env python3
import boto3
import json
import time
import uuid

SPARK_SUPERVISOR_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR'

def test_spark_emr():
    """Test Spark agent with EMR execution"""
    client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(
            read_timeout=480,  # 8 minutes
            connect_timeout=30,
            retries={'max_attempts': 0}
        )
    )
    
    session_id = f"test-emr-{uuid.uuid4().hex}"
    
    payload = {
        "prompt": "Load the sales data and show the first 5 rows",
        "session_id": session_id,
        "s3_input_path": "s3://strands-agent-data/sample-data/sales.csv",
        "selected_tables": ["sales"],
        "execution_platform": "emr"
    }
    
    print(f"🔵 Testing Spark agent with EMR execution...")
    print(f"Session: {session_id}")
    
    start = time.time()
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=SPARK_SUPERVISOR_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        response_body = response["response"].read()
        elapsed = time.time() - start
        
        print(f"✅ Response received in {elapsed:.2f}s")
        print(f"Response size: {len(response_body)} bytes")
        
        return elapsed
        
    except Exception as e:
        elapsed = time.time() - start
        print(f"❌ Failed after {elapsed:.2f}s: {e}")
        return elapsed

if __name__ == "__main__":
    test_spark_emr()
