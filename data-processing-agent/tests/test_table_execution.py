#!/usr/bin/env python3
"""Test script to verify fetch_spark_results is called for table executions"""

import boto3
import json
import time

def test_table_execution():
    """Test table-based execution to ensure fetch_spark_results is called"""
    
    # Initialize Bedrock AgentCore client
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test payload with table selection
    session_id = f"test-session-{int(time.time())}-{''.join([str(i) for i in range(10)])}"
    payload = {
        "prompt": "Find the top 5 transactions by closing price from the NASDAQ data",
        "session_id": session_id,
        "selected_tables": ["northwind.nasdaq"],
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/test_table_execution/",
        "execution_platform": "emr"
    }
    
    agent_arn = "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
    
    print("Testing table execution with fetch_spark_results fix...")
    print(f"Session ID: {session_id}")
    print(f"Selected tables: {payload['selected_tables']}")
    print(f"Output path: {payload['s3_output_path']}")
    print()
    
    try:
        # Invoke the agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Read the response
        if 'response' in response:
            result_text = response['response'].read().decode('utf-8')
            print("Agent Response:")
            print("=" * 50)
            print(result_text)
            print("=" * 50)
            
            # Try to parse as JSON
            try:
                result_json = json.loads(result_text)
                print("\nParsed JSON Response:")
                print(f"Execution Result: {result_json.get('execution_result', 'N/A')}")
                print(f"Actual Results Count: {len(result_json.get('actual_results', []))}")
                print(f"S3 Output Path: {result_json.get('s3_output_path', 'N/A')}")
                
                # Check if actual_results is populated (indicates fetch_spark_results was called)
                if result_json.get('actual_results'):
                    print("✅ SUCCESS: fetch_spark_results was called and returned data")
                    print(f"Sample data: {result_json['actual_results'][:2]}")
                elif 'actual_results' in result_json:
                    print("⚠️  PARTIAL: fetch_spark_results was called but returned empty data")
                else:
                    print("❌ FAILED: fetch_spark_results was not called (missing actual_results field)")
                    
            except json.JSONDecodeError:
                print("Response is not valid JSON")
                # Check if the response mentions fetch_spark_results
                if 'fetch_spark_results' in result_text.lower():
                    print("✅ fetch_spark_results was mentioned in response")
                else:
                    print("❌ fetch_spark_results was not mentioned in response")
        else:
            print("No response received from agent")
            
    except Exception as e:
        print(f"Error invoking agent: {e}")

if __name__ == "__main__":
    test_table_execution()
