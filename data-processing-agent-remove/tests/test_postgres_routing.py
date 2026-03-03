#!/usr/bin/env python3
"""Test that PostgreSQL requests route to EMR, not Lambda"""

import requests
import json

# Test payload with PostgreSQL tables
payload = {
    "prompt": "Show me the top 5 orders by total amount",
    "session_id": "test-postgres-routing",
    "framework": "spark",
    "selected_postgres_tables": [
        {
            "schema": "public",
            "table": "orders",
            "secret_name": "spark/postgres/aurora-e9d9d867"
        }
    ],
    "execution_platform": "lambda",  # Should be overridden to EMR
    "execution_engine": "auto"
}

print("=" * 60)
print("Testing PostgreSQL Routing")
print("=" * 60)
print(f"Payload: {json.dumps(payload, indent=2)}")
print()

response = requests.post(
    "http://localhost:8000/spark/generate",
    json=payload,
    timeout=30
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text[:500]}")
