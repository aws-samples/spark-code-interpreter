#!/usr/bin/env python3
"""Debug script to see actual Spark supervisor agent response"""

import json
import boto3
import uuid

def debug_spark_response():
    """Debug the actual response from Spark supervisor agent"""
    
    # Create AgentCore client
    agentcore_client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test payload - simple analysis request
    session_id = f"debug-{uuid.uuid4().hex}"
    
    payload = {
        "prompt": "Analyze sales data by region. Calculate total sales and average order value for each region.",
        "s3_input_path": "s3://spark-data-260005718447-us-east-1/master_dataset.csv",
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/",
        "execution_platform": "lambda",
        "session_id": session_id,
        "skip_generation": False
    }
    
    print(f"🔍 Debugging Spark response with session: {session_id}")
    
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
        
        print(f"📤 Raw response:")
        print(f"   Type: {type(response_body)}")
        print(f"   Length: {len(response_body)} characters")
        print(f"   Content: {response_body}")
        
        # Try to parse as JSON
        try:
            result = json.loads(response_body)
            print(f"\n✅ Successfully parsed as JSON")
            print(f"   Type after parsing: {type(result)}")
            
            # If it's a string, try parsing again (double-encoded JSON)
            if isinstance(result, str):
                print(f"   Response is double-encoded JSON, parsing again...")
                result = json.loads(result)
                print(f"   Type after second parsing: {type(result)}")
            
            print(f"   Keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
            if isinstance(result, dict) and 'spark_code' in result:
                spark_code = result['spark_code']
                print(f"   Spark code length: {len(spark_code)}")
                print(f"   Spark code preview: {spark_code[:200]}...")
                
                # Check for placeholder text
                has_placeholder = "Full code as generated" in spark_code or "see execution above" in spark_code
                print(f"   Has placeholder text: {'❌ YES' if has_placeholder else '✅ NO'}")
                
                if not has_placeholder:
                    print(f"\n🎉 SUCCESS: Code preservation is working! No placeholder text found.")
                else:
                    print(f"\n❌ ISSUE: Still contains placeholder text")
                    
        except json.JSONDecodeError as e:
            print(f"\n❌ Failed to parse as JSON: {e}")
            
    except Exception as e:
        print(f"❌ Debug failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_spark_response()
