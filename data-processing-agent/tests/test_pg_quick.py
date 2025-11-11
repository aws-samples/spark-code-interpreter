#!/usr/bin/env python3
"""Quick test for PostgreSQL code generation"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

payload = {
    "prompt": "find top 10 products by order total",
    "session_id": f"pg-test-{int(time.time())}",
    "framework": "spark",
    "execution_platform": "emr",
    "selected_postgres_tables": [
        {
            "connection_name": "aurora",
            "database": "postgres",
            "schema": "public",
            "table": "order_details",
            "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
            "auth_method": "user_password",
            "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
            "host": "pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com",
            "port": 5432,
            "columns": [
                {"name": "order_id", "type": "smallint", "nullable": False},
                {"name": "product_id", "type": "smallint", "nullable": False},
                {"name": "unit_price", "type": "real", "nullable": False},
                {"name": "quantity", "type": "smallint", "nullable": False},
                {"name": "discount", "type": "real", "nullable": False}
            ]
        }
    ]
}

print(f"🔵 Testing PostgreSQL code generation")
print(f"Session: {payload['session_id']}")
print(f"Table: postgres.public.order_details")
print(f"Secret: {payload['selected_postgres_tables'][0]['secret_arn']}")
print(f"Host: {payload['selected_postgres_tables'][0]['host']}")

response = requests.post(
    f"{BACKEND_URL}/spark/generate",
    json=payload,
    timeout=720
)

result = response.json()

if result.get("success"):
    spark_code = result.get("result", {}).get("spark_code", "")
    
    # Check if code uses JDBC
    has_jdbc = "jdbc" in spark_code.lower()
    has_secrets = "secretsmanager" in spark_code.lower() or "get_secret_value" in spark_code
    has_postgres = "postgresql" in spark_code.lower()
    
    print(f"\n✅ Success!")
    print(f"   JDBC connection: {'✓' if has_jdbc else '✗'}")
    print(f"   Secrets Manager: {'✓' if has_secrets else '✗'}")
    print(f"   PostgreSQL: {'✓' if has_postgres else '✗'}")
    
    if has_jdbc and has_secrets and has_postgres:
        print(f"\n🎉 Code correctly uses PostgreSQL with Secrets Manager!")
    else:
        print(f"\n⚠️  Code uses sample data instead of PostgreSQL")
        
    print(f"\nExecution: {result.get('result', {}).get('execution_result')}")
    print(f"Platform: {result.get('result', {}).get('execution_message', '')[:100]}")
else:
    print(f"\n❌ Failed: {result.get('error')}")
