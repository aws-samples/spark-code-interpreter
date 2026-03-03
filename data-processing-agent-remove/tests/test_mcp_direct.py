#!/usr/bin/env python3

import boto3
import json
import asyncio
from mcp.client.streamable_http import streamablehttp_client
from strands.tools.mcp import MCPClient

async def test_mcp_gateway_direct():
    """Test MCP Gateway directly with proper AWS authentication"""
    
    # Gateway configuration
    GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Get AWS credentials
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create proper AWS signature headers
    headers = {}
    if credentials:
        headers["Authorization"] = f"AWS4-HMAC-SHA256 Credential={credentials.access_key}"
        if credentials.token:
            headers["X-Amz-Security-Token"] = credentials.token
    
    print("🔧 Testing MCP Gateway authentication and tool routing...")
    print(f"Gateway URL: {GATEWAY_URL}")
    print(f"Using AWS credentials: {credentials.access_key[:10]}...")
    
    try:
        # Create MCP client
        mcp_client = MCPClient(
            lambda: streamablehttp_client(
                GATEWAY_URL,
                headers=headers
            )
        )
        
        # Start client
        await mcp_client.start()
        print("✅ MCP client connected successfully")
        
        # List available tools
        tools = await mcp_client.list_tools()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        # Test the validate_ray_code tool
        test_code = """
import ray

@ray.remote
def factorial(n):
    if n <= 1:
        return 1
    return n * factorial.remote(n - 1)

result = ray.get(factorial.remote(5))
print(f"Factorial of 5: {result}")
"""
        
        print(f"\n🧪 Testing ray-validation-inline___validate_ray_code tool...")
        print(f"Code to validate: {len(test_code)} characters")
        
        # Call the tool
        result = await mcp_client.call_tool(
            "ray-validation-inline___validate_ray_code",
            {
                "code": test_code,
                "ray_cluster_ip": "172.31.4.12"
            }
        )
        
        print("✅ Tool call successful!")
        print(f"Result: {result}")
        
        # Check if result indicates success
        result_str = str(result).lower()
        if "succeeded" in result_str or "success" in result_str:
            print("✅ SUCCESS: Ray code validation succeeded")
        elif "error" in result_str or "failed" in result_str:
            print("❌ WARNING: Ray code validation failed")
        else:
            print("ℹ️  INFO: Validation result unclear")
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Run the async test"""
    asyncio.run(test_mcp_gateway_direct())

if __name__ == "__main__":
    main()
