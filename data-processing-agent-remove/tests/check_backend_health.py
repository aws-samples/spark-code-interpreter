#!/usr/bin/env python3
"""
Quick backend health check - automated, no hanging
"""
import requests
import sys

BACKEND_URL = "http://localhost:8000"

print("🏥 Backend Health Check (Automated)")
print("=" * 60)

try:
    response = requests.get(f"{BACKEND_URL}/health", timeout=3)
    if response.status_code == 200:
        data = response.json()
        print("✅ Backend is healthy")
        print(f"   Ray Private IP: {data.get('ray_private_ip')}")
        print(f"   Ray Public IP: {data.get('ray_public_ip')}")
        print(f"   S3 Bucket: {data.get('s3_bucket')}")
        sys.exit(0)
    else:
        print(f"⚠️  Backend returned status {response.status_code}")
        sys.exit(1)
except requests.exceptions.ConnectionError:
    print("❌ Backend not running at http://localhost:8000")
    print("\nTo start backend:")
    print("  cd /Users/nmurich/strands-agents/agent-core/data-processing-agent")
    print("  conda run -n bedrock-sdk python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000")
    sys.exit(1)
except requests.exceptions.Timeout:
    print("❌ Backend health check timed out")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
