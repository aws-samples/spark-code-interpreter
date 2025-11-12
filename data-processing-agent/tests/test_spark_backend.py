#!/usr/bin/env python3
import requests
import json

response = requests.post(
    'http://localhost:8000/spark/generate',
    json={
        'prompt': 'Generate a sample DataFrame with 10 rows and 5 columns (id, name, age, city, salary) and show the DataFrame',
        'session_id': 'test-spark-sample-df-123',
        'execution_engine': 'lambda'
    }
)

print(f"Status: {response.status_code}")
result = response.json()
print(f"\nSuccess: {result.get('success')}")
print(f"Framework: {result.get('framework')}")
print(f"Platform: {result.get('execution_platform')}")

if result.get('success'):
    spark_result = result.get('result', {})
    print(f"\nExecution Result: {spark_result.get('execution_result')}")
    print(f"\nCode Generated: {spark_result.get('spark_code') is not None}")
    if spark_result.get('spark_code'):
        print(f"\nFirst 200 chars of code:\n{spark_result.get('spark_code')[:200]}...")
    print(f"\nExecution Output: {spark_result.get('execution_output')}")
else:
    print(f"\nError: {result}")
