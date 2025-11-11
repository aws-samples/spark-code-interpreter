#!/usr/bin/env python3
"""Direct test of PostgreSQL code generation"""

import json
import boto3

# Initialize bedrock-agentcore client
client = boto3.client('bedrock-agentcore', region_name='us-east-1')

# Supervisor agent ARN
supervisor_arn = "arn:aws:bedrock-agentcore:us-east-1:260005718447:agent-runtime/AQVQVQXQXQ/spark-supervisor-agent"

# Test payload with PostgreSQL configuration
payload = {
    "prompt": "find top 10 products by order sum",
    "session_id": "test-postgres-direct-001-12345678901",
    "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/test-postgres-direct-001/",
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
    "config": {
        "bedrock_region": "us-east-1",
        "s3_bucket": "spark-data-260005718447-us-east-1",
        "emr_application_id": "00g0oddl52n83r09",
        "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar",
        "code_gen_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:agent-runtime/AQVQVQXQXQ/code-generation-agent",
        "emr_timeout_minutes": 15,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    }
}

print("=" * 80)
print("TESTING POSTGRESQL CODE GENERATION - DIRECT AGENT CALL")
print("=" * 80)
print(f"\nPrompt: {payload['prompt']}")
print(f"PostgreSQL Table: postgres.public.order_details")
print(f"Auth Method: secrets_manager")
print(f"Secret ARN: {payload['selected_postgres_tables'][0]['secret_arn']}")
print(f"JDBC URL: {payload['selected_postgres_tables'][0]['jdbc_url']}")
print(f"JDBC Driver: {payload['config']['jdbc_driver_path']}")
print("\n" + "=" * 80)
print("Invoking agent...")
print("=" * 80)

try:
    response = client.invoke_agent_runtime(
        agentRuntimeArn=supervisor_arn,
        runtimeSessionId=payload['session_id'],
        payload=json.dumps(payload)
    )
    
    # Read response
    result_text = response['response'].read().decode('utf-8')
    result_data = json.loads(result_text)
    
    print("\n" + "=" * 80)
    print("AGENT RESPONSE")
    print("=" * 80)
    
    spark_code = result_data.get("spark_code", "")
    execution_result = result_data.get("execution_result", "")
    execution_message = result_data.get("execution_message", "")
    
    print(f"\nExecution Result: {execution_result}")
    print(f"\nExecution Message:\n{execution_message[:500]}")
    
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
    
    print(f"✓ Contains JDBC configuration: {has_jdbc}")
    print(f"✓ Fetches credentials from Secrets Manager: {has_secrets}")
    print(f"✓ Reads from PostgreSQL using spark.read.format('jdbc'): {has_postgres_read}")
    print(f"✗ Uses createDataFrame (BAD): {has_createDataFrame}")
    print(f"✗ Contains sample/synthetic data (BAD): {has_sample_data}")
    print(f"✗ Contains hardcoded data structures (BAD): {has_hardcoded_data}")
    
    print("\n" + "=" * 80)
    print("DIAGNOSIS")
    print("=" * 80)
    
    if has_postgres_read and has_secrets and not has_createDataFrame and not has_hardcoded_data:
        print("✅ SUCCESS: Code correctly reads from PostgreSQL!")
    elif has_createDataFrame or has_sample_data or has_hardcoded_data:
        print("❌ PROBLEM: Code is synthesizing data instead of reading from PostgreSQL")
        print("\nLikely causes:")
        print("1. PostgreSQL context not being passed to code generation agent")
        print("2. System prompt not enforcing PostgreSQL reads")
        print("3. Context building logic not including PostgreSQL tables")
        print("\nDebugging steps:")
        print("- Check if selected_postgres_tables is in call_code_generation_agent context")
        print("- Verify PostgreSQL context is added to full_prompt in call_code_generation_agent")
        print("- Check code generation agent system prompt has PostgreSQL instructions")
    elif not has_jdbc:
        print("❌ PROBLEM: Code missing JDBC configuration")
    elif not has_secrets:
        print("❌ PROBLEM: Code not fetching credentials from Secrets Manager")
    else:
        print("⚠️  UNCLEAR: Code structure unexpected")
    
    # Check what context was passed
    print("\n" + "=" * 80)
    print("CONTEXT CHECK")
    print("=" * 80)
    print(f"selected_postgres_tables passed: {bool(payload.get('selected_postgres_tables'))}")
    print(f"Number of PostgreSQL tables: {len(payload.get('selected_postgres_tables', []))}")
    
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
