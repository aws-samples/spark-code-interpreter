"""Test Output File Fix - Verify agent generates code with /tmp/output.json"""
import boto3
import json
import time
import uuid
import sys
import os

# Add parent directory to path for config helper
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from deployment_config_helper import load_config

# Load config to get agent ARN
config = load_config()
AGENT_ARN = config.get('spark', {}).get('supervisor_arn')
REGION = boto3.Session().region_name or 'us-east-1'

if not AGENT_ARN:
    print("❌ ERROR: Agent ARN not found in config")
    print("Please ensure the agent is deployed first")
    sys.exit(1)

print(f"🧪 Testing Output File Fix")
print(f"Agent ARN: {AGENT_ARN}")
print(f"Region: {REGION}\n")

def invoke_agent(test_name, payload):
    """Invoke agent and check for output file writing in generated code"""
    print(f"\n{'='*80}")
    print(f"🧪 TEST: {test_name}")
    print(f"{'='*80}\n")
    
    print("📝 Payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    try:
        from botocore.config import Config
        client = boto3.client(
            'bedrock-agentcore',
            region_name=REGION,
            config=Config(read_timeout=600, connect_timeout=10)
        )
        
        print("🚀 Invoking agent...")
        
        response = client.invoke_agent_runtime(
            agentRuntimeArn=AGENT_ARN,
            runtimeSessionId=payload['session_id'],
            payload=json.dumps(payload)
        )
        
        if 'response' in response:
            response_body = response['response'].read().decode('utf-8')
            
            print(f"📥 Raw response (first 200 chars): {response_body[:200]}")
            
            # The response might be the code directly or a JSON object
            # Try to parse as JSON first
            try:
                parsed = json.loads(response_body)
                # If it's a dict with spark_code, use that
                if isinstance(parsed, dict) and 'spark_code' in parsed:
                    spark_code = parsed['spark_code']
                else:
                    # Otherwise, the response body itself might be the code
                    spark_code = response_body
            except json.JSONDecodeError:
                # If not JSON, treat the whole response as code
                spark_code = response_body
            
            # Now check the spark_code
            if spark_code:
                # Verify output file requirements
                checks = {
                    'has_json_import': 'import json' in spark_code,
                    'has_output_file': '/tmp/output.json' in spark_code,
                    'has_json_dump': 'json.dump(' in spark_code,
                    'has_output_dict': 'output = {' in spark_code or 'output={' in spark_code
                }
                
                print("✅ Agent responded with Spark code\n")
                print("🔍 Output File Checks:")
                for check, passed in checks.items():
                    status = "✅" if passed else "❌"
                    print(f"  {status} {check}: {passed}")
                
                all_passed = all(checks.values())
                
                if all_passed:
                    print("\n✅ ALL CHECKS PASSED - Code includes output file writing!")
                else:
                    print("\n⚠️ SOME CHECKS FAILED - Code may be missing output file requirements")
                
                print("\n📄 Generated Spark Code:")
                print("-" * 80)
                print(spark_code)
                print("-" * 80)
                
                return all_passed
            else:
                print("⚠️ No spark code found in response")
                print("Response:", response_body[:500])
                return False
        else:
            print("⚠️ No response body")
            return False
            
    except Exception as e:
        print(f"❌ Error: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

def main():
    """Run all test cases"""
    
    results = {}
    
    # Test 1: Simple Calculation
    test1_payload = {
        "prompt": "What is 7 times 10?",
        "session_id": f"test-simple-calc-{uuid.uuid4().hex}"
    }
    results['Simple Calculation'] = invoke_agent("Simple Calculation (7 × 10)", test1_payload)
    time.sleep(2)
    
    # Test 2: Small Aggregation (with data source)
    account_id = boto3.client('sts').get_caller_identity()['Account']
    s3_bucket = f"s3://spark-data-{account_id}-{REGION}"
    
    test2_payload = {
        "prompt": "Group by category and count the rows",
        "s3_input_path": f"{s3_bucket}/sample_data.csv",
        "s3_output_path": f"{s3_bucket}/output/test_aggregation",
        "session_id": f"test-aggregation-{uuid.uuid4().hex}"
    }
    results['Small Aggregation'] = invoke_agent("Small Aggregation (Group By)", test2_payload)
    time.sleep(2)
    
    # Test 3: Top N Query
    test3_payload = {
        "prompt": "Show me the top 10 rows sorted by price in descending order",
        "s3_input_path": f"{s3_bucket}/sample_data.csv",
        "s3_output_path": f"{s3_bucket}/output/test_top_n",
        "session_id": f"test-top-n-{uuid.uuid4().hex}"
    }
    results['Top N Query'] = invoke_agent("Top N Query (Top 10)", test3_payload)
    time.sleep(2)
    
    # Test 4: Large Dataset Query
    test4_payload = {
        "prompt": "Give me all rows from the dataset",
        "s3_input_path": f"{s3_bucket}/sample_data.csv",
        "s3_output_path": f"{s3_bucket}/output/test_all_rows",
        "session_id": f"test-all-rows-{uuid.uuid4().hex}"
    }
    results['Large Dataset'] = invoke_agent("Large Dataset (All Rows)", test4_payload)
    
    # Summary
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY")
    print(f"{'='*80}\n")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\n📈 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Output file fix is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {failed} test(s) failed. Review the output above for details.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
