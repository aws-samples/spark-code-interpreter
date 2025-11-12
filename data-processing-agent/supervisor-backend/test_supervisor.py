"""Test supervisor agent with sample prompt"""

import boto3
import json
import uuid

SUPERVISOR_AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'

def test_supervisor_agent(prompt: str):
    """Test supervisor agent with a prompt"""
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    session_id = f"test-session-{uuid.uuid4().hex}"
    
    print(f"🧪 Testing Supervisor Agent")
    print(f"📝 Prompt: {prompt}")
    print(f"🔑 Session ID: {session_id}")
    print("=" * 60)
    
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SUPERVISOR_AGENT_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps({"prompt": prompt})
        )
        
        response_body = response["response"].read()
        if response_body:
            try:
                result = json.loads(response_body.decode("utf-8"))
                result_str = str(result) if not isinstance(result, str) else result
            except json.JSONDecodeError:
                result_str = response_body.decode("utf-8")
        else:
            result_str = "No response"
        
        print("\n✅ Response:")
        print("=" * 60)
        print(result_str)
        print("=" * 60)
        
        return result_str
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return str(e)

if __name__ == "__main__":
    # Test with simple prompt
    test_prompt = "Generate Ray code to create numbers 1 to 10, filter even numbers, and calculate their sum"
    test_supervisor_agent(test_prompt)
