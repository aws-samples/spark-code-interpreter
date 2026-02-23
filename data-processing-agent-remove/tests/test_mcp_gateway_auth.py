#!/usr/bin/env python3
"""Test MCP Gateway authentication and tool discovery"""

import boto3
import json
from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client

GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'

def test_mcp_gateway_auth():
    """Test MCP Gateway authentication and tool discovery"""
    
    print("🔐 Testing MCP Gateway Authentication")
    print("=" * 50)
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    print(f"✓ AWS Credentials: {credentials.access_key[:10]}...")
    print(f"✓ Gateway URL: {GATEWAY_URL}")
    
    # Create MCP client with proper headers
    headers = {}
    if credentials:
        headers["Authorization"] = f"AWS4-HMAC-SHA256 Credential={credentials.access_key}"
        if credentials.token:
            headers["X-Amz-Security-Token"] = credentials.token
    
    print(f"✓ Headers: {list(headers.keys())}")
    
    try:
        mcp_client = MCPClient(
            lambda: streamablehttp_client(GATEWAY_URL, headers=headers)
        )
        
        print("🚀 Starting MCP client...")
        mcp_client.start()
        
        print("📋 Listing available tools...")
        tools = mcp_client.list_tools_sync()
        
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test the validation tool
        if tools:
            validation_tool = None
            for tool in tools:
                if "validate" in tool.name.lower():
                    validation_tool = tool
                    break
            
            if validation_tool:
                print(f"\n🧪 Testing validation tool: {validation_tool.name}")
                
                test_code = """import ray
ray.init()
@ray.remote
def test_func():
    return "Hello Ray!"
result = ray.get(test_func.remote())
print(result)"""
                
                try:
                    result = mcp_client.call_tool_sync(
                        validation_tool.name,
                        {"code": test_code, "ray_cluster_ip": "172.31.4.12"}
                    )
                    print(f"✅ Tool call successful: {result}")
                    return True
                except Exception as e:
                    print(f"❌ Tool call failed: {e}")
                    return False
            else:
                print("⚠️ No validation tool found")
                return False
        else:
            print("❌ No tools available")
            return False
            
    except Exception as e:
        print(f"❌ MCP Gateway test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_mcp_gateway_auth()
    if success:
        print("\n🎉 MCP Gateway authentication and validation working!")
    else:
        print("\n❌ MCP Gateway authentication or validation failed!")
