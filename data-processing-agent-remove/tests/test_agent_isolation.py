#!/usr/bin/env python3

import boto3
import json
import time
import uuid
import signal

class TimeoutError(Exception):
    pass

def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")

def test_with_timeout(test_func, timeout_seconds=15):
    """Run test function with timeout"""
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    
    try:
        result = test_func()
        signal.alarm(0)  # Cancel alarm
        return result
    except TimeoutError:
        print(f"❌ Test timed out after {timeout_seconds}s")
        return False
    except Exception as e:
        signal.alarm(0)  # Cancel alarm
        print(f"❌ Test failed: {e}")
        return False

def test_code_generation_agent():
    """Test code generation agent directly"""
    
    print("🔄 Testing code generation agent...")
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(
            read_timeout=10,
            connect_timeout=5
        )
    )
    
    session_id = f"codegen-test-{uuid.uuid4().hex}"
    
    # Code generation payload
    payload = json.dumps({
        "prompt": "Create a simple Spark DataFrame with 2 rows",
        "session_id": session_id,
        "framework": "spark"
    })
    
    start_time = time.time()
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/code_generation_agent-xyz',
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=payload,
        contentType="application/json"
    )
    end_time = time.time()
    
    print(f"✅ Code generation agent responded in {end_time - start_time:.2f}s")
    return True

def test_spark_supervisor_agent():
    """Test Spark supervisor agent directly"""
    
    print("🔄 Testing Spark supervisor agent...")
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(
            read_timeout=10,
            connect_timeout=5
        )
    )
    
    session_id = f"spark-test-{uuid.uuid4().hex}"
    
    # Spark execution payload
    payload = json.dumps({
        "user_request": "Create a simple DataFrame with 2 rows",
        "session_id": session_id,
        "execution_platform": "lambda",
        "s3_output_path": "s3://spark-data-260005718447-us-east-1/output/"
    })
    
    start_time = time.time()
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=payload,
        contentType="application/json"
    )
    end_time = time.time()
    
    print(f"✅ Spark supervisor agent responded in {end_time - start_time:.2f}s")
    return True

def test_ray_supervisor_agent():
    """Test Ray supervisor agent for comparison"""
    
    print("🔄 Testing Ray supervisor agent...")
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(
            read_timeout=10,
            connect_timeout=5
        )
    )
    
    session_id = f"ray-test-{uuid.uuid4().hex}"
    
    # Ray execution payload
    payload = json.dumps({
        "user_request": "Simple test request",
        "session_id": session_id
    })
    
    start_time = time.time()
    response = agentcore_client.invoke_agent_runtime(
        agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky',
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=payload,
        contentType="application/json"
    )
    end_time = time.time()
    
    print(f"✅ Ray supervisor agent responded in {end_time - start_time:.2f}s")
    return True

if __name__ == "__main__":
    print("🧪 Testing Individual Agents (15s timeout each)")
    print("=" * 50)
    
    # Test each agent individually with timeout
    codegen_ok = test_with_timeout(test_code_generation_agent, 15)
    print()
    
    spark_ok = test_with_timeout(test_spark_supervisor_agent, 15)
    print()
    
    ray_ok = test_with_timeout(test_ray_supervisor_agent, 15)
    print()
    
    # Summary
    print("📊 Agent Test Results:")
    print(f"   Code Generation Agent: {'✅ OK' if codegen_ok else '❌ FAIL'}")
    print(f"   Spark Supervisor Agent: {'✅ OK' if spark_ok else '❌ FAIL'}")
    print(f"   Ray Supervisor Agent: {'✅ OK' if ray_ok else '❌ FAIL'}")
    
    # Analysis
    if not any([codegen_ok, spark_ok, ray_ok]):
        print("🔍 All AgentCore agents are failing - service-wide issue")
    elif codegen_ok and not spark_ok:
        print("🔍 Issue is specific to Spark supervisor agent")
    elif spark_ok and not codegen_ok:
        print("🔍 Issue is specific to code generation agent")
    elif ray_ok and not spark_ok:
        print("🔍 Issue is specific to Spark supervisor agent")
    else:
        print("🔍 Mixed results - partial service degradation")
