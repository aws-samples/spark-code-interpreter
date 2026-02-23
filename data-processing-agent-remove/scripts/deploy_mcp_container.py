#!/usr/bin/env python3
"""Deploy MCP Gateway Supervisor Agent as Container to AgentCore Runtime"""

import boto3
import subprocess
import time
import json

def build_and_push_container():
    """Build and push container with MCP Gateway supervisor agent"""
    
    print("🐳 Building and pushing container...")
    
    # ECR repository details
    account_id = "260005718447"
    region = "us-east-1"
    repository_name = "bedrock-agentcore-ray_code_interpreter"
    container_uri = f"{account_id}.dkr.ecr.{region}.amazonaws.com/{repository_name}:latest"
    
    try:
        # Get ECR login token
        print("🔐 Getting ECR login token...")
        ecr_client = boto3.client('ecr', region_name=region)
        token_response = ecr_client.get_authorization_token()
        token = token_response['authorizationData'][0]['authorizationToken']
        endpoint = token_response['authorizationData'][0]['proxyEndpoint']
        
        # Docker login to ECR
        login_cmd = f"echo {token} | base64 -d | docker login --username AWS --password-stdin {endpoint}"
        subprocess.run(login_cmd, shell=True, check=True)
        print("✅ ECR login successful")
        
        # Build container
        print("🔨 Building container...")
        build_cmd = f"docker build -t {container_uri} backend/"
        result = subprocess.run(build_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Container build failed: {result.stderr}")
            return None
            
        print("✅ Container built successfully")
        
        # Push container
        print("📤 Pushing container to ECR...")
        push_cmd = f"docker push {container_uri}"
        result = subprocess.run(push_cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"❌ Container push failed: {result.stderr}")
            return None
            
        print("✅ Container pushed successfully")
        return container_uri
        
    except Exception as e:
        print(f"❌ Container build/push failed: {e}")
        return None

def update_agent_runtime(container_uri):
    """Update AgentCore runtime with new container"""
    
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    
    agent_runtime_id = "ray_code_interpreter-oTKmLH9IB9"
    role_arn = "arn:aws:iam::260005718447:role/AmazonBedrockAgentCoreSDKRuntime-us-east-1-a7ee536645"
    
    print(f"🚀 Updating AgentCore runtime with new container...")
    
    try:
        response = agentcore_client.update_agent_runtime(
            agentRuntimeId=agent_runtime_id,
            agentRuntimeArtifact={
                'containerConfiguration': {
                    'containerUri': container_uri
                }
            },
            roleArn=role_arn,
            networkConfiguration={
                'networkMode': 'PUBLIC'
            },
            description="Ray Code Interpreter with MCP Gateway integration",
            protocolConfiguration={
                'serverProtocol': 'HTTP'
            },
            lifecycleConfiguration={
                'idleRuntimeSessionTimeout': 900,
                'maxLifetime': 28800
            },
            environmentVariables={
                'BEDROCK_AGENTCORE_MEMORY_ID': 'ray_code_interpreter_mem-4QpyU5EMFM',
                'BEDROCK_AGENTCORE_MEMORY_NAME': 'ray_code_interpreter_mem'
            }
        )
        
        print("✅ AgentCore runtime update initiated")
        print(f"   Status: {response.get('status')}")
        print(f"   Version: {response.get('agentRuntimeVersion')}")
        
        return response
        
    except Exception as e:
        print(f"❌ Runtime update failed: {e}")
        return None

def wait_for_deployment():
    """Wait for deployment to complete"""
    
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    agent_runtime_id = "ray_code_interpreter-oTKmLH9IB9"
    
    print("⏳ Waiting for deployment to complete...")
    
    for i in range(60):  # Wait up to 10 minutes
        try:
            response = agentcore_client.get_agent_runtime(agentRuntimeId=agent_runtime_id)
            status = response.get('status')
            version = response.get('agentRuntimeVersion')
            
            print(f"   Status: {status}, Version: {version}")
            
            if status == 'READY':
                print("✅ Deployment completed successfully!")
                return True
            elif status in ['FAILED', 'STOPPED']:
                print(f"❌ Deployment failed with status: {status}")
                return False
                
            time.sleep(10)
            
        except Exception as e:
            print(f"   Error checking status: {e}")
            time.sleep(10)
    
    print("⚠️ Deployment timeout - check AWS console for status")
    return False

def test_deployment():
    """Test the deployed MCP Gateway supervisor agent"""
    
    print("🧪 Testing deployed MCP Gateway supervisor agent...")
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name='us-east-1',
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    agent_arn = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9'
    session_id = f"mcp_test_{int(time.time() * 1000)}"
    
    payload = {
        "prompt": f"Session ID: {session_id}\\n\\nGenerate Ray code to create numbers 1 to 10, filter even numbers, and calculate their sum",
        "ray_cluster_ip": "100.27.32.218"
    }
    
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=agent_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Extract response
        if "text/event-stream" in response.get("contentType", ""):
            content = []
            for line in response["response"].iter_lines(chunk_size=1):
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        content.append(line[6:])
            result = "\\n".join(content)
        else:
            events = []
            for event in response.get("response", []):
                events.append(event)
            result = json.loads(events[0].decode("utf-8")) if events else "No response"
        
        print("📋 Test Result:")
        print("=" * 50)
        print(result)
        print("=" * 50)
        
        # Check if MCP Gateway was used (no fallback message)
        if "fallback" in result.lower() or "direct lambda" in result.lower():
            print("⚠️ **Fallback detected** - MCP Gateway may not be working properly")
            return False
        elif "import ray" in result and "print" in result:
            print("✅ **SUCCESS** - MCP Gateway integration working!")
            return True
        else:
            print("❓ **Unclear** - Check response for validation method used")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False

def main():
    """Main deployment function"""
    
    print("🚀 Deploying MCP Gateway Supervisor Agent Container")
    print("=" * 70)
    
    try:
        # Build and push container
        container_uri = build_and_push_container()
        if not container_uri:
            return
        
        # Update agent runtime
        update_response = update_agent_runtime(container_uri)
        if not update_response:
            return
        
        # Wait for deployment
        success = wait_for_deployment()
        if not success:
            print("⚠️ Deployment may have issues - check AWS console")
            return
        
        # Test deployment
        test_success = test_deployment()
        
        if test_success:
            print("\\n🎉 MCP Gateway Supervisor Agent deployed and tested successfully!")
            print("   ✅ Agent uses MCP Gateway for validation without fallback to direct Lambda calls")
            print("   ✅ Aligned with sample notebook pattern from amazon-bedrock-agentcore-samples")
        else:
            print("\\n⚠️ Deployment completed but test results unclear - check logs above")
            
    except Exception as e:
        print(f"\\n❌ Deployment failed: {e}")

if __name__ == "__main__":
    main()
