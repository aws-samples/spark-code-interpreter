#!/usr/bin/env python3
"""Test PostgreSQL code generation with debug output"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

payload = {
    "prompt": "find top 10 products by order total",
    "session_id": f"test-pg-{int(time.time())}",
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

print(f"Session ID: {payload['session_id']}")
print(f"Calling: {BACKEND_URL}/spark/generate")
print(f"PostgreSQL tables: {len(payload['selected_postgres_tables'])}")

try:
    response = requests.post(
        f"{BACKEND_URL}/spark/generate",
        json=payload,
        timeout=720
    )
    
    print(f"\nHTTP Status: {response.status_code}")
    
    result = response.json()
    print(f"\nFull Response:")
    print(json.dumps(result, indent=2))
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
