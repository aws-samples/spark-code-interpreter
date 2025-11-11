#!/usr/bin/env python3

import boto3
import json
import uuid

def test_code_generation_direct():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Exact same prompt as end-to-end test
    test_request = {
        "prompt": "generate ray code to print first 10 prime numbers"
    }
    
    # Proper session ID format
    session_id = f"test-codegen-{uuid.uuid4().hex}"
    
    print("🧪 TESTING CODE GENERATION AGENT DIRECTLY")
    print("=" * 60)
    print(f"Prompt: {test_request['prompt']}")
    print(f"Session ID: {session_id}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9',
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(test_request)
        )
        
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            
            print("📋 CODE GENERATION AGENT RESPONSE:")
            print("=" * 60)
            print(result)
            print("=" * 60)
            
            # Check if it contains prime number logic
            if "prime" in result.lower():
                print("✅ Response mentions primes")
            else:
                print("❌ Response does NOT mention primes")
                
            if "import ray" in result:
                print("✅ Contains Ray import")
            else:
                print("❌ Missing Ray import")
                
            if "@ray.remote" in result:
                print("✅ Contains Ray remote decorator")
            else:
                print("❌ Missing Ray remote decorator")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_code_generation_direct()
