#!/usr/bin/env python3
import subprocess
import time
import requests
import sys
import signal
import os

backend_proc = None
frontend_proc = None

def cleanup():
    global backend_proc, frontend_proc
    if backend_proc:
        backend_proc.terminate()
        backend_proc.wait()
    if frontend_proc:
        frontend_proc.terminate()
        frontend_proc.wait()
    print("\n✅ Cleanup complete")

def signal_handler(sig, frame):
    cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

try:
    # Start backend
    print("🚀 Starting backend...")
    backend_proc = subprocess.Popen(
        ["python3", "-m", "uvicorn", "main:app", "--port", "8000"],
        cwd="backend",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(5)
    
    # Test backend health
    print("🔍 Testing backend...")
    resp = requests.get("http://localhost:8000/", timeout=5)
    assert resp.status_code == 200
    print("✅ Backend running")
    
    # Test Ray status
    resp = requests.get("http://localhost:8000/ray/status", timeout=5)
    print(f"✅ Ray status: {resp.json()}")
    
    # Test code generation
    print("🔍 Testing code generation...")
    resp = requests.post(
        "http://localhost:8000/generate",
        json={"prompt": "Create a dataset with 100 rows", "session_id": "test"},
        timeout=30
    )
    if resp.status_code != 200:
        print(f"❌ Generation failed: {resp.status_code} - {resp.text}")
        sys.exit(1)
    result = resp.json()
    assert result["success"]
    print(f"✅ Generated code ({len(result['code'])} chars)")
    
    # Test code execution
    print("🔍 Testing code execution...")
    resp = requests.post(
        "http://localhost:8000/execute",
        json={"code": result["code"], "session_id": "test"},
        timeout=90
    )
    assert resp.status_code == 200
    exec_result = resp.json()
    print(f"✅ Execution: {exec_result['success']}")
    if exec_result['success']:
        print(f"Output: {exec_result['result'][:200]}")
    
    # Test CSV upload
    print("🔍 Testing CSV upload...")
    csv_content = "date,price,volume\n2024-01-01,150.5,1000\n2024-01-02,152.3,1200"
    resp = requests.post(
        "http://localhost:8000/upload-csv",
        json={"filename": "test.csv", "content": csv_content, "session_id": "test2"},
        timeout=10
    )
    assert resp.status_code == 200
    csv_result = resp.json()
    assert csv_result["success"]
    print(f"✅ CSV uploaded to: {csv_result['s3_path']}")
    
    # Test code generation with CSV
    print("🔍 Testing code generation with CSV...")
    resp = requests.post(
        "http://localhost:8000/generate",
        json={"prompt": "Read the CSV and show the first 5 rows", "session_id": "test2"},
        timeout=30
    )
    assert resp.status_code == 200
    result = resp.json()
    assert result["success"]
    assert "s3://" in result["code"]
    print(f"✅ Generated code with S3 path")
    
    print("\n✅ All tests passed!")
    
finally:
    cleanup()
