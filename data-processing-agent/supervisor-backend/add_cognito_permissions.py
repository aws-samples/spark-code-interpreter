"""Add Cognito permissions to supervisor agent execution role"""

import boto3
import json

ROLE_NAME = "AmazonBedrockAgentCoreSDKRuntime-us-east-1-5130eca7b1"
POLICY_NAME = "CognitoGatewayAccess"

policy_document = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:DescribeUserPoolClient"
            ],
            "Resource": "arn:aws:cognito-idp:us-east-1:260005718447:userpool/us-east-1_XubTBv9c6"
        }
    ]
}

iam = boto3.client('iam')

try:
    response = iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=json.dumps(policy_document)
    )
    print(f"✅ Added Cognito permissions to role: {ROLE_NAME}")
    print(f"   Policy: {POLICY_NAME}")
except Exception as e:
    print(f"❌ Error: {e}")
