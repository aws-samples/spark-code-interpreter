#!/usr/bin/env python3
import json
import boto3
import uuid

# Initialize client
agentcore_client = boto3.client('bedrock-agentcore', region_name='us-east-1')

SPARK_SUPERVISOR_ARN = "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"

session_id = f"test-{uuid.uuid4().hex}"

payload = {
    "prompt": "Show me the first 5 rows of the data",
    "session_id": session_id,
    "s3_input_path": "s3://spark-data-260005718447-us-east-1/test.csv",
    "selected_tables": None,
    "execution_platform": "lambda"
}

print(f"🔍 Testing Spark Supervisor Agent")
print(f"Session ID: {session_id}")
print(f"Payload: {json.dumps(payload, indent=2)}")
print("\n" + "="*80 + "\n")

try:
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn=SPARK_SUPERVISOR_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=json.dumps(payload)
    )
    
    response_body = response["response"].read()
    result_text = response_body.decode('utf-8')
    
    print("📦 RAW RESPONSE:")
    print(result_text)
    print("\n" + "="*80 + "\n")
    
    # Try parsing
    try:
        result_json = json.loads(result_text)
        print("✅ PARSED JSON (Level 1):")
        print(json.dumps(result_json, indent=2))
        print("\n" + "="*80 + "\n")
        
        if isinstance(result_json, dict) and "result" in result_json:
            inner_result = result_json["result"]
            print(f"📝 Inner result type: {type(inner_result)}")
            
            if isinstance(inner_result, str):
                print("🔄 Inner result is string, attempting to parse...")
                try:
                    parsed_inner = json.loads(inner_result)
                    print("✅ PARSED JSON (Level 2):")
                    print(json.dumps(parsed_inner, indent=2))
                    print("\n" + "="*80 + "\n")
                    
                    if isinstance(parsed_inner, dict) and "result" in parsed_inner:
                        final_result = parsed_inner["result"]
                        print(f"📝 Final result type: {type(final_result)}")
                        
                        if isinstance(final_result, str):
                            print("🔄 Final result is string, attempting to parse...")
                            try:
                                final_parsed = json.loads(final_result)
                                print("✅ PARSED JSON (Level 3):")
                                print(json.dumps(final_parsed, indent=2))
                                
                                # Check for validated_code and execution_result
                                if isinstance(final_parsed, dict):
                                    print("\n" + "="*80 + "\n")
                                    print("🎯 EXTRACTED DATA:")
                                    if "validated_code" in final_parsed:
                                        print(f"✅ validated_code: {len(final_parsed['validated_code'])} chars")
                                    if "execution_result" in final_parsed:
                                        print(f"✅ execution_result: {final_parsed['execution_result']}")
                                    if "data" in final_parsed:
                                        print(f"✅ data: {final_parsed['data']}")
                            except json.JSONDecodeError as e:
                                print(f"❌ Level 3 parse failed: {e}")
                                print(f"Raw final result: {final_result[:500]}")
                except json.JSONDecodeError as e:
                    print(f"❌ Level 2 parse failed: {e}")
                    print(f"Raw inner result: {inner_result[:500]}")
    except json.JSONDecodeError as e:
        print(f"❌ Level 1 parse failed: {e}")
        
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
