"""Test Spark Supervisor Agent deployment"""
import boto3
import json

AGENT_ID = 'spark_supervisor_agent-EZPQeDGCjR'
REGION = 'us-east-1'

def test_agent_status():
    """Test if agent is deployed and ready"""
    try:
        client = boto3.client('bedrock-agentcore', region_name=REGION)
        response = client.get_runtime(runtimeId=AGENT_ID)
        print(f"✅ Agent Status: {response['status']}")
        print(f"✅ Agent ARN: {response['arn']}")
        return True
    except Exception as e:
        print(f"❌ Agent status check failed: {e}")
        return False

def test_agent_invocation():
    """Test agent invocation with sample payload"""
    try:
        client = boto3.client('bedrock-agentcore-runtime', region_name=REGION)
        
        # Simple test payload
        test_payload = {
            "spark_code": """
from pyspark.sql import SparkSession
spark = SparkSession.builder.appName("test").getOrCreate()
df = spark.read.option("header", "true").csv("s3://test-bucket/data.csv")
df.show()
""",
            "s3_input_path": "s3://test-bucket/data.csv",
            "execution_platform": "lambda"
        }
        
        response = client.invoke_agent(
            agentId=AGENT_ID,
            sessionId='test-session-' + str(int(time.time())),
            inputText=json.dumps(test_payload)
        )
        
        # Read response
        result = ""
        for event in response['completion']:
            if 'chunk' in event:
                result += event['chunk']['bytes'].decode('utf-8')
        
        print(f"✅ Agent invocation successful")
        print(f"Response: {result[:200]}...")
        return True
    except Exception as e:
        print(f"❌ Agent invocation failed: {e}")
        return False

if __name__ == "__main__":
    import time
    
    print("🧪 Testing Spark Supervisor Agent Deployment\n")
    
    print("1. Checking agent status...")
    status_ok = test_agent_status()
    
    if status_ok:
        print("\n2. Testing agent invocation...")
        invocation_ok = test_agent_invocation()
        
        if invocation_ok:
            print("\n✅ All tests passed!")
        else:
            print("\n⚠️ Invocation test failed")
    else:
        print("\n⚠️ Agent not ready")
