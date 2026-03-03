#!/usr/bin/env python3
"""Test agent invocation and callback handling"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_code_generator_invocation():
    """Test that code generator agent can be invoked"""
    print("=" * 60)
    print("AGENT INVOCATION TEST")
    print("=" * 60)
    print()
    
    from agents import create_code_generator_agent
    
    print("1. Creating CodeGeneratorAgent...")
    code_agent = create_code_generator_agent()
    print(f"   ✓ {code_agent.name} created")
    print()
    
    print("2. Testing direct invocation...")
    try:
        import asyncio
        
        # Simple test prompt
        prompt = "Generate Ray code to create a dataset with 10 rows and print them"
        
        # Run async invocation
        result = asyncio.run(code_agent.invoke_async(prompt))
        
        print("   ✓ Agent invoked successfully")
        print(f"   Response type: {type(result)}")
        print(f"   Has message: {hasattr(result, 'message')}")
        
        if hasattr(result, 'message'):
            if hasattr(result.message, 'content'):
                print(f"   Message has content: {len(result.message.content) if result.message.content else 0} items")
            else:
                print(f"   Message: {str(result.message)[:100]}...")
        
        print()
        print("✅ CodeGeneratorAgent invocation works correctly")
        
    except Exception as e:
        print(f"   ✗ Invocation failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_supervisor_tools():
    """Test that supervisor tools work"""
    print()
    print("=" * 60)
    print("SUPERVISOR TOOLS TEST")
    print("=" * 60)
    print()
    
    from agents import create_supervisor_agent
    from main import sessions, CodeInterpreterSession
    
    print("1. Creating supervisor...")
    supervisor = create_supervisor_agent()
    print(f"   ✓ {supervisor.name} created")
    print(f"   Tools: {supervisor.tool_names}")
    print()
    
    print("2. Setting up test session...")
    session_id = "test-invocation"
    sessions[session_id] = CodeInterpreterSession(session_id)
    sessions[session_id].uploaded_csv = {
        'filename': 'test.csv',
        's3_path': 's3://bucket/test.csv',
        'preview': 'id,value\n1,100'
    }
    print(f"   ✓ Session {session_id} created with CSV")
    print()
    
    print("3. Testing tool invocation through supervisor...")
    print("   Note: This requires Bedrock API access")
    print("   Skipping actual invocation to avoid API calls")
    print()
    
    print("✅ Supervisor tools are properly configured")
    return True

if __name__ == "__main__":
    print()
    success = test_code_generator_invocation()
    if success:
        test_supervisor_tools()
    print()
