#!/usr/bin/env python3
import requests
import json
import time

url = "http://localhost:8000/spark/generate"
payload = {
    "prompt": "Generate a sample dataframe with 10 rows and 5 columns and print the dataframe",
    "session_id": "test-sample-df-123",
    "s3_input_path": None,
    "execution_platform": "lambda"
}

print("🚀 Testing Spark Code Generation Workflow")
print(f"Prompt: {payload['prompt']}")
print(f"Execution Platform: {payload['execution_platform']}")
print("\n" + "="*80 + "\n")

start = time.time()
try:
    response = requests.post(url, json=payload, timeout=600)  # 10 minutes to match backend
    elapsed = time.time() - start
    
    print(f"⏱️  Response time: {elapsed:.2f}s")
    print(f"Status: {response.status_code}\n")
    
    if response.status_code == 200:
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ Error: {data.get('error')}")
            exit(1)
        
        result = data.get('result')
        
        # Parse nested JSON - multiple levels
        for _ in range(3):  # Try up to 3 levels of unwrapping
            if isinstance(result, str):
                try:
                    result = json.loads(result)
                except json.JSONDecodeError:
                    break
            elif isinstance(result, dict) and 'result' in result:
                result = result['result']
            else:
                break
        
        # If still a string, try to extract JSON from markdown
        if isinstance(result, str):
            import re
            json_match = re.search(r'```json\s*\n(.*?)\n```', result, re.DOTALL)
            if json_match:
                try:
                    result = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
        
        print(f"DEBUG: Final result type: {type(result)}")
        if isinstance(result, str):
            print(f"DEBUG: Result is still string, length: {len(result)}")
            print(f"DEBUG: First 500 chars: {result[:500]}")
        elif isinstance(result, dict):
            print(f"DEBUG: Result keys: {list(result.keys())}")
        
        # Check for error in result
        if isinstance(result, dict) and 'error' in result:
            print("\n" + "="*80)
            print("❌ AGENT ERROR:")
            print("="*80)
            print(f"Error: {result.get('error')}")
            print(f"Error Type: {result.get('error_type')}")
            exit(1)
        
        # Extract code and execution result
        if isinstance(result, dict):
            validated_code = result.get('validated_code', '')
            execution_result = result.get('execution_result', {})
            data_result = result.get('data', [])
            s3_output = result.get('s3_output_path', '')
            
            print("="*80)
            print("📝 GENERATED CODE:")
            print("="*80)
            print(validated_code)
            print("\n" + "="*80)
            print("🎯 EXECUTION RESULT:")
            print("="*80)
            print(json.dumps(execution_result, indent=2))
            
            if data_result:
                print("\n" + "="*80)
                print("📊 DATA (first 5 rows):")
                print("="*80)
                if isinstance(data_result, list):
                    print(json.dumps(data_result[:5], indent=2))
                else:
                    print(json.dumps(data_result, indent=2))
            
            if s3_output:
                print(f"\n📁 S3 Output: {s3_output}")
            
            print("\n" + "="*80)
            print("✅ Workflow completed successfully!")
        else:
            print(f"⚠️  Unexpected result format: {type(result)}")
            print(json.dumps(result, indent=2))
    else:
        print(f"❌ HTTP Error: {response.status_code}")
        print(response.text)
        
except requests.exceptions.Timeout:
    print(f"⏱️  TIMEOUT after {time.time() - start:.2f}s")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
