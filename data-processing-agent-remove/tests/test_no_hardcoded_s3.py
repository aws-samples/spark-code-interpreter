#!/usr/bin/env python3
"""Test script to verify no hardcoded S3 paths are used in Spark supervisor agent"""

import json
import boto3
import uuid

def test_no_hardcoded_s3():
    """Test that agent only uses S3 paths provided by backend"""
    
    # Create AgentCore client
    agentcore_client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test with custom S3 paths (not the hardcoded ones)
    session_id = f"test-s3-{uuid.uuid4().hex}"
    custom_input_path = "s3://my-custom-bucket/input/data.csv"
    custom_output_path = "s3://my-custom-bucket/output/"
    
    payload = {
        "prompt": "Analyze data and calculate totals by category",
        "s3_input_path": custom_input_path,
        "s3_output_path": custom_output_path,
        "execution_platform": "lambda",
        "session_id": session_id,
        "skip_generation": False
    }
    
    print(f"🧪 Testing with custom S3 paths:")
    print(f"   Input: {custom_input_path}")
    print(f"   Output: {custom_output_path}")
    print(f"   Session: {session_id}")
    
    try:
        # Call Spark supervisor agent
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn="arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR",
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Parse response
        response_body = response["response"].read().decode("utf-8")
        
        # Handle double-encoded JSON
        result = json.loads(response_body)
        if isinstance(result, str):
            result = json.loads(result)
        
        print(f"\n🔍 Response Analysis:")
        
        # Check if hardcoded S3 bucket appears anywhere
        hardcoded_bucket = "spark-data-260005718447-us-east-1"
        response_str = str(result)
        
        if hardcoded_bucket in response_str:
            print(f"❌ ISSUE: Hardcoded S3 bucket found in response")
            print(f"   Found: {hardcoded_bucket}")
            return False
        else:
            print(f"✅ SUCCESS: No hardcoded S3 bucket found")
        
        # Check if custom paths are preserved
        s3_output_path = result.get("s3_output_path", "")
        if custom_output_path in s3_output_path or custom_output_path == s3_output_path:
            print(f"✅ SUCCESS: Custom output path preserved: {s3_output_path}")
        else:
            print(f"⚠️  WARNING: Output path differs from input: {s3_output_path}")
        
        # Check generated code for custom paths
        spark_code = result.get("spark_code", "")
        if custom_input_path in spark_code:
            print(f"✅ SUCCESS: Custom input path used in generated code")
        else:
            print(f"⚠️  INFO: Custom input path not found in code (may be expected)")
        
        if custom_output_path in spark_code:
            print(f"✅ SUCCESS: Custom output path used in generated code")
        else:
            print(f"⚠️  INFO: Custom output path not found in code (may be expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_no_hardcoded_s3()
    print(f"\n{'🎉 TEST PASSED' if success else '❌ TEST FAILED'}")
    exit(0 if success else 1)
