#!/usr/bin/env python3

import boto3
import json
import tempfile
import os

def test_supervisor_agent_mcp():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Test request that should trigger MCP Gateway validation
    test_request = {
        "user_request": "Create a Ray remote function that calculates the square of a number. The function should take an integer as input and return its square. Then demonstrate calling this function with the number 5.",
        "max_iterations": 3
    }
    
    # Create temporary file for response
    with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
        temp_filename = temp_file.name
    
    try:
        # Invoke supervisor agent
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
            payload=json.dumps(test_request)
        )
        
        print("Supervisor agent invoked successfully:")
        print(f"Status Code: {response['statusCode']}")
        print(f"Session ID: {response['runtimeSessionId']}")
        
        # Read the streaming response
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            print("\nSupervisor agent response:")
            print(result)
            
            # Try to parse as JSON for better formatting
            try:
                parsed_result = json.loads(result)
                print("\nParsed response:")
                print(json.dumps(parsed_result, indent=2))
            except json.JSONDecodeError:
                print("Response is not valid JSON")
            
    except Exception as e:
        print(f"Error invoking supervisor agent: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(temp_filename):
            os.unlink(temp_filename)

if __name__ == "__main__":
    test_supervisor_agent_mcp()
