#!/usr/bin/env python3

import boto3
import json

def test_mcp_gateway():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test simple Ray code
    test_code = """
import ray

@ray.remote
def hello_world():
    return "Hello from Ray!"

result = ray.get(hello_world.remote())
print(result)
"""
    
    try:
        # Create event for MCP Gateway
        response = client.create_event(
            eventType='TOOL_USE',
            eventData={
                'toolUse': {
                    'toolUseId': 'test-tool-use-001',
                    'name': 'ray-validation-inline___validate_ray_code',
                    'input': {
                        'code': test_code,
                        'ray_cluster_ip': '172.31.4.12'
                    }
                }
            }
        )
        
        print("Event created successfully:")
        print(json.dumps(response, indent=2, default=str))
        
        # Get the event to see results
        event_id = response['eventId']
        result = client.get_event(eventId=event_id)
        
        print("\nEvent result:")
        print(json.dumps(result, indent=2, default=str))
        
    except Exception as e:
        print(f"Error testing MCP Gateway: {e}")

if __name__ == "__main__":
    test_mcp_gateway()
