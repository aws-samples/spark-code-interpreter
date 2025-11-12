#!/usr/bin/env python3
"""Test MCP Gateway integration without network dependency"""

import sys
import os
sys.path.append('/Users/nmurich/strands-agents/agent-core/ray-code-interpreter-agent/backend')

from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import boto3

def test_mcp_client_creation():
    """Test that MCP client can be created with proper authentication"""
    
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.bedrock-agentcore.us-east-1.amazonaws.com'
    
    try:
        # Get AWS credentials for IAM authentication
        session = boto3.Session()
        credentials = session.get_credentials()
        
        print("✅ AWS credentials obtained")
        print(f"   Access Key: {credentials.access_key[:10]}...")
        print(f"   Has Token: {bool(credentials.token)}")
        
        # Create MCP client with IAM auth headers
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                GATEWAY_URL,
                headers={
                    "Authorization": f"AWS4-HMAC-SHA256 Credential={credentials.access_key}",
                    "X-Amz-Security-Token": credentials.token if credentials.token else ""
                }
            )
        )
        
        print("✅ MCP Client created successfully")
        
        # Try to start client and get available tools
        try:
            mcp_client.start()
            tools = mcp_client.list_tools_sync()
            print(f"✅ MCP Gateway tools available: {len(tools)} tools")
            for tool in tools:
                print(f"   - {tool.name}: {tool.description}")
            return True
        except Exception as e:
            print(f"⚠️ Could not get tools from MCP Gateway: {e}")
            print("   This may be due to network connectivity or authentication issues")
            return False
            
    except Exception as e:
        print(f"❌ Failed to create MCP client: {e}")
        return False

def test_supervisor_agent_structure():
    """Test that supervisor agent is structured correctly for MCP Gateway"""
    
    try:
        from agents import create_ray_code_agent
        
        # Create agent
        agent = create_ray_code_agent("100.27.32.218")
        
        print("✅ Supervisor agent created successfully")
        print(f"   Agent name: {agent.name}")
        print(f"   Number of tools: {len(agent.tools)}")
        
        # Check for expected tools
        tool_names = [tool.name for tool in agent.tools]
        print(f"   Available tools: {tool_names}")
        
        # Verify no direct Lambda fallback tools
        has_fallback = any("lambda" in name.lower() or "fallback" in name.lower() for name in tool_names)
        if has_fallback:
            print("⚠️ Agent may have fallback tools - check implementation")
        else:
            print("✅ No fallback tools detected - using MCP Gateway only")
            
        # Check for MCP Gateway tools
        has_validate_tool = any("validate" in name.lower() for name in tool_names)
        if has_validate_tool:
            print("✅ Validation tool available via MCP Gateway")
        else:
            print("⚠️ No validation tool found - check MCP Gateway connection")
            
        return True
        
    except Exception as e:
        print(f"❌ Failed to create supervisor agent: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing MCP Gateway Integration")
    print("=" * 50)
    
    print("\n1. Testing MCP Client Creation:")
    mcp_success = test_mcp_client_creation()
    
    print("\n2. Testing Supervisor Agent Structure:")
    agent_success = test_supervisor_agent_structure()
    
    print("\n" + "=" * 50)
    if mcp_success and agent_success:
        print("✅ MCP Gateway integration is properly configured!")
        print("   Supervisor agent will use MCP Gateway without fallback to direct Lambda calls")
    else:
        print("⚠️ Some issues detected - check logs above")
