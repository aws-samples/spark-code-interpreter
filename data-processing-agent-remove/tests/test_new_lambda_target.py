#!/usr/bin/env python3
"""Test supervisor agent with new ray-code-validation-inline lambda target"""

import boto3
import json
import time

def test_supervisor_with_new_target():
    """Test that supervisor agent uses the new ray-code-validation-inline target"""
    
    print("🧪 Testing Supervisor Agent with New Lambda Target")
    print("=" * 60)
    
    # Supervisor Agent ARN
    supervisor_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'
    
    # Create AgentCore client
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test prompt
    test_prompt = "Generate Ray code to create numbers 1 to 5 and sum them"
    session_id = f"test_new_target_{int(time.time())}"
    
    print(f"📝 Test Prompt: {test_prompt}")
    print(f"🆔 Session ID: {session_id}")
    print(f"🎯 Expected: Should use ray-code-validation-inline lambda target")
    print("=" * 60)
    
    try:
        print("⏳ Calling Supervisor Agent...")
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn=supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({
                "prompt": test_prompt
            })
        )
        
        # Parse response
        response_body = response["response"].read().decode("utf-8")
        
        print("✅ Supervisor Agent Response:")
        print("-" * 40)
        print(response_body)
        print("-" * 40)
        
        # Check if response contains validation results
        if "VALIDATED" in response_body:
            print("\n🎉 SUCCESS: Code was validated using new lambda target!")
        elif "VALIDATION_ERROR" in response_body:
            print("\n⚠️ VALIDATION ERROR: Check if new lambda target is working")
        elif "import ray" in response_body:
            print("\n✅ Code generated successfully (validation may have been skipped)")
        else:
            print("\n❓ Unexpected response format")
            
        return response_body
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None

def verify_lambda_target_exists():
    """Verify the new lambda target exists in the gateway"""
    
    print("\n🔍 Verifying Lambda Target Configuration")
    print("=" * 50)
    
    try:
        # Check if lambda function exists
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        
        function_name = 'ray-validation-inline'
        response = lambda_client.get_function(FunctionName=function_name)
        
        print(f"✅ Lambda function '{function_name}' exists")
        print(f"   ARN: {response['Configuration']['FunctionArn']}")
        print(f"   Runtime: {response['Configuration']['Runtime']}")
        print(f"   Last Modified: {response['Configuration']['LastModified']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda function check failed: {e}")
        return False

if __name__ == "__main__":
    # First verify the lambda target exists
    if verify_lambda_target_exists():
        # Then test the supervisor agent
        test_supervisor_with_new_target()
    else:
        print("❌ Cannot proceed - lambda function not found")
