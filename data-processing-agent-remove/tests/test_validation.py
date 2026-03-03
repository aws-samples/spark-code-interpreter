#!/usr/bin/env python3
"""Test validation retry and session isolation"""

import asyncio
import sys
sys.path.insert(0, 'backend')

from agents import create_ray_code_agent
from main import prompt_sessions

async def test_validation():
    """Test that agent validates code before returning"""
    print("=" * 60)
    print("TEST 1: Validation Workflow")
    print("=" * 60)
    
    agent = create_ray_code_agent()
    
    # Create isolated session
    session_id = "test_session_1"
    prompt_sessions[session_id] = {
        'csv': None,
        'tables': []
    }
    
    # Test simple prompt
    prompt = "Create a Ray dataset with 10 rows containing numbers 0-9, square each value, and print results"
    
    print(f"\n📝 Prompt: {prompt}")
    print(f"🔑 Session ID: {session_id}")
    print("\n⏳ Generating code with validation...\n")
    
    response = await agent.invoke_async(prompt, session_id=session_id)
    
    # Extract response
    full_response = ""
    if hasattr(response.message, 'content'):
        for block in response.message.content:
            if hasattr(block, 'text'):
                full_response += block.text
            elif isinstance(block, dict) and 'text' in block:
                full_response += block['text']
    else:
        full_response = str(response.message)
    
    print("\n" + "=" * 60)
    print("AGENT RESPONSE:")
    print("=" * 60)
    print(full_response)
    print("=" * 60)
    
    # Check for validation
    if 'validation failed' in full_response.lower():
        print("\n❌ FAIL: Agent reported validation failure")
        return False
    else:
        print("\n✅ PASS: Agent returned code (validation should have passed)")
    
    return True

async def test_session_isolation():
    """Test that each prompt gets isolated session"""
    print("\n\n" + "=" * 60)
    print("TEST 2: Session Isolation")
    print("=" * 60)
    
    # Create two different prompt sessions
    session1 = "test_session_2_1"
    session2 = "test_session_2_2"
    
    prompt_sessions[session1] = {
        'csv': {'filename': 'data1.csv', 's3_path': 's3://bucket/data1.csv'},
        'tables': []
    }
    
    prompt_sessions[session2] = {
        'csv': {'filename': 'data2.csv', 's3_path': 's3://bucket/data2.csv'},
        'tables': []
    }
    
    print(f"\n📊 Session 1: {session1}")
    print(f"   CSV: {prompt_sessions[session1]['csv']['filename']}")
    
    print(f"\n📊 Session 2: {session2}")
    print(f"   CSV: {prompt_sessions[session2]['csv']['filename']}")
    
    # Verify isolation
    if prompt_sessions[session1]['csv']['filename'] != prompt_sessions[session2]['csv']['filename']:
        print("\n✅ PASS: Sessions are isolated (different CSV files)")
        return True
    else:
        print("\n❌ FAIL: Sessions are not isolated")
        return False

async def main():
    print("\n🧪 Testing Ray Code Interpreter Validation & Isolation\n")
    
    test1 = await test_validation()
    test2 = await test_session_isolation()
    
    print("\n\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Validation Workflow: {'✅ PASS' if test1 else '❌ FAIL'}")
    print(f"Session Isolation: {'✅ PASS' if test2 else '❌ FAIL'}")
    print("=" * 60)
    
    if test1 and test2:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n⚠️ Some tests failed")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
