#!/usr/bin/env python3
"""Main orchestration script for Ray code generation and validation"""

import boto3
import json
import time

# Supervisor Agent Runtime ARN
SUPERVISOR_AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'

def generate_and_validate_ray_code(user_prompt: str, ray_cluster_ip: str = "172.31.4.12") -> str:
    """
    Main function to generate and validate Ray code
    Flow: User -> Main.py -> Supervisor AgentCore Runtime -> Code Generation Runtime + Validation Gateway
    """
    
    print("🚀 Ray Code Generation and Validation Pipeline")
    print("=" * 60)
    print(f"📝 User Prompt: {user_prompt}")
    print(f"🎯 Ray Cluster: {ray_cluster_ip}")
    print("=" * 60)
    
    # Initialize AgentCore client
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    # Create unique session ID (minimum 33 characters)
    session_id = f"main_session_{int(time.time() * 1000)}_{int(time.time() % 1000000):06d}"
    
    # Prepare payload for supervisor agent
    payload = {
        "prompt": user_prompt,
        "ray_cluster_ip": ray_cluster_ip
    }
    
    try:
        print("⏳ Calling Supervisor Agent Runtime...")
        print(f"   Session ID: {session_id}")
        print(f"   Supervisor ARN: {SUPERVISOR_AGENT_ARN}")
        
        # Call supervisor agent runtime
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=SUPERVISOR_AGENT_ARN,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        print("✅ Supervisor Agent Response Received")
        
        # Extract response content
        if "text/event-stream" in response.get("contentType", ""):
            content = []
            for line in response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        content.append(line[6:])
            result = "\n".join(content)
        else:
            events = []
            for event in response.get("response", []):
                events.append(event)
            result = json.loads(events[0].decode("utf-8")) if events else "No response"
        
        print("\n📋 Final Validated Ray Code:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        
        # Check if code contains Ray imports (validation success indicator)
        if "import ray" in result:
            print("\n🎉 SUCCESS - Ray code generated and validated!")
            print("✅ Code passed through complete pipeline:")
            print("   User → Main.py → Supervisor Runtime → Code Generation Runtime + Validation Gateway")
        else:
            print("\n⚠️ Response may not contain validated Ray code")
            
        return result
        
    except Exception as e:
        error_msg = f"Pipeline failed: {e}"
        print(f"\n❌ ERROR: {error_msg}")
        return error_msg

def main():
    """Interactive main function"""
    
    print("🔬 Ray Code Generation and Validation System")
    print("=" * 60)
    print("Architecture: User → Main.py → Supervisor Runtime → Code Gen Runtime + Validation Gateway")
    print("=" * 60)
    
    # Example prompts
    examples = [
        "Generate Ray code to create numbers 1 to 20, filter even numbers, and calculate their sum",
        "Create Ray code to process a dataset of 100 numbers, filter odd numbers, and find the maximum",
        "Write Ray code to generate 50 random numbers, filter those greater than 0.5, and count them"
    ]
    
    print("\n📝 Example prompts:")
    for i, example in enumerate(examples, 1):
        print(f"   {i}. {example}")
    
    print("\n" + "=" * 60)
    
    # Interactive input
    while True:
        try:
            user_input = input("\n💬 Enter your Ray code request (or 'quit' to exit): ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
                
            if not user_input:
                print("⚠️ Please enter a valid request")
                continue
                
            # Process the request
            result = generate_and_validate_ray_code(user_input)
            
            print(f"\n📄 Result saved to session. Ready for next request...")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    # Test with example prompt
    test_prompt = "Generate Ray code to create numbers 1 to 10, filter even numbers, and calculate their sum"
    generate_and_validate_ray_code(test_prompt)
