"""Test Spark code generation through supervisor agent"""
import boto3
import json
import time
import requests
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest

AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-EZPQeDGCjR'
REGION = 'us-east-1'

def get_agent_endpoint():
    """Get the agent's HTTP endpoint"""
    try:
        client = boto3.client('bedrock-agentcore', region_name=REGION)
        response = client.get_runtime(runtimeId='spark_supervisor_agent-EZPQeDGCjR')
        
        # Get endpoint URL
        if 'endpoint' in response:
            endpoint_url = response['endpoint'].get('url')
            if endpoint_url:
                return endpoint_url
        
        print("⚠️ No endpoint URL found in response")
        print(json.dumps(response, indent=2, default=str))
        return None
    except Exception as e:
        print(f"❌ Error getting endpoint: {e}")
        return None

def test_spark_code_generation():
    """Test Spark code generation with sample prompt"""
    
    print("🧪 Testing Spark Supervisor Agent\n")
    print(f"Agent ARN: {AGENT_ARN}")
    print(f"Region: {REGION}\n")
    
    # Get agent endpoint
    print("🔍 Getting agent endpoint...")
    endpoint_url = get_agent_endpoint()
    
    if not endpoint_url:
        print("❌ Could not get agent endpoint")
        return False
    
    print(f"✅ Agent endpoint: {endpoint_url}\n")
    
    # Sample test payload
    test_payload = {
        "prompt": "Calculate the average sales amount by region from the sales data",
        "s3_input_path": "s3://spark-data-025523569182-us-east-1/sample_sales.csv",
        "execution_platform": "lambda",
        "session_id": f"test-{int(time.time())}"
    }
    
    print("📝 Test Payload:")
    print(json.dumps(test_payload, indent=2))
    print("\n" + "="*60 + "\n")
    
    try:
        # Get AWS credentials
        session = boto3.Session()
        credentials = session.get_credentials()
        
        # Prepare request
        request_body = json.dumps(test_payload)
        
        # Create AWS request for signing
        request = AWSRequest(
            method='POST',
            url=endpoint_url,
            data=request_body,
            headers={
                'Content-Type': 'application/json'
            }
        )
        
        # Sign request with SigV4
        SigV4Auth(credentials, 'bedrock-agentcore', REGION).add_auth(request)
        
        print("🚀 Invoking Spark Supervisor Agent via HTTP...")
        
        # Make HTTP request
        response = requests.post(
            endpoint_url,
            data=request_body,
            headers=dict(request.headers),
            timeout=60
        )
        
        print(f"✅ Response status: {response.status_code}\n")
        
        if response.status_code == 200:
            response_text = response.text
            print(f"📥 Response length: {len(response_text)} bytes\n")
            print("="*60)
            print("\n📄 Full Response:\n")
            print(response_text)
            print("\n" + "="*60 + "\n")
            
            # Try to parse as JSON
            try:
                parsed_response = json.loads(response_text)
                print("✅ Response is valid JSON\n")
                print("📊 Parsed Response:")
                print(json.dumps(parsed_response, indent=2))
                
                # Check for specific fields
                if 'spark_code' in parsed_response:
                    print("\n✅ Spark code generated:")
                    print("-" * 60)
                    print(parsed_response['spark_code'])
                    print("-" * 60)
                
                if 'validation_errors' in parsed_response:
                    if parsed_response['validation_errors']:
                        print("\n⚠️ Validation errors found:")
                        for error in parsed_response['validation_errors']:
                            print(f"  - {error}")
                    else:
                        print("\n✅ No validation errors")
                
                if 'status' in parsed_response:
                    print(f"\n📊 Status: {parsed_response['status']}")
                
            except json.JSONDecodeError as e:
                print(f"⚠️ Response is not JSON: {e}")
                print("Raw response content:")
                print(response_text[:500])
            
            return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
        
    except Exception as e:
        print(f"\n❌ Error occurred: {type(e).__name__}")
        print(f"Error message: {str(e)}")
        
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
