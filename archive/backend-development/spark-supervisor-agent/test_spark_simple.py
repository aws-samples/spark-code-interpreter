"""Test Spark code generation through supervisor agent"""
import boto3
import json
import time

AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-EZPQeDGCjR'
REGION = 'us-east-1'

def test_spark_code_generation():
    """Test Spark code generation with sample prompt"""
    
    print("🧪 Testing Spark Supervisor Agent\n")
    print(f"Agent ARN: {AGENT_ARN}")
    print(f"Region: {REGION}\n")
    
    # Sample test payload - session ID must be at least 33 characters
    import uuid
    test_payload = {
        "prompt": "Calculate the average sales amount by region from the sales data",
        "s3_input_path": "s3://spark-data-025523569182-us-east-1/sample_sales.csv",
        "s3_output_path": "s3://spark-data-025523569182-us-east-1/output/test_results",
        "execution_platform": "lambda",
        "session_id": f"test-spark-session-{uuid.uuid4().hex}"  # 51 chars total
    }
    
    print("📝 Test Payload:")
    print(json.dumps(test_payload, indent=2))
    print("\n" + "="*60 + "\n")
    
    try:
        # Initialize Bedrock AgentCore client with extended timeout
        from botocore.config import Config
        client = boto3.client(
            'bedrock-agentcore',
            region_name=REGION,
            config=Config(read_timeout=600, connect_timeout=10)
        )
        
        print("🚀 Invoking Spark Supervisor Agent...")
        
        # Invoke the agent runtime with correct parameters
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=test_payload['session_id'],
            payload=json.dumps(test_payload)
        )
        
        print("✅ Agent invoked successfully\n")
        print("📥 Response received\n")
        
        # Read the streaming response
        if 'response' in response:
            response_body = response['response'].read().decode('utf-8')
            print("="*60)
            print("\n📄 Response Body:\n")
            print(response_body)
            print("\n" + "="*60 + "\n")
            
            # Try to parse as JSON
            try:
                parsed_output = json.loads(response_body)
                print("✅ Response is valid JSON\n")
                print("📊 Parsed Response:")
                print(json.dumps(parsed_output, indent=2))
                
                # Check for specific fields
                if 'spark_code' in parsed_output:
                    print("\n✅ Spark code generated:")
                    print("-" * 60)
                    print(parsed_output['spark_code'])
                    print("-" * 60)
                
                if 'validation_errors' in parsed_output:
                    if parsed_output['validation_errors']:
                        print("\n⚠️ Validation errors found:")
                        for error in parsed_output['validation_errors']:
                            print(f"  - {error}")
                    else:
                        print("\n✅ No validation errors")
                
                if 'status' in parsed_output:
                    print(f"\n📊 Status: {parsed_output['status']}")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Response is not JSON: {e}")
                print("Raw response content:")
                print(response_body[:500])
        else:
            print("="*60)
            print("\n📄 Full Response:\n")
            print(json.dumps(response, indent=2, default=str))
            print("\n" + "="*60 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error occurred: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
        # Print detailed error information
        if hasattr(e, 'response'):
            print("\n📋 Error Response:")
            print(json.dumps(e.response, indent=2, default=str))
        
        import traceback
        print("\n📋 Full Traceback:")
        print(traceback.format_exc())
        
        return False

if __name__ == "__main__":
    success = test_spark_code_generation()
    
    if success:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
