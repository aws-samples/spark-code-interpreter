#!/usr/bin/env python3
"""Test PostgreSQL with full code output"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

payload = {
    "prompt": "find top 10 products by order total",
    "session_id": f"pg-full-{int(time.time())}",
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

print(f"🔵 Testing PostgreSQL on EMR")
print(f"Session: {payload['session_id']}")

response = requests.post(
    f"{BACKEND_URL}/spark/generate",
    json=payload,
    timeout=720
)

result = response.json()

if result.get("success"):
    spark_code = result.get("result", {}).get("spark_code", "")
    exec_result = result.get("result", {}).get("execution_result")
    exec_msg = result.get("result", {}).get("execution_message", "")
    
    print(f"\n✅ Execution: {exec_result}")
    print(f"📝 Message: {exec_msg[:200]}")
    
    # Check code features
    has_jdbc = "jdbc:postgresql" in spark_code
    has_secrets = "get_secret_value" in spark_code
    has_secret_arn = "aurora-e9d9d867" in spark_code
    
    print(f"\n📊 Code Analysis:")
    print(f"   JDBC PostgreSQL: {'✓' if has_jdbc else '✗'}")
    print(f"   Secrets Manager: {'✓' if has_secrets else '✗'}")
    print(f"   Correct Secret: {'✓' if has_secret_arn else '✗'}")
    
    if "Lambda" in exec_msg:
        print(f"\n⚠️  Executed on Lambda (should be EMR for PostgreSQL)")
    elif "EMR" in exec_msg:
        print(f"\n✅ Executed on EMR (correct!)")
    
    print(f"\n📄 Generated Code (first 500 chars):")
    print(spark_code[:500])
else:
    print(f"\n❌ Failed: {result.get('error')}")
