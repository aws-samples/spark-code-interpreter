#!/usr/bin/env python3

import boto3
import json
import time
import uuid

def test_bedrock_agent_service():
    """Test standard bedrock-agent service"""
    
    try:
        print("🔄 Testing bedrock-agent service...")
        
        bedrock_agent_client = boto3.client(
            'bedrock-agent',
            region_name='us-east-1'
        )
        
        # Try to list agents to test connectivity
        response = bedrock_agent_client.list_agents(maxResults=1)
        print(f"✅ bedrock-agent service accessible")
        print(f"📝 Found {len(response.get('agentSummaries', []))} agents")
        return True
        
    except Exception as e:
        print(f"❌ bedrock-agent service failed: {e}")
        return False

def test_bedrock_agentcore_service():
    """Test bedrock-agentcore service"""
    
    try:
        print("🔄 Testing bedrock-agentcore service...")
        
        agentcore_client = boto3.client(
            'bedrock-agentcore',
            region_name='us-east-1'
        )
        
        # Generate proper session ID
        session_id = f"service-test-{uuid.uuid4().hex}"
        
        # Minimal payload
        payload = json.dumps({
            "user_request": "Hello",
            "session_id": session_id
        })
        
        # Test with timeout
        start_time = time.time()
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=payload,
            contentType="application/json"
        )
        end_time = time.time()
        
        print(f"✅ bedrock-agentcore service accessible in {end_time - start_time:.2f}s")
        return True
        
    except Exception as e:
        print(f"❌ bedrock-agentcore service failed: {e}")
        return False

def check_service_availability():
    """Check which Bedrock services are available"""
    
    session = boto3.Session()
    available_services = session.get_available_services()
    
    bedrock_services = [s for s in available_services if 'bedrock' in s]
    
    print("🔍 Available Bedrock services:")
    for service in bedrock_services:
        print(f"   - {service}")
    
    return bedrock_services

if __name__ == "__main__":
    print("🧪 Testing Bedrock Agent Services")
    print("=" * 50)
    
    # Check available services
    services = check_service_availability()
    print()
    
    # Test bedrock-agent
    agent_ok = test_bedrock_agent_service()
    print()
    
    # Test bedrock-agentcore  
    agentcore_ok = test_bedrock_agentcore_service()
    print()
    
    # Summary
    print("📊 Service Test Results:")
    print(f"   bedrock-agent: {'✅ OK' if agent_ok else '❌ FAIL'}")
    print(f"   bedrock-agentcore: {'✅ OK' if agentcore_ok else '❌ FAIL'}")
    
    if 'bedrock-agent' in services and 'bedrock-agentcore' in services:
        print("🔍 Both services are available in boto3")
    elif 'bedrock-agentcore' in services:
        print("🔍 Only bedrock-agentcore is available")
    elif 'bedrock-agent' in services:
        print("🔍 Only bedrock-agent is available")
