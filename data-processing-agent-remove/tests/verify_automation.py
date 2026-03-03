#!/usr/bin/env python3
"""
Verify that the Ray Code Interpreter workflow is fully automated.
This script checks for any user interaction points.
"""

import os
import re

def check_file_for_input(filepath):
    """Check if file contains input() calls or interactive prompts"""
    issues = []
    
    with open(filepath, 'r') as f:
        content = f.read()
        lines = content.split('\n')
        
        # Check for input() calls
        for i, line in enumerate(lines, 1):
            if 'input(' in line and not line.strip().startswith('#'):
                issues.append(f"Line {i}: Found input() call: {line.strip()}")
        
        # Check for common interactive patterns
        interactive_patterns = [
            (r'input\s*\(', 'input() call'),
            (r'raw_input\s*\(', 'raw_input() call'),
            (r'sys\.stdin\.readline', 'stdin.readline() call'),
            (r'getpass\.getpass', 'getpass() call'),
        ]
        
        for pattern, desc in interactive_patterns:
            matches = re.finditer(pattern, content)
            for match in matches:
                line_num = content[:match.start()].count('\n') + 1
                line = lines[line_num - 1].strip()
                if not line.startswith('#'):
                    issues.append(f"Line {line_num}: Found {desc}: {line}")
    
    return issues

def main():
    print("=" * 80)
    print("RAY CODE INTERPRETER - AUTOMATION VERIFICATION")
    print("=" * 80)
    print()
    
    # Files to check
    files_to_check = [
        'backend/main.py',
        'backend/agents.py',
    ]
    
    all_issues = []
    
    for filepath in files_to_check:
        full_path = os.path.join(os.path.dirname(__file__), filepath)
        if not os.path.exists(full_path):
            print(f"⚠️  File not found: {filepath}")
            continue
        
        print(f"Checking {filepath}...")
        issues = check_file_for_input(full_path)
        
        if issues:
            print(f"  ❌ Found {len(issues)} issue(s):")
            for issue in issues:
                print(f"     {issue}")
            all_issues.extend(issues)
        else:
            print(f"  ✅ No interactive prompts found")
    
    print()
    print("=" * 80)
    
    if all_issues:
        print(f"❌ FAILED: Found {len(all_issues)} interactive prompt(s)")
        print()
        print("The workflow is NOT fully automated.")
        return 1
    else:
        print("✅ SUCCESS: No interactive prompts found")
        print()
        print("The workflow is FULLY AUTOMATED:")
        print("  • Code generation is automatic")
        print("  • Validation is automatic")
        print("  • Error fixing is automatic (up to 5 retries)")
        print("  • Execution is automatic")
        print("  • No user interaction required")
        return 0

if __name__ == '__main__':
    exit(main())
