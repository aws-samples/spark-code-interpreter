"""Test multiple executions to reproduce the issue"""

import requests
import json
import time

BACKEND_URL = "http://localhost:8000"

# Test code
test_code = """import ray
ray.init()

@ray.remote
def calculate_sum():
    numbers = list(range(1, 11))
    total = sum(numbers)
    return total

result = ray.get(calculate_sum.remote())
print(f"Sum of numbers 1-10: {result}")
"""

session_id = "test-session-multiple-exec"

print("=" * 60)
print("Testing multiple executions")
print("=" * 60)

for i in range(3):
    print(f"\n🧪 Execution {i+1}")
    print("-" * 60)
    
    # Execute code
    response = requests.post(
        f"{BACKEND_URL}/execute",
        json={"code": test_code, "session_id": session_id}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Success: {result.get('success')}")
        print(f"📄 Output length: {len(result.get('output', ''))}")
        print(f"📄 Output: {result.get('output', 'NO OUTPUT')}")
    else:
        print(f"❌ Error: {response.status_code}")
        print(f"   {response.text}")
    
    # Reset session (like frontend does)
    reset_response = requests.post(f"{BACKEND_URL}/sessions/{session_id}/reset")
    print(f"🔄 Session reset: {reset_response.status_code}")
    
    time.sleep(2)

print("\n" + "=" * 60)
print("Test complete")
print("=" * 60)
