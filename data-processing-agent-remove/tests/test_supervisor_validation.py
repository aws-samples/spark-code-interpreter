#!/usr/bin/env python3

import boto3
import json

def test_supervisor_validation():
    """Test supervisor agent with pre-generated code to validate MCP integration"""
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Simple test with minimal prompt to avoid token limits
    test_request = {
        "prompt": "validate this ray code: import ray\n@ray.remote\ndef test(): return 42\nprint(ray.get(test.remote()))"
    }
    
    print("Testing supervisor agent validation capability...")
    print(f"Prompt: {test_request['prompt']}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
            payload=json.dumps(test_request)
        )
        
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            
            try:
                parsed_result = json.loads(result)
                print("SUPERVISOR AGENT RESPONSE:")
                print("=" * 60)
                print(parsed_result)
                print("=" * 60)
                
                # Check for validation success
                response_text = str(parsed_result).lower()
                if "validated" in response_text or "succeeded" in response_text:
                    print("✅ SUCCESS: Supervisor agent validation working!")
                elif "error" in response_text or "failed" in response_text:
                    print("❌ WARNING: Validation issues detected")
                else:
                    print("ℹ️  INFO: Response received, checking content...")
                    
            except json.JSONDecodeError:
                print("SUPERVISOR AGENT RESPONSE:")
                print("=" * 60)
                print(result)
                print("=" * 60)
                
                # Check raw response
                if "validated" in result.lower() or "succeeded" in result.lower():
                    print("✅ SUCCESS: Supervisor agent validation working!")
                    
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_supervisor_validation()
