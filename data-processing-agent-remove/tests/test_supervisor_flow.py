#!/usr/bin/env python3
"""Test complete supervisor agent flow via /execute endpoint"""

import requests
import json
import time

def test_supervisor_flow():
    """Test complete flow: Backend -> Supervisor Agent -> MCP Gateway -> Lambda"""
    
    print("🔄 Testing Complete Supervisor Agent Flow")
    print("=" * 60)
    
    # Sample Ray code
    sample_code = """import ray
ray.init(address="auto")

# Create dataset and process
numbers = [1, 2, 3, 4, 5]
ds = ray.data.from_items(numbers)
doubled = ds.map(lambda x: x * 2)
total = doubled.sum()
print(f"Doubled sum: {total}")
"""
    
    payload = {
        "code": sample_code,
        "session_id": f"supervisor_flow_{int(time.time())}"
    }
    
    print("📋 Flow Architecture:")
    print("   Backend (/execute)")
    print("   ↓")
    print("   Supervisor Agent (arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky)")
    print("   ↓")
    print("   MCP Gateway (ray-validation-gateway-e9r35gofyj)")
    print("   ↓")
    print("   Lambda Target (ray-code-validation-inline___validate_ray_code)")
    print("   ↓")
    print("   Ray Cluster (172.31.4.12)")
    
    print(f"\n📝 Test Code:")
    print(sample_code)
    print(f"🆔 Session: {payload['session_id']}")
    print("-" * 60)
    
    try:
        print("⏳ Calling /execute endpoint...")
        
        response = requests.post(
            "http://localhost:8000/execute",
            json=payload,
            timeout=180  # Longer timeout for full flow
        )
        
        print(f"📡 HTTP Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("📋 Full Response:")
            print(json.dumps(result, indent=2))
            
            # Analyze response
            if result.get("success"):
                print("\n🎉 SUCCESS: Complete flow working!")
                print("✅ Supervisor Agent -> MCP Gateway -> Lambda -> Ray Cluster")
                
                if result.get("output"):
                    print(f"📊 Ray Execution Output: {result['output']}")
                if result.get("job_id"):
                    print(f"🔧 Ray Job ID: {result['job_id']}")
                    
            else:
                error = result.get("error", "Unknown error")
                print(f"\n⚠️ Flow Error: {error}")
                
                # Analyze error type
                if "VALIDATION_ERROR" in error:
                    print("🔍 Issue: MCP Gateway or Lambda validation failed")
                elif "AGENT_ERROR" in error:
                    print("🔍 Issue: Supervisor agent or code generation failed")
                elif "timeout" in error.lower():
                    print("🔍 Issue: Request timeout (agent may be processing)")
                else:
                    print("🔍 Issue: Unknown error in flow")
                    
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.Timeout:
        print("⏰ Request timed out - supervisor agent may still be processing")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_supervisor_flow()
