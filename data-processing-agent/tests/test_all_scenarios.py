#!/usr/bin/env python3
"""Test all three scenarios: Glue, PostgreSQL, CSV"""

import requests
import json
import time

def test_scenario(name, payload):
    print(f"\n{'='*70}")
    print(f"TEST: {name}")
    print(f"{'='*70}")
    
    try:
        response = requests.post(
            "http://localhost:8000/spark/generate",
            json=payload,
            timeout=900
        )
        
        if response.status_code == 200:
            result = response.json()
            success = result.get('success', False)
            platform = result.get('execution_platform', 'unknown')
            
            print(f"✅ Status: {response.status_code}")
            print(f"✅ Success: {success}")
            print(f"✅ Platform: {platform}")
            
            if result.get('result'):
                agent_result = result['result']
                exec_result = agent_result.get('execution_result', 'unknown')
                print(f"✅ Execution: {exec_result}")
                
                if agent_result.get('spark_code'):
                    print(f"✅ Code generated: {len(agent_result['spark_code'])} chars")
            
            return success
        else:
            print(f"❌ HTTP {response.status_code}: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test 1: PostgreSQL
postgres_payload = {
    "prompt": "Show top 5 products by order count",
    "session_id": f"test-postgres-{int(time.time())}",
    "framework": "spark",
    "selected_postgres_tables": [{
        "connection_name": "aurora",
        "database": "postgres",
        "schema": "public",
        "table": "order_details",
        "jdbc_url": "jdbc:postgresql://pg-database.cluster-ro-c8lobwtocefp.us-east-1.rds.amazonaws.com:5432/postgres",
        "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
        "auth_method": "secrets_manager"
    }]
}

# Test 2: Glue table
glue_payload = {
    "prompt": "Show top 5 rows from the table",
    "session_id": f"test-glue-{int(time.time())}",
    "framework": "spark",
    "selected_tables": [
        {"database": "default", "table": "nyc_taxi_data"}
    ]
}

# Test 3: CSV file
csv_payload = {
    "prompt": "Show summary statistics",
    "session_id": f"test-csv-{int(time.time())}",
    "framework": "spark",
    "s3_input_path": "s3://spark-data-260005718447-us-east-1/sample.csv"
}

print("="*70)
print("TESTING ALL SCENARIOS")
print("="*70)

results = {}
results['PostgreSQL'] = test_scenario("PostgreSQL Table", postgres_payload)
time.sleep(2)
results['Glue'] = test_scenario("Glue Table", glue_payload)
time.sleep(2)
results['CSV'] = test_scenario("CSV File", csv_payload)

print(f"\n{'='*70}")
print("SUMMARY")
print(f"{'='*70}")
for scenario, success in results.items():
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{scenario:15} {status}")
