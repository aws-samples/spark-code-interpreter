#!/bin/bash

# Add EMR permissions to the Bedrock AgentCore execution role

ROLE_NAME="AmazonBedrockAgentCoreSDKRuntime-us-east-1-976e96fdb5"
POLICY_NAME="EMRServerlessStartJobPolicy"

echo "Adding EMR permissions to role: $ROLE_NAME"

# Create the policy document
cat > /tmp/emr-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "emr-serverless:StartJobRun",
        "emr-serverless:GetJobRun",
        "emr-serverless:CancelJobRun",
        "emr-serverless:ListJobRuns"
      ],
      "Resource": "arn:aws:emr-serverless:us-east-1:817323390093:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PassRole"
      ],
      "Resource": "arn:aws:iam::817323390093:role/dev-spark-emr-execution-role"
    }
  ]
}
EOF

# Add the policy to the role
aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "$POLICY_NAME" \
  --policy-document file:///tmp/emr-policy.json

if [ $? -eq 0 ]; then
    echo "✅ EMR permissions added successfully"
else
    echo "❌ Failed to add EMR permissions"
    exit 1
fi

# Clean up
rm /tmp/emr-policy.json

echo "Done!"
