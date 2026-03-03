#!/usr/bin/env python3
"""Verify supervisor agent is configured to use new lambda target"""

def verify_supervisor_configuration():
    """Check supervisor agent configuration for new lambda target"""
    
    print("🔍 Verifying Supervisor Agent Configuration")
    print("=" * 50)
    
    # Read supervisor agent file
    supervisor_file = "supervisor-backend/supervisor_agents.py"
    
    try:
        with open(supervisor_file, 'r') as f:
            content = f.read()
        
        print("✅ Supervisor agent file loaded")
        
        # Check for new lambda target name
        if "ray-code-validation-inline___validate_ray_code" in content:
            print("✅ Using NEW lambda target: ray-code-validation-inline")
        elif "ray-validation-inline___validate_ray_code" in content:
            print("⚠️ Using OLD lambda target: ray-validation-inline")
            print("   Should be: ray-code-validation-inline")
        else:
            print("❌ No lambda target found in configuration")
        
        # Check MCP Gateway URL
        if "ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com" in content:
            print("✅ MCP Gateway URL configured correctly")
        else:
            print("❌ MCP Gateway URL not found")
        
        # Check tool name pattern
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if '"name":' in line and 'validate_ray_code' in line:
                print(f"📋 Tool name configuration (line {i+1}):")
                print(f"   {line.strip()}")
                
        print("\n🎯 Expected tool name format:")
        print("   ray-code-validation-inline___validate_ray_code")
        
        return True
        
    except FileNotFoundError:
        print(f"❌ File not found: {supervisor_file}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False

def show_deployment_commands():
    """Show commands to redeploy supervisor agent"""
    
    print("\n🚀 To Deploy Updated Supervisor Agent:")
    print("=" * 40)
    print("cd supervisor-backend")
    print("python agent_deployment.py")
    print("\nOr use the deployment script:")
    print("python deploy_mcp_supervisor.py")

if __name__ == "__main__":
    if verify_supervisor_configuration():
        show_deployment_commands()
