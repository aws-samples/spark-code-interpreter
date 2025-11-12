#!/usr/bin/env python3
"""End-to-end automated test for PostgreSQL routing"""

import requests
import json
import time

def test_postgres_routing():
    """Test that PostgreSQL requests route to EMR"""
    
    print("=" * 70)
    print("AUTOMATED POSTGRES ROUTING TEST")
    print("=" * 70)
    
    # Test payload with PostgreSQL tables
    payload = {
        "prompt": "Show me the top 5 orders",
        "session_id": f"test-postgres-{int(time.time())}",
        "framework": "spark",
        "selected_postgres_tables": [
            {
                "connection_name": "aurora-postgres",
                "database": "postgres",
                "schema": "public",
                "table": "orders",
                "jdbc_url": "jdbc:postgresql://aurora-e9d9d867.cluster-cqtoagdxxvgg.us-east-1.rds.amazonaws.com:5432/postgres",
                "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-e9d9d867-9Bxwrf",
                "auth_method": "secrets_manager"
            }
        ]
    }
    
    print(f"\n✓ Test session: {payload['session_id']}")
    print(f"✓ PostgreSQL tables: {len(payload['selected_postgres_tables'])}")
    print(f"✓ Prompt: {payload['prompt']}")
    
    # Send request
    print("\n→ Sending request to /spark/generate...")
    try:
        response = requests.post(
            "http://localhost:8000/spark/generate",
            json=payload,
            timeout=900  # 15 minutes for EMR
        )
        
        print(f"✓ Response status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Success: {result.get('success', False)}")
            
            if result.get('success'):
                print(f"✓ Execution platform: {result.get('execution_platform', 'unknown')}")
                print(f"✓ Code generated: {bool(result.get('code'))}")
                
                if result.get('execution_platform') == 'emr':
                    print("\n✅ TEST PASSED: PostgreSQL routed to EMR")
                    return True
                else:
                    print(f"\n❌ TEST FAILED: Expected EMR, got {result.get('execution_platform')}")
                    return False
            else:
                print(f"\n❌ TEST FAILED: {result.get('error', 'Unknown error')}")
                return False
        else:
            print(f"\n❌ TEST FAILED: HTTP {response.status_code}")
            print(f"Response: {response.text[:500]}")
            return False
            
    except requests.exceptions.Timeout:
        print("\n⏱️  Request timed out (expected for long EMR jobs)")
        print("Check CloudWatch logs to verify EMR execution")
        return None
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    result = test_postgres_routing()
    exit(0 if result else 1)
