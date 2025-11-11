#!/usr/bin/env python3

import boto3
import json

def test_monte_carlo_pi():
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    test_request = {
        "prompt": "generate code to calculate the value of pi using monte carlo method",
        "ray_cluster_ip": "172.31.4.12"
    }
    
    print("Testing Monte Carlo Pi calculation with Ray...")
    print(f"Prompt: {test_request['prompt']}")
    print("-" * 60)
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
            payload=json.dumps(test_request)
        )
        
        if 'response' in response:
            result = response['response'].read().decode('utf-8')
            
            try:
                parsed_result = json.loads(result)
                print("FINAL GENERATED CODE:")
                print("=" * 60)
                print(parsed_result)
                print("=" * 60)
            except json.JSONDecodeError:
                print("FINAL GENERATED CODE:")
                print("=" * 60)
                print(result)
                print("=" * 60)
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_monte_carlo_pi()
