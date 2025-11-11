#!/usr/bin/env python3
"""Final automated validation - no user input required"""

import requests
import time
import sys

BASE_URL = "http://localhost:8000"
SESSION_ID = f"final-test-{int(time.time())}"

def test_session_isolation():
    """Test that session is properly isolated between prompts"""
    
    print("=" * 80)
    print("AUTOMATED END-TO-END VALIDATION")
    print("=" * 80)
    print(f"Session: {SESSION_ID}\n")
    
    # Test 1: Upload CSV and generate simple code (no execution)
    print("Test 1: Upload CSV")
    r = requests.post(f"{BASE_URL}/upload-csv", json={
        "filename": "test.csv",
        "content": "id,value\n1,100",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200, f"CSV upload failed: {r.status_code}"
    print("  ✅ CSV uploaded")
    
    # Test 2: Generate code (will auto-execute)
    print("\nTest 2: Generate code with CSV (will execute)")
    r = requests.post(f"{BASE_URL}/generate", json={
        "prompt": "Create a simple dataset with 5 rows",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200, f"Generate failed: {r.status_code}"
    result = r.json()
    
    if not result.get('success'):
        print(f"  ⚠️  Generation failed: {result.get('error')}")
        print("  Continuing test...")
    else:
        print(f"  ✅ Code generated and executed")
        print(f"  CSV used: {result.get('csv_file_used')}")
    
    # Wait for execution to complete and session to clear
    print("\n  Waiting for session to clear...")
    time.sleep(5)
    
    # Test 3: Generate again - should NOT have CSV
    print("\nTest 3: Generate again (CSV should be cleared)")
    r = requests.post(f"{BASE_URL}/generate", json={
        "prompt": "Create another dataset with 10 rows",
        "session_id": SESSION_ID
    })
    assert r.status_code == 200, f"Second generate failed: {r.status_code}"
    result2 = r.json()
    
    csv_used_second = result2.get('csv_file_used')
    
    print(f"  CSV used in second generation: {csv_used_second}")
    
    # Verification
    print("\n" + "=" * 80)
    print("VALIDATION RESULT")
    print("=" * 80)
    
    if csv_used_second is None:
        print("✅ SUCCESS: Session isolation working correctly")
        print("   - CSV was cleared after first execution")
        print("   - Second generation had clean session")
        return True
    else:
        print("❌ FAILURE: Session isolation NOT working")
        print(f"   - CSV '{csv_used_second}' still in session")
        print("   - Session was not cleared after execution")
        return False

def cleanup():
    """Clean up test session"""
    print("\n" + "=" * 80)
    print("CLEANUP")
    print("=" * 80)
    try:
        # Clear the test session
        requests.post(f"{BASE_URL}/sessions/{SESSION_ID}/reset", timeout=2)
        print("✅ Test session cleared")
    except:
        print("⚠️  Could not clear test session (may not exist)")
    
    print("=" * 80)

if __name__ == '__main__':
    try:
        success = test_session_isolation()
        cleanup()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
        cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        cleanup()
        sys.exit(1)
