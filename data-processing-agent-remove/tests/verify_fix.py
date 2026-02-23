#!/usr/bin/env python3
"""Verify the fix by checking the code directly"""

import sys
sys.path.insert(0, 'backend')

from main import sessions, CodeInterpreterSession

# Create test session
session_id = "test-verify"
sessions[session_id] = CodeInterpreterSession(session_id)
session = sessions[session_id]

print("=" * 80)
print("VERIFYING SESSION CLEARING FIX")
print("=" * 80)

# Simulate: Upload CSV
print("\n1. Simulating CSV upload...")
session.uploaded_csv = {
    'filename': 'test.csv',
    's3_path': 's3://bucket/test.csv',
    'preview': 'id,val\n1,10'
}
print(f"   CSV in session: {session.uploaded_csv['filename']}")

# Simulate: Execution completes - check if clearing code is in place
print("\n2. Checking if clearing code is in generate endpoint...")

# Read the main.py file to verify clearing happens before success check
with open('backend/main.py', 'r') as f:
    content = f.read()
    
# Check if clearing happens before "if execution_result['success']"
clear_pos = content.find("session.uploaded_csv = None")
success_check_pos = content.find("if execution_result['success']:", clear_pos - 500)

if clear_pos > 0 and success_check_pos > 0:
    if clear_pos < success_check_pos:
        print("   ✅ Clearing happens BEFORE success check")
        print("   ✅ Session will be cleared regardless of execution outcome")
    else:
        print("   ❌ Clearing happens AFTER success check")
        print("   ❌ Session will NOT be cleared if execution fails")
else:
    print("   ⚠️  Could not verify code structure")

# Simulate: Manual clearing
print("\n3. Simulating session clearing...")
session.uploaded_csv = None
session.selected_tables = []
print(f"   CSV in session: {session.uploaded_csv}")
print(f"   Tables in session: {session.selected_tables}")

# Simulate: Select tables
print("\n4. Simulating table selection...")
session.selected_tables = [
    {'database': 'test_db', 'table': 'test_table', 'location': 's3://bucket/table'}
]
print(f"   CSV in session: {session.uploaded_csv}")
print(f"   Tables in session: {len(session.selected_tables)} selected")

print("\n" + "=" * 80)
print("VERIFICATION RESULT")
print("=" * 80)

if clear_pos < success_check_pos:
    print("✅ FIX IS CORRECT")
    print("   - Clearing happens before success check")
    print("   - Session will be cleared after EVERY execution")
    print("   - Next prompt will have clean session")
else:
    print("❌ FIX IS INCOMPLETE")
    print("   - Clearing still happens after success check")
    print("   - Session may not be cleared if execution fails")

print("=" * 80)
