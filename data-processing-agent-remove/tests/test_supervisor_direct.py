#!/usr/bin/env python3
"""Test supervisor agent directly calling AgentCore Gateway"""

import boto3
import json
import time

def test_supervisor_direct():
    """Test supervisor agent with simple Ray code"""
    
    print("🧪 Testing Supervisor Agent -> AgentCore Gateway -> Lambda")
    print("=" * 60)
    
    supervisor_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'
    
    # Simple Ray code
    test_code = """import ray
ray.init(address="auto")
result = 1 + 1
print(f"Result: {result}")"""
    
    session_id = f"supervisor_test_{int(time.time())}_{int(time.time() % 1000000):06d}"
    
    print(f"📝 Test Code: {test_code.replace(chr(10), ' | ')}")
    print(f"🆔 Session: {session_id}")
    print(f"🎯 Supervisor ARN: {supervisor_arn}")
    print("-" * 60)
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    try:
        print("⏳ Invoking supervisor agent...")
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn=supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({
                "prompt": f"Validate this Ray code: {test_code}"
            })
        )
        
        result = response["response"].read().decode("utf-8")
        
        print("📋 Supervisor Response:")
        print(result)
        print("-" * 60)
        
        # Analyze response
        if "VALIDATED" in result:
            print("✅ SUCCESS: Code validated through complete chain!")
        elif "VALIDATION_ERROR" in result:
            print("⚠️ Validation error detected")
            if "MCP Gateway internal error" in result:
                print("🔍 Issue: MCP Gateway returning internal error")
            elif "Invalid JSON response" in result:
                print("🔍 Issue: Lambda response format problem")
        elif "An internal error occurred" in result:
            print("❌ MCP Gateway internal error")
        else:
            print("❓ Unexpected response format")
            
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    test_supervisor_direct()
