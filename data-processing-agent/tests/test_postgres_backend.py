#!/usr/bin/env python3
"""Test PostgreSQL code generation via backend API"""

import requests
import json
import time

# Backend URL (assuming it's running locally)
BACKEND_URL = "http://localhost:8000"

# Test payload
payload = {
    "prompt": "find top 10 products by order sum",
    "session_id": f"test-postgres-{int(time.time())}",
    "framework": "spark",
    "execution_platform": "emr",
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
    ]
}

print("=" * 80)
print("TESTING POSTGRESQL CODE GENERATION VIA BACKEND API")
print("=" * 80)
print(f"\nPrompt: {payload['prompt']}")
print(f"Session ID: {payload['session_id']}")
print(f"PostgreSQL Table: postgres.public.order_details")
print(f"Auth Method: secrets_manager")
print(f"Secret ARN: {payload['selected_postgres_tables'][0]['secret_arn']}")
print(f"JDBC URL: {payload['selected_postgres_tables'][0]['jdbc_url']}")
print("\n" + "=" * 80)
print("Sending request to backend...")
print("=" * 80)

try:
    response = requests.post(
        f"{BACKEND_URL}/spark/generate",
        json=payload,
        timeout=720  # 12 minutes for EMR
    )
    
    if response.status_code != 200:
        print(f"\n❌ HTTP Error {response.status_code}: {response.text}")
        exit(1)
    
    result = response.json()
    
    print("\n" + "=" * 80)
    print("BACKEND RESPONSE")
    print("=" * 80)
    
    success = result.get("success", False)
    spark_code = result.get("spark_code", "")
    execution_result = result.get("execution_result", "")
    error = result.get("error", "")
    
    print(f"\nSuccess: {success}")
    if error:
        print(f"Error: {error}")
    print(f"\nExecution Result: {execution_result}")
    
    if spark_code:
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
        has_sample_data = any(x in spark_code.lower() for x in ["sample data", "synthetic", "fake data"])
        has_hardcoded_data = "[{" in spark_code or "[(" in spark_code
        has_jdbc_driver_config = "spark.jars" in spark_code and "postgresql" in spark_code.lower()
        
        print(f"✓ Contains JDBC configuration: {has_jdbc}")
        print(f"✓ Fetches credentials from Secrets Manager: {has_secrets}")
        print(f"✓ Reads from PostgreSQL using spark.read.format('jdbc'): {has_postgres_read}")
        print(f"✓ Configures JDBC driver in spark.jars: {has_jdbc_driver_config}")
        print(f"✗ Uses createDataFrame (BAD): {has_createDataFrame}")
        print(f"✗ Contains sample/synthetic data (BAD): {has_sample_data}")
        print(f"✗ Contains hardcoded data structures (BAD): {has_hardcoded_data}")
        
        print("\n" + "=" * 80)
        print("DIAGNOSIS")
        print("=" * 80)
        
        if has_postgres_read and has_secrets and has_jdbc_driver_config and not has_createDataFrame and not has_hardcoded_data:
            print("✅ SUCCESS: Code correctly reads from PostgreSQL with all required configurations!")
        elif has_createDataFrame or has_sample_data or has_hardcoded_data:
            print("❌ PROBLEM: Code is synthesizing data instead of reading from PostgreSQL")
            print("\nThis means:")
            print("- The PostgreSQL context is not reaching the code generation agent")
            print("- OR the system prompt is not being followed")
            print("\nNext steps:")
            print("1. Check CloudWatch logs for the supervisor agent to see what context was built")
            print("2. Check if selected_postgres_tables is being passed correctly")
            print("3. Verify the JDBC driver path is in the context")
        elif not has_jdbc:
            print("❌ PROBLEM: Code missing JDBC configuration")
        elif not has_secrets:
            print("❌ PROBLEM: Code not fetching credentials from Secrets Manager")
        elif not has_jdbc_driver_config:
            print("❌ PROBLEM: Code missing JDBC driver configuration in spark.jars")
        else:
            print("⚠️  UNCLEAR: Code structure unexpected")
    else:
        print("\n❌ No Spark code generated")
    
except requests.exceptions.Timeout:
    print("\n❌ Request timed out after 12 minutes")
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
