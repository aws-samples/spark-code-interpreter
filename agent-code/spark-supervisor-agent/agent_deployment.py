from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from deployment_config_helper import load_config, save_config

boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "spark_supervisor_agent"

response = agentcore_runtime.configure(
    entrypoint="spark_supervisor_agent.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)

print("Configuration response:")
print(response)

launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)

print("\nLaunch result:")
print(launch_result)

# ============================================================================
# AUTOMATIC IAM PERMISSION ATTACHMENT
# ============================================================================

import boto3
import json
from datetime import datetime, timezone, timedelta

# Get account ID
sts_client = boto3.client('sts')
account_id = sts_client.get_caller_identity()['Account']

iam_client = boto3.client('iam', region_name=region)

# List all roles and find the agent's execution role
# The role name pattern is: AmazonBedrockAgentCoreSDKRuntime-{region}-{hash}
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
    print(f"\n🔧 Adding comprehensive permissions to role: {role_name}")
    
    # Define comprehensive policy
    policy_document = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "LambdaInvoke",
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": [
                    f"arn:aws:lambda:{region}:{account_id}:function:dev-spark-on-lambda",
                    f"arn:aws:lambda:{region}:{account_id}:function:prod-spark-on-lambda"
                ]
            },
            {
                "Sid": "S3Access",
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:GetObject",
                    "s3:ListBucket",
                    "s3:DeleteObject"
                ],
                "Resource": [
                    f"arn:aws:s3:::spark-data-{account_id}-{region}",
                    f"arn:aws:s3:::spark-data-{account_id}-{region}/*"
                ]
            },
            {
                "Sid": "BedrockAgentCoreInvoke",
                "Effect": "Allow",
                "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
                "Resource": [f"arn:aws:bedrock-agentcore:{region}:{account_id}:runtime/*"]
            },
            {
                "Sid": "EMRServerlessAccess",
                "Effect": "Allow",
                "Action": [
                    "emr-serverless:StartJobRun",
                    "emr-serverless:GetJobRun",
                    "emr-serverless:CancelJobRun",
                    "emr-serverless:ListJobRuns"
                ],
                "Resource": [
                    f"arn:aws:emr-serverless:{region}:{account_id}:/applications/*"
                ]
            },
            {
                "Sid": "IAMPassRole",
                "Effect": "Allow",
                "Action": "iam:PassRole",
                "Resource": [
                    f"arn:aws:iam::{account_id}:role/dev-spark-emr-execution-role",
                    f"arn:aws:iam::{account_id}:role/prod-spark-emr-execution-role"
                ],
                "Condition": {
                    "StringEquals": {
                        "iam:PassedToService": "emr-serverless.amazonaws.com"
                    }
                }
            },
            {
                "Sid": "CloudWatchLogs",
                "Effect": "Allow",
                "Action": [
                    "logs:StartQuery",
                    "logs:GetQueryResults",
                    "logs:FilterLogEvents"
                ],
                "Resource": [
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/lambda/*:*",
                    f"arn:aws:logs:{region}:{account_id}:log-group:/aws/emr-serverless/*:*"
                ]
            },
            {
                "Sid": "SecretsManagerAccess",
                "Effect": "Allow",
                "Action": [
                    "secretsmanager:GetSecretValue"
                ],
                "Resource": [
                    f"arn:aws:secretsmanager:{region}:{account_id}:secret:*"
                ]
            },
            {
                "Sid": "GlueCatalogAccess",
                "Effect": "Allow",
                "Action": [
                    "glue:GetDatabase",
                    "glue:GetTable",
                    "glue:GetPartitions",
                    "glue:GetDatabases",
                    "glue:GetTables"
                ],
                "Resource": "*"
            }
        ]
    }
    
    try:
        # Check if policy already exists
        try:
            existing_policy = iam_client.get_role_policy(
                RoleName=role_name,
                PolicyName='SparkAgentComprehensivePolicy'
            )
            print(f"ℹ️  Policy already exists, updating...")
        except iam_client.exceptions.NoSuchEntityException:
            print(f"ℹ️  Creating new policy...")
        
        # Put (create or update) the policy
        iam_client.put_role_policy(
            RoleName=role_name,
            PolicyName='SparkAgentComprehensivePolicy',
            PolicyDocument=json.dumps(policy_document)
        )
        
        print(f"✅ Successfully added comprehensive permissions to {role_name}")
        print("   ✓ Lambda invoke")
        print("   ✓ S3 read/write")
        print("   ✓ Agent-to-agent calls")
        print("   ✓ EMR Serverless")
        print("   ✓ CloudWatch Logs")
        print("   ✓ Secrets Manager")
        print("   ✓ Glue Catalog")
        
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
agent_arn = launch_result.agent_arn if hasattr(launch_result, 'agent_arn') else None

if agent_arn:
    config = load_config()
    if 'spark' not in config:
        config['spark'] = {}
    config['spark']['supervisor_arn'] = agent_arn
    save_config(config)
    print(f"\n✅ Spark Supervisor Agent deployed successfully!")
    print(f"ARN: {agent_arn}")
    print(f"✅ Updated config with Spark supervisor ARN: {agent_arn}")
else:
    print("\n⚠️ Could not retrieve agent ARN")
