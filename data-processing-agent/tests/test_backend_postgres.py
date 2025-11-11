#!/usr/bin/env python3
"""Test PostgreSQL via backend /spark/generate endpoint"""

import requests
import json

payload = {
    "prompt": "Find sum of order total (unit_price * quantity) grouped by product_id",
    "session_id": "test-backend-postgres",
    "framework": "spark",
    "selected_postgres_tables": [
        {
            "connection_name": "aurora",
            "database": "postgres",
            "schema": "public",
            "table": "order_details",
            "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
            "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
            "auth_method": "secrets_manager"
        }
    ]
}

print("=" * 70)
print("BACKEND POSTGRES TEST")
print("=" * 70)
print(f"Endpoint: http://localhost:8000/spark/generate")
print(f"Session: {payload['session_id']}")
print(f"Query: {payload['prompt']}")
print()

try:
    response = requests.post(
        "http://localhost:8000/spark/generate",
        json=payload,
        timeout=900
    )
    
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"\n✅ Success: {result.get('success')}")
        print(f"Platform: {result.get('execution_platform')}")
        
        if result.get('result'):
            agent_result = result['result']
            if agent_result.get('spark_code'):
                print(f"\n📝 Code Generated ({len(agent_result['spark_code'])} chars)")
                print(agent_result['spark_code'][:300] + "...")
            print(f"\nExecution: {agent_result.get('execution_result')}")
            print(f"Message: {agent_result.get('execution_message', '')[:200]}")
    else:
        print(f"\n❌ Error: {response.text[:500]}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")
