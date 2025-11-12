#!/usr/bin/env python3
"""
Comprehensive automated test suite for Ray Code Interpreter
Tests frontend startup, backend functionality, and ensures proper cleanup
"""
import subprocess
import time
import requests
import os
import sys

def cleanup():
    """Ensure all processes are killed"""
    print("🧹 Final cleanup...")
    for cmd in ['uvicorn', 'vite', 'node']:
        subprocess.run(['pkill', '-f', cmd], capture_output=True)
    
    for pid_file in ['backend.pid', 'frontend.pid']:
        if os.path.exists(pid_file):
            os.remove(pid_file)
    
    print("✅ All processes cleaned up")

def run_tests():
    """Run all automated tests"""
    print("🚀 Ray Code Interpreter - Automated Test Suite")
    print("=" * 50)
    
    tests_passed = 0
    total_tests = 3
    
    try:
        # Test 1: Frontend startup test
        print("\n📋 Test 1: Frontend Startup")
        result = subprocess.run(['python3', './test_frontend_startup.py'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Frontend startup test PASSED")
            tests_passed += 1
        else:
            print("❌ Frontend startup test FAILED")
            print(result.stdout)
        
        # Test 2: Full system test
        print("\n📋 Test 2: Full System Integration")
        result = subprocess.run(['python3', './test_full_system.py'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Full system test PASSED")
            tests_passed += 1
        else:
            print("❌ Full system test FAILED")
            print(result.stdout)
        
        # Test 3: Backend import test
        print("\n📋 Test 3: Backend Dependencies")
        result = subprocess.run(['python3', '-c', 'import main; print("Backend imports OK")'], 
                              capture_output=True, text=True, cwd='backend')
        if result.returncode == 0:
            print("✅ Backend dependencies test PASSED")
            tests_passed += 1
        else:
            print("❌ Backend dependencies test FAILED")
            print(result.stderr)
        
        # Results
        print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
        
        if tests_passed == total_tests:
            print("🎉 ALL TESTS PASSED!")
            return True
        else:
            print("💥 SOME TESTS FAILED!")
            return False
    
    except Exception as e:
        print(f"❌ Test suite error: {e}")
        return False
    
    finally:
        cleanup()

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
