#!/usr/bin/env python3
"""Test session isolation"""

import requests
import json

BASE_URL = "http://localhost:8000"
SESSION_ID = "test-session-123"

def test_session_isolation():
    print("=" * 80)
    print("TESTING SESSION ISOLATION")
    print("=" * 80)
    print()
    
    # Test 1: Generate code without CSV
    print("Test 1: Generate code without CSV")
    print("-" * 80)
    
    response = requests.post(f"{BASE_URL}/generate", json={
        "prompt": "Create a dataset with 10 rows",
        "session_id": SESSION_ID
    })
    
    data = response.json()
    print(f"Success: {data.get('success')}")
    print(f"CSV used: {data.get('csv_file_used')}")
    print(f"Expected: None")
    print(f"✅ PASS" if data.get('csv_file_used') is None else f"❌ FAIL")
    print()
    
    # Test 2: Check session state
    print("Test 2: Check session state after execution")
    print("-" * 80)
    
    response = requests.get(f"{BASE_URL}/sessions/{SESSION_ID}/history")
    data = response.json()
    
    if data.get('success'):
        print(f"Execution results: {len(data.get('execution_results', []))}")
        if data.get('execution_results'):
            last_result = data['execution_results'][-1]
            print(f"Last execution success: {last_result.get('success')}")
    
    print()
    print("=" * 80)
    print("Check backend logs for session state messages:")
    print("  - Should see: 'CSV: None' before generation")
    print("  - Should see: 'Cleared session data sources (CSV was: None)'")
    print("=" * 80)

if __name__ == '__main__':
    test_session_isolation()
