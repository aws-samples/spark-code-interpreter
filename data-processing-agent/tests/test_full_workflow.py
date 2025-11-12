#!/usr/bin/env python3

import boto3
import json
import time

def test_full_workflow():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Clear, specific request for Ray code generation and validation
    test_request = {
        "prompt": "Please generate Ray code that creates a remote function to calculate the factorial of a number. The function should take an integer n as input and return n!. Then demonstrate calling this function with n=5 and print the result.",
        "ray_cluster_ip": "172.31.4.12"
    }
    
    print("Testing full workflow: FastAPI → Supervisor Agent → Code Generation Agent → MCP Gateway → Lambda → Ray Cluster")
    print(f"Request: {test_request['prompt']}")
    print("-" * 80)
    
    try:
        # Invoke supervisor agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
            payload=json.dumps(test_request)
        )
        
        print(f"✓ Supervisor agent invoked successfully")
        print(f"  Status Code: {response['statusCode']}")
        print(f"  Session ID: {response['runtimeSessionId']}")
        
        # Read the streaming response
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            print(f"\n✓ Response received ({len(result)} characters)")
            
            # Try to parse as JSON for better formatting
            try:
                parsed_result = json.loads(result)
                print("\n📋 Supervisor Agent Response:")
                print("-" * 40)
                print(parsed_result)
                
                # Check if the response indicates successful code generation and validation
                response_text = parsed_result.lower() if isinstance(parsed_result, str) else str(parsed_result).lower()
                
                if "factorial" in response_text and ("ray" in response_text or "@ray.remote" in response_text):
                    print("\n✅ SUCCESS: Response contains Ray factorial code")
                    
                if "validated" in response_text or "succeeded" in response_text:
                    print("✅ SUCCESS: Code appears to have been validated")
                    
                if "error" in response_text or "failed" in response_text:
                    print("❌ WARNING: Response indicates potential errors")
                    
            except json.JSONDecodeError:
                print("Response is not valid JSON, showing raw response:")
                print(result)
                
        # Check recent Lambda logs to confirm MCP Gateway called Lambda
        print(f"\n🔍 Checking Lambda logs for recent invocations...")
        logs_client = boto3.client('logs', region_name='us-east-1')
        
        # Get recent log streams
        log_streams = logs_client.describe_log_streams(
            logGroupName='/aws/lambda/ray-code-validation',
            orderBy='LastEventTime',
            descending=True,
            limit=3
        )
        
        recent_invocations = 0
        for stream in log_streams['logStreams']:
            # Check if log stream is from the last 5 minutes
            current_time = time.time() * 1000  # Convert to milliseconds
            if current_time - stream['lastEventTimestamp'] < 300000:  # 5 minutes
                recent_invocations += 1
                
        if recent_invocations > 0:
            print(f"✅ SUCCESS: Found {recent_invocations} recent Lambda invocation(s)")
            print("✅ SUCCESS: MCP Gateway is successfully routing calls to Lambda function")
        else:
            print("❌ WARNING: No recent Lambda invocations found")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    test_full_workflow()
