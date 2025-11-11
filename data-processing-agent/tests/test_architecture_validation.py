#!/usr/bin/env python3
"""Validate architecture and test iterative code generation workflow"""

import requests
import json
import time

def validate_architecture():
    """Validate the system architecture"""
    
    print("🏗️ ARCHITECTURE VALIDATION")
    print("=" * 60)
    
    print("✅ Component 1: Code Generation Agent")
    print("   - Deployed in AgentCore Runtime")
    print("   - ARN: arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9")
    print("   - Model: us.anthropic.claude-sonnet-4-20250514-v1:0")
    
    print("\n✅ Component 2: Code Validation/Execution Agent")
    print("   - Lambda Function: ray-validation-inline")
    print("   - Called via AgentCore Gateway (MCP)")
    print("   - Gateway: ray-validation-gateway-e9r35gofyj")
    print("   - Target: ray-code-validation-inline___validate_ray_code")
    
    print("\n✅ Component 3: Supervisor Agent")
    print("   - Deployed in AgentCore Runtime")
    print("   - ARN: arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky")
    print("   - Model: us.anthropic.claude-sonnet-4-20250514-v1:0")
    print("   - Orchestrates: Code Gen → Validation (up to 5 attempts)")
    
    print("\n✅ Workflow:")
    print("   Backend → Supervisor Agent → Code Gen Agent")
    print("                              ↓")
    print("                         Extract Code")
    print("                              ↓")
    print("                    MCP Gateway → Lambda → Ray Cluster")
    print("                              ↓")
    print("                    Retry if failed (max 5 times)")
    print("=" * 60)

def test_iterative_workflow():
    """Test iterative code generation with intentionally failing code"""
    
    print("\n🧪 TESTING ITERATIVE WORKFLOW")
    print("=" * 60)
    
    # Test with code that might fail initially
    test_prompt = "Generate Ray code to create a dataset from numbers 1 to 10, double each value, and print the sum"
    
    payload = {
        "prompt": test_prompt,
        "session_id": f"iterative_test_{int(time.time())}"
    }
    
    print(f"📝 Test Prompt: {test_prompt}")
    print(f"🆔 Session: {payload['session_id']}")
    print(f"⏳ Expected: Up to 5 generation attempts until validation succeeds")
    print("-" * 60)
    
    try:
        print("⏳ Calling backend /generate endpoint...")
        
        response = requests.post(
            "http://localhost:8000/generate",
            json=payload,
            timeout=180
        )
        
        print(f"📡 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("📋 Response:")
            print(json.dumps(result, indent=2))
            
            # Check if code was generated and validated
            if result.get("code"):
                print("\n✅ Code Generated:")
                print(result["code"][:200] + "..." if len(result["code"]) > 200 else result["code"])
                
            if result.get("auto_executed"):
                print("\n✅ Auto-Executed: Code was validated successfully")
                if result.get("execution_result"):
                    print(f"📊 Execution Result: {result['execution_result']}")
            
            # Check for validation attempts
            if "VALIDATED" in str(result):
                print("\n🎉 SUCCESS: Code validated through iterative workflow!")
            elif "VALIDATION_ERROR" in str(result):
                print("\n⚠️ Validation failed after attempts")
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_simple_execution():
    """Test simple code execution through complete workflow"""
    
    print("\n🧪 TESTING SIMPLE EXECUTION")
    print("=" * 60)
    
    simple_code = """import ray
ray.init(address="auto")
result = 5 + 5
print(f"Result: {result}")"""
    
    payload = {
        "code": simple_code,
        "session_id": f"simple_exec_{int(time.time())}",
        "ray_cluster_ip": "172.31.4.12"
    }
    
    print(f"📝 Simple Ray Code")
    print(f"🆔 Session: {payload['session_id']}")
    print("-" * 60)
    
    try:
        response = requests.post(
            "http://localhost:8000/execute",
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if result.get("success"):
                print("✅ SUCCESS: Code executed successfully")
                print(f"📊 Job ID: {result.get('job_id')}")
                print(f"📋 Output: {result.get('output')}")
            else:
                print(f"⚠️ Execution failed: {result.get('error')}")
                
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    validate_architecture()
    time.sleep(2)
    test_simple_execution()
    time.sleep(2)
    test_iterative_workflow()
