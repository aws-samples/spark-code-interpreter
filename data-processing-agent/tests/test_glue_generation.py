#!/usr/bin/env python3
import requests
import json

response = requests.post(
    'http://localhost:8000/spark/generate',
    json={
        'prompt': 'Find the top 10 transactions by closing price',
        'session_id': 'test-glue-nasdaq-123',
        'selected_tables': [
            {'database': 'northwind', 'table': 'nasdaq'}
        ],
        'execution_engine': 'auto'
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
