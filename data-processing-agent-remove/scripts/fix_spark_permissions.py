#!/usr/bin/env python3
"""Add Lambda invoke permissions to Spark supervisor agent role"""

import boto3
import json

# Get the agent's execution role
iam = boto3.client('iam', region_name='us-east-1')

# The role name from the error message
role_name = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-976e96fdb5"

# Policy to allow Lambda invocation
policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "lambda:InvokeFunction",
            "Resource": "arn:aws:lambda:us-east-1:260005718447:function:sparkOnLambda-spark-code-interpreter"
        }
    ]
}

policy_name = "SparkLambdaInvokePolicy"

try:
    # Create inline policy
    iam.put_role_policy(
        RoleName=role_name,
        PolicyName=policy_name,
        PolicyDocument=json.dumps(policy_document)
    )
    print(f"✅ Successfully added Lambda invoke permission to role: {role_name}")
    print(f"   Policy: {policy_name}")
    print(f"   Lambda function: sparkOnLambda-spark-code-interpreter")
except Exception as e:
    print(f"❌ Error: {e}")
