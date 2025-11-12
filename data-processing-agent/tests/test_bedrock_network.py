#!/usr/bin/env python3

import boto3
import json
import time
import uuid

def test_bedrock_inference():
    """Test direct Bedrock inference to check network connectivity"""
    
    # Create Bedrock client
    bedrock_client = boto3.client(
        'bedrock-runtime',
        region_name='us-east-1'
    )
    
    # Simple test prompt
    prompt = "Hello, please respond with 'Network test successful' if you can read this."
    
    # Prepare request
    request_body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 100,
        "messages": [
            {
                "role": "user",
                "content": prompt
            }
        ]
    }
    
    try:
        print("🔄 Testing Bedrock network connectivity...")
        start_time = time.time()
        
        response = bedrock_client.invoke_model(
            modelId="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
            body=json.dumps(request_body),
            contentType="application/json"
        )
        
        end_time = time.time()
        
        # Parse response
        response_body = json.loads(response['body'].read())
        content = response_body['content'][0]['text']
        
        print(f"✅ Bedrock inference successful in {end_time - start_time:.2f}s")
        print(f"📝 Response: {content}")
        return True
        
    except Exception as e:
        print(f"❌ Bedrock inference failed: {e}")
        return False

def test_agentcore_connectivity():
    """Test AgentCore service connectivity"""
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1'
    )
    
    try:
        print("🔄 Testing AgentCore connectivity...")
        start_time = time.time()
        
        # Generate proper session ID (33+ chars)
        session_id = f"network-test-{uuid.uuid4().hex}"
        
        # Minimal payload for network test
        payload = json.dumps({
            "user_request": "Hello, just testing network connectivity",
            "session_id": session_id
        })
        
        # Try to invoke the Spark supervisor agent
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=payload,
            contentType="application/json"
        )
        
        end_time = time.time()
        print(f"✅ AgentCore connection successful in {end_time - start_time:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ AgentCore connection failed: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Bedrock Network Connectivity")
    print("=" * 50)
    
    # Test 1: Direct Bedrock inference
    bedrock_ok = test_bedrock_inference()
    print()
    
    # Test 2: AgentCore connectivity
    agentcore_ok = test_agentcore_connectivity()
    print()
    
    # Summary
    print("📊 Test Results:")
    print(f"   Bedrock Runtime: {'✅ OK' if bedrock_ok else '❌ FAIL'}")
    print(f"   AgentCore: {'✅ OK' if agentcore_ok else '❌ FAIL'}")
    
    if bedrock_ok and not agentcore_ok:
        print("🔍 Issue appears to be with AgentCore service specifically")
    elif not bedrock_ok:
        print("🔍 Issue appears to be with general Bedrock connectivity")
    else:
        print("🔍 Both services appear to be working")
