#!/usr/bin/env python3
"""
Automated validation of backend imports - no user input required
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

print("🔍 Validating Backend Imports (Automated)")
print("=" * 60)

# Test 1: Package import
print("\n1️⃣ Testing package import (from backend.main)...")
try:
    from backend.main import app
    print("   ✅ Package import successful")
except ImportError as e:
    print(f"   ❌ Package import failed: {e}")
    sys.exit(1)

# Test 2: Config functions
print("\n2️⃣ Testing config functions...")
try:
    from backend.config import get_ray_private_ip, get_ray_public_ip, get_s3_bucket
    private_ip = get_ray_private_ip()
    public_ip = get_ray_public_ip()
    bucket = get_s3_bucket()
    print(f"   ✅ Config loaded: {private_ip}, {public_ip}, {bucket}")
except Exception as e:
    print(f"   ❌ Config failed: {e}")
    sys.exit(1)

# Test 3: Uvicorn can load app
print("\n3️⃣ Testing uvicorn import...")
try:
    from uvicorn.importer import import_from_string
    app = import_from_string('backend.main:app')
    print("   ✅ Uvicorn can load app")
except Exception as e:
    print(f"   ❌ Uvicorn load failed: {e}")
    sys.exit(1)

# Test 4: Direct module import
print("\n4️⃣ Testing direct module import...")
try:
    sys.path.insert(0, 'backend')
    import main as direct_main
    print("   ✅ Direct import successful")
except ImportError as e:
    print(f"   ❌ Direct import failed: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("✅ ALL IMPORT TESTS PASSED")
print("\nBackend is ready to start with:")
print("  python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
