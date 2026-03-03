import requests
import json
import time

# Test EMR execution with sample data generation
payload = {
    "prompt": "Generate a sample DataFrame with 5 rows containing id (1-5) and name (Alice, Bob, Charlie, David, Eve) columns, then write it to S3",
    "session_id": f"test-emr-output-{int(time.time())}",
    "execution_engine": "emr"
}

print("🔵 Testing EMR output formatting...")
print(f"Session ID: {payload['session_id']}")

response = requests.post(
    "http://localhost:8000/spark/generate",
    json=payload,
    timeout=600
)

result = response.json()

print("\n" + "="*80)
print("RESPONSE STRUCTURE:")
print("="*80)
print(json.dumps(result, indent=2, default=str))

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
        print("\n✅ SUCCESS: Output is properly formatted!")
    else:
        print("\n❌ FAILED: Output formatting issue detected")
else:
    print(f"\n❌ Request failed: {result.get('error')}")
