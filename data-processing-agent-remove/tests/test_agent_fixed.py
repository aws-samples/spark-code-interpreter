#!/usr/bin/env python3
import boto3
import json

# Test the agent by invoking it
client = boto3.client('bedrock-agent-runtime', region_name='us-east-1')

agent_id = 'spark_supervisor_agent-EZPQeDGCjR'
agent_alias_id = 'DEFAULT'

try:
    response = client.invoke_agent(
        agentId=agent_id,
        agentAliasId=agent_alias_id,
        sessionId='test-session-123',
        inputText='Hello, are you working?'
    )
    
    print("✅ Agent invoked successfully!")
    print(f"Response: {response}")
    
except Exception as e:
    print(f"❌ Error invoking agent: {e}")
