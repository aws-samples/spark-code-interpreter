#!/usr/bin/env python3
"""Test supervisor agent with new ray-code-validation-inline target"""

import boto3
import json
import time

def test_supervisor_agent():
    """Test supervisor agent uses new lambda target"""
    
    print("🧪 Testing Supervisor Agent with ray-code-validation-inline")
    print("=" * 60)
    
    # Configuration
    supervisor_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'
    
    # Create client
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test payload
    test_prompt = "Generate Ray code to create numbers 1 to 3 and sum them"
    session_id = f"test_new_target_{int(time.time())}_{int(time.time() % 1000000):06d}"
    
    print(f"📝 Prompt: {test_prompt}")
    print(f"🆔 Session: {session_id}")
    print("🎯 Expected: Should use ray-code-validation-inline lambda target")
    print("-" * 60)
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn=supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({"prompt": test_prompt})
        )
        
        result = response["response"].read().decode("utf-8")
        
        print("📋 Response:")
        print(result)
        print("-" * 60)
        
        # Check response indicators
        if "VALIDATED" in result:
            print("✅ SUCCESS: Code validated using new lambda target!")
        elif "VALIDATION_ERROR" in result:
            print("⚠️ Validation failed - check lambda target configuration")
        elif "import ray" in result:
            print("✅ Code generated (validation may have been skipped)")
        else:
            print("❓ Unexpected response format")
            
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    test_supervisor_agent()
