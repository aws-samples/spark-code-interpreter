#!/usr/bin/env python3
"""Simple automated test for Glue table code generation"""

import boto3
import json

def test_code_generation_agent_directly():
    """Test code generation agent directly with Glue table prompt"""
    
    print("🧪 Testing Code Generation Agent with Glue Tables\n")
    
    # Simulate what supervisor sends to code generation agent
    test_prompt = """Available Glue tables:
  - northwind.customers at s3://my-data-lake/northwind/customers/

Show first 10 customers"""
    
    ray_system_prompt = """You are a Ray distributed computing code generation specialist.

For Glue tables: Use S3 location from "at s3://..." with ray.data.read_parquet()

GLUE TABLE PATTERN:
For Glue table "database.table at s3://bucket/path/":
ds = ray.data.read_parquet("s3://bucket/path/")

Generate Ray code. Return ONLY executable Python code."""
    
    print("📤 Testing Code Generation Agent...")
    
    client = boto3.client('bedrock-agentcore', region_name='us-east-1', 
                          config=boto3.session.Config(read_timeout=60))
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9',
            qualifier='DEFAULT',
            runtimeSessionId='test-codegen-12345678901234567890',
            payload=json.dumps({
                "prompt": test_prompt,
                "system_prompt": ray_system_prompt
            })
        )
        
        result = response["response"].read().decode("utf-8")
        
        print("✅ Code Generation Agent responded\n")
        print("📝 Generated Code:")
        print("-" * 60)
        print(result[:500])
        print("-" * 60)
        
        # Verify
        checks = {
            "Uses read_parquet": "read_parquet" in result,
            "Has S3 path": "s3://my-data-lake/northwind/customers/" in result,
            "No read_sql": "read_sql" not in result
        }
        
        all_passed = all(checks.values())
        
        for check, passed in checks.items():
            print(f"   {'✅' if passed else '❌'} {check}")
        
        if all_passed:
            print("\n🎉 SUCCESS: Code generation uses read_parquet() correctly!")
            return True
        else:
            print("\n❌ FAILURE: Code generation still incorrect")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_code_generation_agent_directly()
    exit(0 if success else 1)
