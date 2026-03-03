#!/usr/bin/env python3
"""Simple test for Ray Code Interpreter"""

import requests
import time
import subprocess
import os
from uuid import uuid4

API_BASE = "http://localhost:8000"
SESSION_ID = str(uuid4())

print("="*60)
print("Ray Code Interpreter - Simple Test")
print("="*60)

# Start backend
print("\n🚀 Starting backend...")
backend = subprocess.Popen(
    ["python3", "-m", "uvicorn", "main:app", "--port", "8000"],
    cwd="backend",
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL
)

# Wait for startup
time.sleep(8)

try:
    # Test 1: Health check
    print("\n1️⃣  Testing health endpoint...")
    r = requests.get(f"{API_BASE}/")
    assert r.status_code == 200
    print(f"✅ Health check passed: {r.json()['message']}")
    
    # Test 2: Ray status
    print("\n2️⃣  Testing Ray status...")
    r = requests.get(f"{API_BASE}/ray/status")
    assert r.status_code == 200
    print(f"✅ Ray status: {r.json()['status']}")
    
    # Test 3: Code generation
    print("\n3️⃣  Testing code generation...")
    r = requests.post(f"{API_BASE}/generate", json={
        "prompt": "Create a dataset with 50 rows",
        "session_id": SESSION_ID
    }, timeout=30)
    assert r.status_code == 200
    code = r.json()['code']
    print(f"✅ Generated {len(code)} chars of code")
    
    # Test 4: CSV upload
    print("\n4️⃣  Testing CSV upload...")
    r = requests.post(f"{API_BASE}/upload-csv", json={
        "filename": "test.csv",
        "content": "id,val\n1,10\n2,20",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200
    print("✅ CSV uploaded")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED")
    print("="*60)
    
finally:
    # Cleanup
    print("\n🧹 Cleaning up...")
    backend.terminate()
    backend.wait(timeout=5)
    subprocess.run("lsof -ti:8000 | xargs kill -9 2>/dev/null", shell=True)
    print("✅ Cleanup complete")
