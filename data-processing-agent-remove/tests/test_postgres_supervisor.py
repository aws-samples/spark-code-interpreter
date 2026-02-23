#!/usr/bin/env python3
"""Test PostgreSQL query via Spark Supervisor Agent"""

import boto3
import json
import sys

# Configuration
SUPERVISOR_ARN = "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
import uuid
SESSION_ID = f"test-postgres-supervisor-{uuid.uuid4().hex[:8]}"

# PostgreSQL table configuration
postgres_table = {
    "connection_name": "aurora",
    "database": "postgres",
    "schema": "public",
    "table": "order_details",
    "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
    "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
    "auth_method": "secrets_manager"
}

# Spark configuration
spark_config = {
    "s3_bucket": "spark-data-260005718447-us-east-1",
    "emr_application_id": "00g0oddl52n83r09",
    "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar",
    "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "code_gen_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9",
    "bedrock_region": "us-east-1"
}

# Payload
payload = {
    "prompt": "Find sum of order total (unit_price * quantity) grouped by product_id",
    "session_id": SESSION_ID,
    "s3_output_path": f"s3://spark-data-260005718447-us-east-1/output/{SESSION_ID}",
    "selected_postgres_tables": [postgres_table],
    "execution_platform": "emr",
    "skip_generation": False,
    "config": spark_config
}

print("=" * 80)
print("POSTGRES SUPERVISOR AGENT TEST")
print("=" * 80)
print(f"\nSupervisor ARN: {SUPERVISOR_ARN}")
print(f"Session ID: {SESSION_ID}")
print(f"Table: {postgres_table['database']}.{postgres_table['schema']}.{postgres_table['table']}")
print(f"Query: {payload['prompt']}")
print(f"\nInvoking supervisor agent...")

try:
    client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(
            read_timeout=1200,
            connect_timeout=30
        )
    )
    
    response = client.invoke_agent_runtime(
        agentRuntimeArn=SUPERVISOR_ARN,
        qualifier="DEFAULT",
        runtimeSessionId=SESSION_ID,
        payload=json.dumps(payload)
    )
    
    response_body = response["response"].read()
    result = json.loads(response_body.decode('utf-8'))
    
    # Handle double-encoded JSON
    while isinstance(result, str):
        result = json.loads(result)
    
    print(f"\n✅ Response received ({len(response_body)} bytes)")
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
    
    if result.get('spark_code'):
        print(f"\n📝 Generated Code:")
        print(result['spark_code'][:500])
    
    sys.exit(0)
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    sys.exit(1)
