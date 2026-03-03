#!/usr/bin/env python3
"""Automated end-to-end test for Ray Code Interpreter"""

import requests
import time
import subprocess
import signal
import os
import sys
from uuid import uuid4

API_BASE = "http://localhost:8000"
SESSION_ID = str(uuid4())

backend_process = None
frontend_process = None

def cleanup():
    """Kill all processes and free ports"""
    global backend_process, frontend_process
    
    print("\n🧹 Cleaning up...")
    
    # Kill processes
    if backend_process:
        backend_process.terminate()
        backend_process.wait(timeout=5)
    if frontend_process:
        frontend_process.terminate()
        frontend_process.wait(timeout=5)
    
    # Kill any remaining processes on ports
    for port in [8000, 3000]:
        try:
            subprocess.run(f"lsof -ti:{port} | xargs kill -9", shell=True, stderr=subprocess.DEVNULL)
        except:
            pass
    
    print("✅ Cleanup complete")

def start_backend():
    """Start backend server"""
    global backend_process
    
    print("🚀 Starting backend...")
    backend_process = subprocess.Popen(
        ["python3", "-m", "uvicorn", "main:app", "--port", "8000", "--log-level", "error"],
        cwd="backend",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for backend to be ready
    for i in range(30):
        try:
            response = requests.get(f"{API_BASE}/", timeout=1)
            if response.status_code == 200:
                print("✅ Backend started")
                return True
        except requests.exceptions.ConnectionError:
            time.sleep(1)
        except Exception as e:
            print(f"   Waiting... ({i+1}/30)")
            time.sleep(1)
    
    print("❌ Backend failed to start")
    return False

def test_ray_status():
    """Test Ray cluster status"""
    print("\n📊 Testing Ray status...")
    response = requests.get(f"{API_BASE}/ray/status")
    assert response.status_code == 200, "Ray status endpoint failed"
    data = response.json()
    assert "status" in data, "Missing status in response"
    print(f"✅ Ray status: {data['status']}")
    return data

def test_code_generation():
    """Test code generation"""
    print("\n🤖 Testing code generation...")
    response = requests.post(
        f"{API_BASE}/generate",
        json={
            "prompt": "Create a dataset with 100 rows and show first 3",
            "session_id": SESSION_ID
        },
        timeout=30
    )
    assert response.status_code == 200, "Code generation failed"
    data = response.json()
    assert data["success"], "Code generation not successful"
    assert "code" in data, "No code in response"
    assert len(data["code"]) > 0, "Empty code generated"
    print(f"✅ Generated {len(data['code'])} chars of code")
    return data["code"]

def test_code_execution(code):
    """Test code execution"""
    print("\n⚡ Testing code execution...")
    response = requests.post(
        f"{API_BASE}/execute",
        json={
            "code": code,
            "session_id": SESSION_ID
        },
        timeout=90
    )
    assert response.status_code == 200, "Code execution failed"
    data = response.json()
    assert "result" in data, "No result in response"
    print(f"✅ Execution completed: {data.get('success', False)}")
    print(f"   Result preview: {data['result'][:100]}...")
    return data

def test_csv_upload():
    """Test CSV upload"""
    print("\n📁 Testing CSV upload...")
    csv_content = "id,value\n1,10\n2,20\n3,30"
    response = requests.post(
        f"{API_BASE}/upload-csv",
        json={
            "filename": "test.csv",
            "content": csv_content,
            "session_id": SESSION_ID
        }
    )
    assert response.status_code == 200, "CSV upload failed"
    data = response.json()
    assert data["success"], "CSV upload not successful"
    print("✅ CSV uploaded successfully")
    return data

def test_file_upload():
    """Test file upload"""
    print("\n📄 Testing file upload...")
    code_content = "import ray\nprint('test')"
    response = requests.post(
        f"{API_BASE}/upload",
        json={
            "filename": "test.py",
            "content": code_content,
            "session_id": SESSION_ID
        }
    )
    assert response.status_code == 200, "File upload failed"
    data = response.json()
    assert data["success"], "File upload not successful"
    print("✅ File uploaded successfully")
    return data

def test_session_history():
    """Test session history"""
    print("\n📜 Testing session history...")
    response = requests.get(f"{API_BASE}/history/{SESSION_ID}")
    assert response.status_code == 200, "History retrieval failed"
    data = response.json()
    assert "history" in data, "No history in response"
    print(f"✅ Retrieved history: {len(data['history'])} items")
    return data

def run_tests():
    """Run all tests"""
    print("="*60)
    print("Ray Code Interpreter - Automated E2E Test")
    print("="*60)
    
    try:
        # Start backend
        if not start_backend():
            print("❌ Failed to start backend")
            return False
        
        # Run tests
        test_ray_status()
        code = test_code_generation()
        test_code_execution(code)
        test_csv_upload()
        test_file_upload()
        test_session_history()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        cleanup()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
