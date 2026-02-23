#!/usr/bin/env python3
"""Test script to verify Spark supervisor agent code preservation fix"""

import json
import boto3
import uuid

def test_spark_code_preservation():
    """Test that Spark supervisor agent returns actual code, not placeholders"""
    
    # Create AgentCore client
    agentcore_client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test payload - simple analysis request
    session_id = f"test-{uuid.uuid4().hex}"
    
    payload = {
        "prompt": "Analyze sales data by region. Calculate total sales and average order value for each region.",
        "s3_input_path": "s3://spark-data-260005718447-us-east-1/master_dataset.csv",
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/",
        "execution_platform": "lambda",
        "session_id": session_id,
        "skip_generation": False
    }
    
    print(f"🧪 Testing Spark code preservation with session: {session_id}")
    print(f"📝 Request: {payload['prompt']}")
    
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
        print(f"📤 Raw response length: {len(response_body)} characters")
        
        try:
            # Try to parse as JSON first
            result = json.loads(response_body)
            
            # Check if spark_code contains actual code or placeholder
            spark_code = result.get("spark_code", "")
            
            print(f"\n🔍 Analysis Results:")
            print(f"   Execution Result: {result.get('execution_result', 'N/A')}")
            print(f"   Code Length: {len(spark_code)} characters")
            
            # Check for placeholder text
            has_placeholder = "Full code as generated" in spark_code or "see execution above" in spark_code
            has_actual_code = "from pyspark.sql import SparkSession" in spark_code and len(spark_code) > 200
            
            print(f"   Has Placeholder Text: {'❌ YES' if has_placeholder else '✅ NO'}")
            print(f"   Has Actual Code: {'✅ YES' if has_actual_code else '❌ NO'}")
            
            if has_placeholder:
                print(f"\n❌ ISSUE FOUND: Code contains placeholder text")
                print(f"   Problematic section: {spark_code[:500]}...")
                return False
            elif has_actual_code:
                print(f"\n✅ SUCCESS: Code preservation working correctly")
                print(f"   Code preview: {spark_code[:200]}...")
                return True
            else:
                print(f"\n⚠️  UNCLEAR: Code doesn't contain placeholders but may be incomplete")
                print(f"   Code content: {spark_code[:300]}...")
                return False
                
        except json.JSONDecodeError as e:
            # Response might be plain text, check for placeholders in raw response
            print(f"📝 Response is not JSON, checking raw content...")
            
            has_placeholder = "Full code as generated" in response_body or "see execution above" in response_body
            has_actual_code = "from pyspark.sql import SparkSession" in response_body and len(response_body) > 200
            
            print(f"   Has Placeholder Text: {'❌ YES' if has_placeholder else '✅ NO'}")
            print(f"   Has Actual Code: {'✅ YES' if has_actual_code else '❌ NO'}")
            
            if has_placeholder:
                print(f"\n❌ ISSUE FOUND: Response contains placeholder text")
                print(f"   Problematic section: {response_body[:500]}...")
                return False
            elif has_actual_code:
                print(f"\n✅ SUCCESS: Response contains actual code")
                print(f"   Code preview: {response_body[:200]}...")
                return True
            else:
                print(f"\n⚠️  Response format unclear")
                print(f"   Content: {response_body[:300]}...")
                return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = test_spark_code_preservation()
    exit(0 if success else 1)
