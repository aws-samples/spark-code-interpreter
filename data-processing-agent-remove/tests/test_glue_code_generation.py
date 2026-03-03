#!/usr/bin/env python3
"""Automated test for Glue table code generation fix"""

import boto3
import json

def test_glue_code_generation():
    """Test that supervisor agent generates correct Ray code for Glue tables"""
    
    print("🧪 Testing Glue Table Code Generation Fix\n")
    
    # Test payload simulating what main.py sends to supervisor
    test_prompt = """Session ID: test-glue-session-12345678901234567890

Available Glue tables:
  - northwind.customers at s3://my-data-lake/northwind/customers/
  - northwind.orders at s3://my-data-lake/northwind/orders/

Count the total number of customers and orders"""
    
    print("📤 Sending test prompt to Supervisor Agent...")
    print(f"   Prompt includes 2 Glue tables with S3 locations\n")
    
    # Call supervisor agent
    client = boto3.client('bedrock-agentcore', region_name='us-east-1')
    
    try:
        response = client.invoke_agent_runtime(
            agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
            qualifier='DEFAULT',
            runtimeSessionId='test-glue-session-12345678901234567890',
            payload=json.dumps({
                "prompt": test_prompt,
                "ray_cluster_ip": "10.0.1.100"
            })
        )
        
        result = response["response"].read().decode("utf-8")
        
        print("✅ Supervisor Agent responded\n")
        print("📝 Generated Code:")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
        # Verify the fix
        print("\n🔍 Verification:")
        
        checks = {
            "Uses read_parquet": "read_parquet" in result,
            "Has S3 customers path": "s3://my-data-lake/northwind/customers/" in result,
            "Has S3 orders path": "s3://my-data-lake/northwind/orders/" in result,
            "No read_sql": "read_sql" not in result,
            "No awsathena": "awsathena" not in result,
            "Has ray.init": "ray.init" in result,
            "Has print statements": "print(" in result
        }
        
        all_passed = True
        for check, passed in checks.items():
            status = "✅" if passed else "❌"
            print(f"   {status} {check}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 SUCCESS: All checks passed!")
            print("   Glue tables are correctly read with ray.data.read_parquet()")
            return True
        else:
            print("\n❌ FAILURE: Some checks failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_glue_code_generation()
    exit(0 if success else 1)
