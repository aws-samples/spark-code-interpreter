from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from deployment_config_helper import load_config, save_config

boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "spark_code_generator"
response = agentcore_runtime.configure(
    entrypoint="agents.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)
response

launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)

print(launch_result)

# ============================================================================
# AUTOMATIC IAM PERMISSION ATTACHMENT (Code Gen Agent)
# ============================================================================

import boto3
import json
from datetime import datetime, timezone, timedelta

# Get account ID
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']

iam_client = boto3.client('iam', region_name=region)

# List all roles and find the agent's execution role
execution_role_arn = None
role_name = None

print(f"\n🔍 Searching for agent execution role...")

try:
    # List all roles with pagination
    paginator = iam_client.get_paginator('list_roles')
    
    for page in paginator.paginate():
        for role in page['Roles']:
            # Check if role matches the pattern
            if role['RoleName'].startswith(f'AmazonBedrockAgentCoreSDKRuntime-{region}-'):
                # Check if this role was created/updated recently (within last 10 minutes)
                time_diff = datetime.now(timezone.utc) - role['CreateDate']
                
                if time_diff < timedelta(minutes=10):
                    execution_role_arn = role['Arn']
                    role_name = role['RoleName']
                    print(f"✅ Found recently created/updated role: {role_name}")
                    break
        
        if execution_role_arn:
            break
    
    # If no recent role found, use the first matching role
    if not execution_role_arn:
        print("⚠️  No recently created role found, searching for any matching role...")
        response_roles = iam_client.list_roles()
        for role in response_roles['Roles']:
            if role['RoleName'].startswith(f'AmazonBedrockAgentCoreSDKRuntime-{region}-'):
                execution_role_arn = role['Arn']
                role_name = role['RoleName']
                print(f"✅ Found existing role: {role_name}")
                break

except Exception as e:
    print(f"⚠️  Error listing roles: {str(e)}")

# Fallback: Try reading from .bedrock_agentcore.yaml
if not execution_role_arn:
    print("🔍 Trying to read role from .bedrock_agentcore.yaml...")
    try:
        import yaml
        with open('.bedrock_agentcore.yaml', 'r') as f:
            config_yaml = yaml.safe_load(f)
            if 'execution_role' in config_yaml:
                execution_role_arn = config_yaml['execution_role']
                role_name = execution_role_arn.split('/')[-1]
                print(f"✅ Found role in config: {role_name}")
    except Exception as e:
        print(f"⚠️  Could not read config file: {str(e)}")

if execution_role_arn and role_name:
    print(f"\n🔧 Adding permissions to role: {role_name}")
    
    # Code gen agent needs minimal permissions (just S3 for code storage)
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "S3CodeStorage",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::spark-data-{account_id}-{region}/*"
                ]
            }
        ]
    }
    
    try:
        # Check if policy already exists
        try:
            existing_policy = iam_client.get_role_policy(
                RoleName=role_name,
                PolicyName='CodeGenAgentPolicy'
            )
            print(f"ℹ️  Policy already exists, updating...")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  Creating new policy...")
        
        # Put (create or update) the policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='CodeGenAgentPolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Successfully added permissions to {role_name}")
        print("   ✓ S3 code storage")
        
    except Exception as e:
        print(f"⚠️  Warning: Could not add IAM permissions: {str(e)}")
        print("   You may need to add these permissions manually")
else:
    print("\n⚠️  Warning: Could not determine execution role ARN")
    print("   IAM permissions must be added manually")
    print(f"   Search for roles starting with: AmazonBedrockAgentCoreSDKRuntime-{region}-")

# ============================================================================
# END IAM PERMISSION ATTACHMENT
# ============================================================================

# Update config with the deployed ARN
if hasattr(launch_result, 'agent_arn') and launch_result.agent_arn:
    config = load_config()
    if 'global' not in config:
        config['global'] = {}
    config['global']['code_gen_agent_arn'] = launch_result.agent_arn
    save_config(config)
    print(f"✅ Updated config with Code Generation Agent ARN: {launch_result.agent_arn}")
else:
    print("⚠️ Could not extract agent ARN from launch result")