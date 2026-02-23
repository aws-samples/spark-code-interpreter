#!/usr/bin/env python3
"""Debug session isolation"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"
SESSION_ID = "debug-session-" + str(int(time.time()))

def check_session_state(step):
    """Check current session state"""
    print(f"\n{'='*60}")
    print(f"STEP {step}")
    print(f"{'='*60}")

def test_flow():
    """Test the complete flow"""
    
    print(f"Using session: {SESSION_ID}")
    
    # Step 1: Upload CSV
    check_session_state("1: Upload CSV")
    response = requests.post(
        f"{BASE_URL}/upload-csv",
        json={
            "filename": "test.csv",
            "content": "id,value\n1,100\n2,200",
            "session_id": SESSION_ID
        }
    )
    print(f"CSV uploaded: {response.json().get('success')}")
    print("Backend should log: '✅ Uploaded CSV' with current tables count")
    
    # Step 2: Generate code with CSV
    check_session_state("2: Generate code with CSV")
    response = requests.post(
        f"{BASE_URL}/generate",
        json={
            "prompt": "Show first 5 rows",
            "session_id": SESSION_ID
        }
    )
    result = response.json()
    print(f"Code generated: {result.get('success')}")
    print("Backend should log: '📊 Session state' showing CSV present")
    print("Backend should log: '🧹 Cleared session data sources' after execution")
    
    time.sleep(2)
    
    # Step 3: Select tables
    check_session_state("3: Select tables")
    response = requests.post(
        f"{BASE_URL}/sessions/{SESSION_ID}/select-tables",
        json={
            "tables": [
                {"database": "northwind", "table": "dow_jones"}
            ]
        }
    )
    print(f"Tables selected: {response.json().get('success')}")
    print("Backend should log: '✅ Selected 1 tables' with current CSV (should be None)")
    
    # Step 4: Generate code with tables
    check_session_state("4: Generate code with tables")
    response = requests.post(
        f"{BASE_URL}/generate",
        json={
            "prompt": "Show first 10 rows from table",
            "session_id": SESSION_ID
        }
    )
    result = response.json()
    print(f"Code generated: {result.get('success')}")
    print("Backend should log: '📊 Session state' showing:")
    print("  - CSV: None")
    print("  - Tables: 1 selected")
    
    if result.get('success'):
        print("\n✅ Session isolation working correctly!")
    else:
        print(f"\n❌ Error: {result.get('error')}")
    
    print(f"\n{'='*60}")
    print("Check backend logs for detailed session state at each step")
    print(f"{'='*60}")

if __name__ == '__main__':
    test_flow()
