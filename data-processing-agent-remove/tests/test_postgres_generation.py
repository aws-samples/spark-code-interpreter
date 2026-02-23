#!/usr/bin/env python3
"""Test PostgreSQL code generation with actual configuration"""

import json
import boto3
from backend.main import invoke_agent_runtime

# Test configuration matching your setup
test_config = {
    "prompt": "find top 10 products by order sum",
    "session_id": "test-postgres-session-001",
    "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/test-postgres-session-001/",
    "selected_postgres_tables": [
        {
            "connection_name": "aurora-test",
            "database": "postgres",
            "schema": "public",
            "table": "order_details",
            "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
            "auth_method": "secrets_manager",
            "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-967bdca7-jS7ksa",
            "host": "pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "columns": [
                {"name": "order_id", "type": "integer"},
                {"name": "product_id", "type": "integer"},
                {"name": "quantity", "type": "integer"},
                {"name": "unit_price", "type": "numeric"},
                {"name": "discount", "type": "numeric"}
            ]
        }
    ],
    "execution_platform": "emr"
}

print("=" * 80)
print("TESTING POSTGRESQL CODE GENERATION")
print("=" * 80)
print(f"\nPrompt: {test_config['prompt']}")
print(f"PostgreSQL Table: postgres.public.order_details")
print(f"Auth Method: secrets_manager")
print(f"Secret ARN: {test_config['selected_postgres_tables'][0]['secret_arn']}")
print(f"JDBC URL: {test_config['selected_postgres_tables'][0]['jdbc_url']}")
print("\n" + "=" * 80)

# Call the backend invoke function
try:
    result = invoke_agent_runtime(test_config)
    
    print("\n" + "=" * 80)
    print("AGENT RESPONSE")
    print("=" * 80)
    
    # Parse result
    if isinstance(result, str):
        result_data = json.loads(result)
    else:
        result_data = result
    
    spark_code = result_data.get("spark_code", "")
    execution_result = result_data.get("execution_result", "")
    execution_message = result_data.get("execution_message", "")
    
    print(f"\nExecution Result: {execution_result}")
    print(f"\nExecution Message:\n{execution_message}")
    
    print("\n" + "=" * 80)
    print("GENERATED SPARK CODE")
    print("=" * 80)
    print(spark_code)
    
    # Analyze the code
    print("\n" + "=" * 80)
    print("CODE ANALYSIS")
    print("=" * 80)
    
    has_jdbc = "jdbc" in spark_code.lower()
    has_secrets = "secretsmanager" in spark_code.lower() or "get_secret_value" in spark_code.lower()
    has_postgres_read = "spark.read.format" in spark_code and "jdbc" in spark_code
    has_createDataFrame = "createDataFrame" in spark_code
    has_sample_data = any(x in spark_code.lower() for x in ["sample data", "synthetic", "fake data", "[{", "[("])
    
    print(f"✓ Contains JDBC configuration: {has_jdbc}")
    print(f"✓ Fetches credentials from Secrets Manager: {has_secrets}")
    print(f"✓ Reads from PostgreSQL using spark.read.format('jdbc'): {has_postgres_read}")
    print(f"✗ Uses createDataFrame (BAD): {has_createDataFrame}")
    print(f"✗ Contains sample/synthetic data (BAD): {has_sample_data}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    
    if has_postgres_read and has_secrets and not has_createDataFrame:
        print("✅ SUCCESS: Code correctly reads from PostgreSQL!")
    elif has_createDataFrame or has_sample_data:
        print("❌ PROBLEM: Code is synthesizing data instead of reading from PostgreSQL")
        print("\nLikely causes:")
        print("1. PostgreSQL context not being passed to code generation agent")
        print("2. System prompt not enforcing PostgreSQL reads")
        print("3. Context building logic not including PostgreSQL tables")
    elif not has_jdbc:
        print("❌ PROBLEM: Code missing JDBC configuration")
    elif not has_secrets:
        print("❌ PROBLEM: Code not fetching credentials from Secrets Manager")
    else:
        print("⚠️  UNCLEAR: Code structure unexpected")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
