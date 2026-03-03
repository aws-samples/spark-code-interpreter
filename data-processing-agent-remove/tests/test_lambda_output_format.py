import requests
import json
import time

# Test Lambda execution with sample data generation
payload = {
    "prompt": "Generate a sample DataFrame with 3 rows containing id (1-3) and color (red, green, blue) columns, then write it to S3",
    "session_id": f"test-lambda-output-{int(time.time())}",
    "execution_engine": "lambda"
}

print("🔵 Testing Lambda output formatting...")
print(f"Session ID: {payload['session_id']}")

response = requests.post(
    "http://localhost:8000/spark/generate",
    json=payload,
    timeout=180
)

result = response.json()

if result.get("success"):
    agent_result = result.get("result", {})
    
    print("\n" + "="*80)
    print("EXECUTION OUTPUT (should NOT contain table data):")
    print("="*80)
    execution_output = agent_result.get("execution_output", [])
    if execution_output:
        for line in execution_output[:20]:
            print(f"  {line}")
    else:
        print("  (empty)")
    
    print("\n" + "="*80)
    print("ACTUAL RESULTS (should contain formatted data):")
    print("="*80)
    actual_results = agent_result.get("actual_results", [])
    if actual_results:
        print(f"  Found {len(actual_results)} rows")
        for row in actual_results[:5]:
            print(f"  {row}")
    else:
        print("  (empty)")
    
    print("\n" + "="*80)
    print("VALIDATION:")
    print("="*80)
    has_table_in_execution = any('+--' in str(line) or (str(line).startswith('|') and str(line).endswith('|')) 
                                   for line in execution_output)
    has_data_in_results = len(actual_results) > 0
    
    print(f"  ❌ Table formatting in Execution Output: {has_table_in_execution}")
    print(f"  ✅ Data in Actual Results: {has_data_in_results}")
    
    if not has_table_in_execution and has_data_in_results:
        print("\n✅ SUCCESS: Lambda output is properly formatted!")
    else:
        print("\n❌ FAILED: Lambda output formatting issue detected")
else:
    print(f"\n❌ Request failed: {result.get('error')}")
