#!/usr/bin/env python3

import requests
import json

def test_spark_generate():
    """Test the /spark/generate endpoint"""
    
    url = "http://localhost:8000/spark/generate"
    
    payload = {
        "prompt": "Generate a sample dataframe with 10 rows and 5 columns (id, name, age, city, salary) and show the dataframe",
        "data_source": "Generate sample data",
        "selected_tables": None,
        "selected_postgres_tables": None,
        "session_id": "test-session-123"
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    print("Testing /spark/generate endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")
    print("=" * 50)
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=300)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        print("Response Body:")
        print("=" * 50)
        
        if response.headers.get('content-type', '').startswith('application/json'):
            try:
                response_json = response.json()
                print(json.dumps(response_json, indent=2))
            except json.JSONDecodeError:
                print("Failed to parse JSON response")
                print(response.text)
        else:
            print(response.text)
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    test_spark_generate()
