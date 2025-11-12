#!/usr/bin/env python3
import requests
import json

# Test generating code with no datasource
response = requests.post(
    'http://localhost:8000/spark/generate',
    json={
        'prompt': 'Generate code to create a simple DataFrame with numbers 1 to 10',
        'session_id': 'test-no-datasource-123',
        's3_input_path': None,
        'selected_tables': None,
        'selected_postgres_tables': None,
        'execution_engine': 'lambda'
    }
)

print(f"Status: {response.status_code}")
print(f"Response: {json.dumps(response.json(), indent=2)}")
