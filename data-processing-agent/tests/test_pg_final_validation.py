#!/usr/bin/env python3
"""Final validation test for PostgreSQL fix"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

payload = {
    "prompt": "find top 10 products by order total",
    "session_id": f"pg-final-{int(time.time())}",
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

print("="*80)
print("FINAL VALIDATION: PostgreSQL Code Generation Fix")
print("="*80)
print(f"\nSession: {payload['session_id']}")
print(f"Table: postgres.public.order_details")
print(f"Host: pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com")
print(f"Secret: ...aurora-e9d9d867-9Bxwrf")
print(f"\nSending request...")

response = requests.post(
    f"{BACKEND_URL}/spark/generate",
    json=payload,
    timeout=720
)

result = response.json()

print("\n" + "="*80)
print("RESULTS")
print("="*80)

if result.get("success"):
    spark_code = result.get("result", {}).get("spark_code", "")
    
    # Validation checks
    checks = {
        "JDBC PostgreSQL URL": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp" in spark_code,
        "Secrets Manager": "get_secret_value" in spark_code,
        "Correct Secret ARN": "aurora-e9d9d867-9Bxwrf" in spark_code,
        "order_details table": "order_details" in spark_code,
        "No sample data": "createDataFrame" not in spark_code and "sample_data" not in spark_code.lower(),
        "JDBC driver config": "postgresql" in spark_code.lower() and "jar" in spark_code.lower()
    }
    
    print(f"\n✅ SUCCESS - Code Generated\n")
    print("Validation Checks:")
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"  {status} {check}")
        if not passed:
            all_passed = False
    
    print(f"\nExecution Result: {result.get('result', {}).get('execution_result')}")
    print(f"Message: {result.get('result', {}).get('execution_message', '')[:150]}...")
    
    if all_passed:
        print("\n" + "="*80)
        print("🎉 ALL CHECKS PASSED - PostgreSQL integration working correctly!")
        print("="*80)
    else:
        print("\n⚠️  Some checks failed - review code generation")
        
else:
    print(f"\n❌ FAILED: {result.get('error')}")
