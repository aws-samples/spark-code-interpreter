#!/usr/bin/env python3
"""
Verify the correct architecture:
- main.py uses AgentCore runtime directly (no agents.py)
- AgentCore runtime replaces agents.py functionality
"""
import os
import sys

def verify_main_py():
    """Verify main.py uses AgentCore runtime directly"""
    with open('backend/main.py', 'r') as f:
        content = f.read()
    
    # Should have
    good_checks = [
        ('agentcore_client = boto3.client', 'AgentCore client'),
        ('agentcore_client.invoke_agent_runtime', 'direct AgentCore calls'),
        ('bedrock-agentcore', 'reports AgentCore'),
        ('AGENT_ARN', 'AgentCore ARN configuration')
    ]
    
    # Should NOT have
    bad_checks = [
        ('from agents import', 'agents.py import'),
        ('strands-agents', 'strands-agents reference'),
        ('ray_code_agent.invoke_async', 'strands-agents calls')
    ]
    
    print("🔍 Verifying main.py...")
    
    for check, desc in good_checks:
        if check in content:
            print(f"✅ {desc}")
        else:
            print(f"❌ Missing: {desc}")
            return False
    
    for check, desc in bad_checks:
        if check in content:
            print(f"❌ Found: {desc} (should not be present)")
            return False
        else:
            print(f"✅ Correctly avoids: {desc}")
    
    return True

def verify_no_agents_dependency():
    """Verify agents.py is not used"""
    print("\n🔍 Verifying no agents.py dependency...")
    
    # Check if agents.py exists but is not imported
    if os.path.exists('backend/agents.py'):
        print("ℹ️ agents.py exists but should not be used")
    
    # Verify main.py doesn't import agents
    with open('backend/main.py', 'r') as f:
        content = f.read()
    
    if 'from agents import' not in content and 'import agents' not in content:
        print("✅ main.py does not import agents.py")
        return True
    else:
        print("❌ main.py still imports agents.py")
        return False

def main():
    print("🏗️ Architecture Verification - AgentCore Direct")
    print("=" * 50)
    
    main_ok = verify_main_py()
    no_agents_ok = verify_no_agents_dependency()
    
    print(f"\n📊 Results:")
    print(f"   main.py: {'✅ CORRECT' if main_ok else '❌ INCORRECT'}")
    print(f"   no agents.py dependency: {'✅ CORRECT' if no_agents_ok else '❌ INCORRECT'}")
    
    if main_ok and no_agents_ok:
        print("\n🎉 Architecture is CORRECT!")
        print("   ✓ main.py uses AgentCore runtime directly")
        print("   ✓ No dependency on agents.py")
        print("   ✓ AgentCore runtime replaces agents.py functionality")
        return True
    else:
        print("\n💥 Architecture has ISSUES!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
