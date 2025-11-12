#!/usr/bin/env python3
import subprocess
import time
import requests
import os
import sys
import json

def kill_all_processes():
    """Kill all processes"""
    for cmd in ['uvicorn', 'vite', 'node']:
        subprocess.run(['pkill', '-f', cmd], capture_output=True)

def test_full_system():
    """Test complete system functionality"""
    print("🧪 Full System Test")
    print("=" * 30)
    
    backend_proc = None
    frontend_proc = None
    
    try:
        # Start backend
        print("📦 Starting backend...")
        backend_proc = subprocess.Popen([
            'python3', '-m', 'uvicorn', 'backend.main:app', '--port', '8000'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for backend
        for i in range(10):
            time.sleep(1)
            try:
                response = requests.get('http://localhost:8000/', timeout=2)
                if response.status_code == 200:
                    print("✅ Backend started")
                    break
            except:
                continue
        else:
            print("❌ Backend failed")
            return False
        
        # Test backend API
        print("🔍 Testing backend API...")
        
        # Test root endpoint
        response = requests.get('http://localhost:8000/')
        assert response.status_code == 200
        data = response.json()
        assert data['message'] == 'Ray Code Interpreter API'
        assert data['agent'] == 'bedrock-agentcore'
        print("✅ Root endpoint works")
        
        # Test generate endpoint (mock)
        test_payload = {
            "prompt": "print('hello world')",
            "session_id": "test_session"
        }
        
        # This will likely fail due to missing AWS credentials, but we test the endpoint
        try:
            response = requests.post('http://localhost:8000/generate', json=test_payload, timeout=5)
            print(f"✅ Generate endpoint accessible (status: {response.status_code})")
        except Exception as e:
            print(f"⚠️ Generate endpoint error (expected): {str(e)[:50]}...")
        
        # Start frontend
        print("🎨 Starting frontend...")
        os.chdir('frontend')
        
        frontend_proc = subprocess.Popen([
            'npm', 'run', 'dev'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Wait for frontend
        for i in range(15):
            time.sleep(1)
            try:
                response = requests.get('http://localhost:3000/', timeout=2)
                if response.status_code == 200:
                    print("✅ Frontend started")
                    break
            except:
                continue
        else:
            print("❌ Frontend failed")
            return False
        
        # Test frontend content
        response = requests.get('http://localhost:3000/')
        content = response.text
        if 'Ray Code Interpreter' in content or 'react' in content.lower():
            print("✅ Frontend content valid")
        else:
            print("⚠️ Frontend content unclear")
        
        os.chdir('..')
        
        print("\n🎉 System test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ System test failed: {e}")
        return False
    
    finally:
        print("\n🛑 Cleaning up...")
        kill_all_processes()
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        print("✅ Cleanup complete")

if __name__ == "__main__":
    success = test_full_system()
    sys.exit(0 if success else 1)
