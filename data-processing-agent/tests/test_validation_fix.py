"""Test validation failure handling and EMR preference for Glue tables"""

import boto3
import json
import time
import uuid

def test_validation_failure():
    """Test that validation failures are properly caught and not executed"""
    print("\n=== Testing Validation Failure Handling ===")
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Generate invalid code (missing SparkSession)
    payload = {
        "prompt": "Generate code that doesn't create a SparkSession",
        "session_id": f"test-validation-{uuid.uuid4().hex}",
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/test-output/",
        "execution_platform": "lambda"
    }
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
        runtimeSessionId=payload['session_id'],
        payload=json.dumps(payload)
    )
    
    result = json.loads(response['response'].read().decode('utf-8'))
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Check if validation failure was caught
    if result.get('execution_result') == 'failed':
        print("✅ Validation failure properly caught")
        return True
    else:
        print("❌ Validation failure not caught - code was executed")
        return False

def test_emr_preference():
    """Test that EMR is preferred when Glue tables are selected"""
    print("\n=== Testing EMR Preference for Glue Tables ===")
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Request with Glue table should use EMR even if lambda is specified
    payload = {
        "prompt": "Count rows in the table",
        "session_id": f"test-emr-pref-{uuid.uuid4().hex}",
        "selected_tables": ["northwind.customers_iceberg"],
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/test-output/",
        "execution_platform": "lambda"  # Should be overridden to EMR
    }
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
        runtimeSessionId=payload['session_id'],
        payload=json.dumps(payload)
    )
    
    result = json.loads(response['response'].read().decode('utf-8'))
    print(f"Result: {json.dumps(result, indent=2)}")
    
    # Check execution message for platform used
    exec_msg = result.get('execution_message', '')
    if 'emr' in exec_msg.lower() or 'EMR' in exec_msg:
        print("✅ EMR was used for Glue table query")
        return True
    else:
        print("❌ EMR preference not applied")
        return False

def test_spark_system_prompt():
    """Test that Spark-specific system prompt is being used"""
    print("\n=== Testing Spark System Prompt ===")
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    # Request that requires Glue catalog configuration
    payload = {
        "prompt": "Query the customers table and show first 5 rows",
        "session_id": f"test-prompt-{uuid.uuid4().hex}",
        "selected_tables": ["northwind.customers_iceberg"],
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/test-output/",
        "execution_platform": "emr"
    }
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
        runtimeSessionId=payload['session_id'],
        payload=json.dumps(payload)
    )
    
    result = json.loads(response['response'].read().decode('utf-8'))
    print(f"Generated code preview:\n{result.get('spark_code', '')[:500]}...")
    
    # Check if generated code has Glue catalog configuration
    code = result.get('spark_code', '')
    has_warehouse_dir = 'spark.sql.warehouse.dir' in code
    has_factory_class = 'AWSGlueDataCatalogHiveClientFactory' in code
    has_hive_support = 'enableHiveSupport()' in code
    
    if has_warehouse_dir and has_factory_class and has_hive_support:
        print("✅ Spark system prompt properly configured Glue catalog")
        return True
    else:
        print(f"❌ Missing Glue configuration:")
        print(f"  - warehouse.dir: {has_warehouse_dir}")
        print(f"  - factory.class: {has_factory_class}")
        print(f"  - enableHiveSupport: {has_hive_support}")
        return False

if __name__ == "__main__":
    print("Testing Spark Supervisor Agent Fixes")
    print("=" * 50)
    
    results = []
    
    # Test 1: Validation failure handling
    try:
        results.append(("Validation Failure", test_validation_failure()))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results.append(("Validation Failure", False))
    
    time.sleep(2)
    
    # Test 2: EMR preference
    try:
        results.append(("EMR Preference", test_emr_preference()))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results.append(("EMR Preference", False))
    
    time.sleep(2)
    
    # Test 3: Spark system prompt
    try:
        results.append(("Spark System Prompt", test_spark_system_prompt()))
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        results.append(("Spark System Prompt", False))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\nTotal: {passed}/{total} tests passed")
