#!/bin/bash
# Simple script to ask the Gateway a question
# Usage: ./ask-gateway.sh "what is 5+5"

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"
PROMPT=${1:-"what is 5+5"}

# Get config
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)

# Get client secret
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

# Setup user
TEST_USER="gateway-test@example.com"
TEST_PASSWORD="TestPass123!"
aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username $TEST_USER --user-attributes Name=email,Value=$TEST_USER Name=email_verified,Value=true --message-action SUPPRESS --region $REGION > /dev/null 2>&1
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username $TEST_USER --password "$TEST_PASSWORD" --permanent --region $REGION > /dev/null 2>&1

# Calculate SECRET_HASH
SECRET_HASH=$(echo -n "${TEST_USER}${CLIENT_ID}" | openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | base64)

# Get token with SECRET_HASH
ID_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$TEST_USER,PASSWORD=$TEST_PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json | jq -r '.AuthenticationResult.IdToken')

if [ -z "$ID_TOKEN" ] || [ "$ID_TOKEN" == "null" ]; then
    echo "Error: Failed to get ID token"
    exit 1
fi

# Send request - Now using wrapper Lambda that accepts natural language
echo "Question: $PROMPT"
echo ""

curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"spark-agent___ask_agent\",\"arguments\":{\"prompt\":\"$PROMPT\"}}}" | jq '.'
