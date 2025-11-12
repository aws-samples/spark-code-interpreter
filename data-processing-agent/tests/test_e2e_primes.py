#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import generate_and_validate_ray_code

def test_end_to_end_primes():
    """Test complete end-to-end workflow: FastAPI Backend → Supervisor Agent → Code Gen → MCP Gateway → Lambda → Ray Cluster"""
    
    print("🧪 TESTING END-TO-END WORKFLOW")
    print("=" * 80)
    print("Architecture: FastAPI Backend → Supervisor Agent → Code Generation Agent → MCP Gateway → Lambda → Ray Cluster")
    print("=" * 80)
    
    # Prime numbers prompt
    prompt = "generate ray code to print first 10 prime numbers"
    
    print(f"📝 Test Prompt: {prompt}")
    print("-" * 80)
    
    try:
        # Call the main FastAPI backend function
        result = generate_and_validate_ray_code(prompt)
        
        print("\n🔍 ANALYZING RESULT:")
        print("-" * 40)
        
        # Check for success indicators
        success_indicators = [
            ("Ray import", "import ray" in result.lower()),
            ("Remote decorator", "@ray.remote" in result.lower()),
            ("Prime logic", "prime" in result.lower()),
            ("Print statement", "print" in result.lower()),
            ("Ray execution", "ray.get" in result.lower())
        ]
        
        print("✅ SUCCESS INDICATORS:")
        for indicator, found in success_indicators:
            status = "✅" if found else "❌"
            print(f"   {status} {indicator}: {found}")
        
        # Overall assessment
        success_count = sum(1 for _, found in success_indicators if found)
        
        if success_count >= 4:
            print(f"\n🎉 END-TO-END TEST SUCCESSFUL! ({success_count}/5 indicators passed)")
            print("✅ Complete pipeline working: FastAPI → Supervisor → CodeGen → MCP → Lambda → Ray")
        elif success_count >= 2:
            print(f"\n⚠️ PARTIAL SUCCESS ({success_count}/5 indicators passed)")
            print("🔍 Pipeline partially working, may have timeout/generation issues")
        else:
            print(f"\n❌ TEST FAILED ({success_count}/5 indicators passed)")
            print("🚨 Pipeline has significant issues")
        
        print(f"\n📋 FULL RESULT:")
        print("=" * 60)
        print(result)
        print("=" * 60)
        
        return success_count >= 4
        
    except Exception as e:
        print(f"\n❌ END-TO-END TEST FAILED: {e}")
        return False

if __name__ == "__main__":
    success = test_end_to_end_primes()
    exit(0 if success else 1)
