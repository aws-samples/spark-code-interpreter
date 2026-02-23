#!/usr/bin/env python3
"""Test AgentCore Gateway using MCP Client from sample notebook"""

from strands.tools.mcp import MCPClient
from mcp.client.streamable_http import streamablehttp_client
import boto3
import asyncio

async def test_mcp_client_direct():
    """Test MCP Gateway directly using MCPClient"""
    
    # Sample Ray code
    ray_code = """import ray

ds = ray.data.range(1, 21)
filtered_ds = ds.filter(lambda x: x["id"] % 2 == 0)
result = filtered_ds.sum("id")
print(f"Sum of even numbers 1-20: {result}")"""
    
    print("🧪 Testing AgentCore Gateway with MCP Client")
    print("=" * 60)
    print("📝 Ray Code to Validate:")
    print(ray_code)
    print("=" * 60)
    
    # Gateway URL
    gateway_url = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'
    
    # Get AWS credentials for IAM authentication
    session = boto3.Session()
    credentials = session.get_credentials()
    
    # Create MCP client with IAM auth headers
    mcp_client = MCPClient(
        lambda: streamablehttp_client(
            gateway_url,
            headers={
                "Authorization": f"AWS4-HMAC-SHA256 Credential={credentials.access_key}",
                "X-Amz-Security-Token": credentials.token if credentials.token else ""
            }
        )
    )
    
    try:
        print("🚀 Starting MCP client...")
        mcp_client.start()
        
        print("📋 Listing available tools...")
        tools = mcp_client.list_tools_sync()
        print(f"✅ Found {len(tools)} tools:")
        for tool in tools:
            print(f"   - {tool.name}: {tool.description}")
        
        print("\n🔧 Calling validation tool...")
        # Find the validation tool
        validation_tool = None
        for tool in tools:
            if "validate_ray_code" in tool.name:
                validation_tool = tool
                break
        
        if validation_tool:
            print(f"   Using tool: {validation_tool.name}")
            
            # Call the tool
            result = mcp_client.call_tool_sync(
                validation_tool.name,
                {
                    "code": ray_code,
                    "ray_cluster_ip": "100.27.32.218"
                }
            )
            
            print("✅ Validation Result:")
            print("=" * 40)
            print(result)
            
            # Check if successful
            if hasattr(result, 'content') and result.content:
                content_text = ""
                for block in result.content:
                    if hasattr(block, 'text'):
                        content_text += block.text
                
                if "success" in content_text.lower() or "job" in content_text.lower():
                    print("\n🎉 SUCCESS - Ray code validated via MCP Gateway!")
                else:
                    print(f"\n❌ VALIDATION FAILED: {content_text}")
            else:
                print(f"\n❓ Unexpected result format: {result}")
        else:
            print("❌ No validation tool found")
            
    except Exception as e:
        print(f"❌ MCP client test failed: {e}")
    finally:
        try:
            mcp_client.stop()
        except:
            pass

def main():
    """Run the async test"""
    asyncio.run(test_mcp_client_direct())

if __name__ == "__main__":
    main()
