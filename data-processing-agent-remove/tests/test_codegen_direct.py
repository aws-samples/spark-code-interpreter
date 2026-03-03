#!/usr/bin/env python3

import boto3
import json

def test_code_generation_direct():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    test_request = {
        "prompt": "generate Ray code to calculate the value of pi using monte carlo method with distributed computing"
    }
    
    print("Testing Code Generation Agent directly...")
    print(f"Prompt: {test_request['prompt']}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9',
            payload=json.dumps(test_request)
        )
        
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            
            try:
                parsed_result = json.loads(result)
                print("CODE GENERATION AGENT RESPONSE:")
                print("=" * 60)
                print(parsed_result)
                print("=" * 60)
            except json.JSONDecodeError:
                print("CODE GENERATION AGENT RESPONSE:")
                print("=" * 60)
                print(result)
                print("=" * 60)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_code_generation_direct()
