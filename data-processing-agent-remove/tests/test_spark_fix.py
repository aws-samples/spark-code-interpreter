#!/usr/bin/env python3

import requests
import json
import time

def test_spark_generation():
    """Test Spark code generation after boto3 import fix"""
    
    # Backend URL
    backend_url = "http://localhost:8000"
    
    # Test payload
    payload = {
        "prompt": "Create a simple Spark DataFrame with sample data and show the first 5 rows",
        "session_id": f"test-spark-{int(time.time())}",
        "framework": "spark",
        "execution_platform": "lambda"
    }
    
    print("🧪 Testing Spark code generation...")
    print(f"📤 Payload: {json.dumps(payload, indent=2)}")
    
    try:
        # Make request to Spark generate endpoint
        response = requests.post(
            f"{backend_url}/spark/generate",
            json=payload,
            timeout=60
        )
        
        print(f"📥 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Success: {result.get('success', False)}")
            
            if result.get('success'):
                agent_result = result.get('result', {})
                print(f"🎯 Generated Code Preview:")
                spark_code = agent_result.get('spark_code', 'No code generated')
                print(spark_code[:200] + "..." if len(spark_code) > 200 else spark_code)
                
                execution_result = agent_result.get('execution_result')
                if execution_result:
                    print(f"🚀 Execution Result: {execution_result}")
                    
                return True
            else:
                print(f"❌ Generation failed: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Request failed: {e}")
        return False

if __name__ == "__main__":
    success = test_spark_generation()
    exit(0 if success else 1)
