#!/usr/bin/env python3
import subprocess
import time
import requests
import os
import signal
import sys
import threading

def kill_all_processes():
    """Kill all processes"""
    for cmd in ['uvicorn', 'vite', 'node']:
        subprocess.run(['pkill', '-f', cmd], capture_output=True)
    
    for pid_file in ['backend.pid', 'frontend.pid']:
        if os.path.exists(pid_file):
            os.remove(pid_file)

def test_backend():
    """Test backend startup"""
    print("📦 Testing backend...")
    
    proc = subprocess.Popen([
        'python3', '-m', 'uvicorn', 'backend.main:app', '--port', '8000'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    # Wait longer for backend with strands-agents initialization
    for i in range(20):  # Increased from 15 to 20
        time.sleep(1)
        try:
            response = requests.get('http://localhost:8000/', timeout=3)
            if response.status_code == 200:
                print("✅ Backend started successfully")
                proc.terminate()
                return True
        except:
            continue
    
    proc.terminate()
    print("❌ Backend failed to start")
    return False

def test_frontend():
    """Test frontend startup"""
    print("🎨 Testing frontend...")
    
    os.chdir('frontend')
    
    # Ensure dependencies
    if not os.path.exists('node_modules/.bin/vite'):
        print("📦 Installing dependencies...")
        result = subprocess.run(['npm', 'install'], capture_output=True)
        if result.returncode != 0:
            print("❌ npm install failed")
            return False
    
    proc = subprocess.Popen([
        'npm', 'run', 'dev'
    ], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    
    # Wait for frontend
    for i in range(20):
        time.sleep(1)
        try:
            response = requests.get('http://localhost:3000/', timeout=2)
            if response.status_code == 200:
                print("✅ Frontend started successfully")
                proc.terminate()
                os.chdir('..')
                return True
        except:
            continue
    
    # Check for errors
    _, stderr = proc.communicate(timeout=2)
    if stderr:
        print(f"❌ Frontend error: {stderr.decode()[:200]}")
    else:
        print("❌ Frontend failed to start (no error output)")
    
    proc.terminate()
    os.chdir('..')
    return False

def main():
    """Run automated tests"""
    print("🧪 Automated Frontend Startup Test")
    print("=" * 40)
    
    # Cleanup first
    kill_all_processes()
    time.sleep(2)
    
    try:
        # Test backend
        backend_ok = test_backend()
        
        # Test frontend
        frontend_ok = test_frontend()
        
        # Results
        print("\n📊 Test Results:")
        print(f"   Backend: {'✅ PASS' if backend_ok else '❌ FAIL'}")
        print(f"   Frontend: {'✅ PASS' if frontend_ok else '❌ FAIL'}")
        
        if backend_ok and frontend_ok:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n💥 Some tests failed!")
            return False
    
    finally:
        print("\n🛑 Final cleanup...")
        kill_all_processes()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
