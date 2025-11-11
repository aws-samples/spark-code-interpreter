#!/usr/bin/env python3
"""Deploy MCP Gateway Supervisor Agent to AgentCore Runtime"""

import boto3
import zipfile
import os
import time

def create_deployment_package():
    """Create deployment package with MCP Gateway supervisor agent"""
    
    print("📦 Creating deployment package...")
    
    # Create zip file
    zip_path = "/tmp/backend-mcp.zip"
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add main agent files
        zipf.write("backend/agents.py", "agents.py")
        zipf.write("backend/requirements.txt", "requirements.txt")
        zipf.write("backend/.bedrock_agentcore.yaml", ".bedrock_agentcore.yaml")
        zipf.write("backend/Dockerfile", "Dockerfile")
        
        # Add main.py if it exists
        if os.path.exists("backend/main.py"):
            zipf.write("backend/main.py", "main.py")
    
    print(f"✅ Deployment package created: {zip_path}")
    return zip_path

def upload_to_s3(zip_path):
    """Upload deployment package to S3"""
    
    s3_client = boto3.client('s3', region_name='us-east-1')
    bucket_name = "bedrock-agentcore-260005718447-us-east-1"
    s3_key = "ray-code-interpreter-agent/backend-mcp.zip"
    
    print(f"📤 Uploading to S3: s3://{bucket_name}/{s3_key}")
    
    s3_client.upload_file(zip_path, bucket_name, s3_key)
    
    print("✅ Upload completed")
    return f"s3://{bucket_name}/{s3_key}"

def update_agent_runtime(s3_location):
    """Update AgentCore runtime with new MCP Gateway implementation"""
    
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    
    agent_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9"
    
    print(f"🚀 Updating AgentCore runtime: {agent_runtime_arn}")
    
    # Parse S3 location
    s3_parts = s3_location.replace("s3://", "").split("/", 1)
    bucket_name = s3_parts[0]
    object_key = s3_parts[1]
    
    response = agentcore_client.update_agent_runtime(
        agentRuntimeArn=agent_runtime_arn,
        agentRuntimeConfig={
            'sourceCodeConfig': {
                'sourceCodeLocation': {
                    's3Location': {
                        's3BucketName': bucket_name,
                        's3ObjectKey': object_key
                    }
                }
            }
        }
    )
    
    print("✅ AgentCore runtime update initiated")
    print(f"   Status: {response.get('agentRuntimeStatus')}")
    
    return response

def wait_for_deployment():
    """Wait for deployment to complete"""
    
    agentcore_client = boto3.client('bedrock-agentcore-control', region_name='us-east-1')
    agent_runtime_arn = "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9"
    
    print("⏳ Waiting for deployment to complete...")
    
    for i in range(30):  # Wait up to 5 minutes
        try:
            response = agentcore_client.get_agent_runtime(agentRuntimeArn=agent_runtime_arn)
            status = response.get('agentRuntimeStatus')
            
            print(f"   Status: {status}")
            
            if status == 'AVAILABLE':
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

def main():
    """Main deployment function"""
    
    print("🚀 Deploying MCP Gateway Supervisor Agent")
    print("=" * 60)
    
    try:
        # Create deployment package
        zip_path = create_deployment_package()
        
        # Upload to S3
        s3_location = upload_to_s3(zip_path)
        
        # Update agent runtime
        update_response = update_agent_runtime(s3_location)
        
        # Wait for deployment
        success = wait_for_deployment()
        
        if success:
            print("\n🎉 MCP Gateway Supervisor Agent deployed successfully!")
            print("   The agent now uses MCP Gateway for validation without fallback to direct Lambda calls")
        else:
            print("\n⚠️ Deployment may have issues - check AWS console")
            
        # Clean up
        os.remove(zip_path)
        
    except Exception as e:
        print(f"\n❌ Deployment failed: {e}")

if __name__ == "__main__":
    main()
