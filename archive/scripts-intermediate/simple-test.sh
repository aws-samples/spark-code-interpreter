#!/bin/bash

# Simple example: Send "what is 5+5" to the Gateway
# Uses USER authentication (ID token) which is what the Gateway expects

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo "=== Simple Gateway Test ==="
echo ""

# 1. Get Gateway URL and credentials
echo "1. Getting configuration..."
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)

echo "   Gateway URL: $GATEWAY_URL"
echo ""

# 2. Create test user
echo "2. Setting up test user..."
TEST_USER="gateway-test@example.com"
TEST_PASSWORD="TestPass123!"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_USER \
  --user-attributes Name=email,Value=$TEST_USER Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --region $REGION > /dev/null 2>&1

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_USER \
  --password "$TEST_PASSWORD" \
  --permanent \
  --region $REGION > /dev/null 2>&1

echo "   User: $TEST_USER"
echo ""

# 3. Get ID token (not access token!)
echo "3. Getting ID token..."

# Get client secret for SECRET_HASH
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

# Calculate SECRET_HASH
SECRET_HASH=$(echo -n "${TEST_USER}${CLIENT_ID}" | openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | base64)

AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$TEST_USER,PASSWORD=$TEST_PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json)

ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')

echo "   Token: ${ID_TOKEN:0:30}..."
echo ""

# 4. Send request: "what is 5+5"
echo "4. Sending request: 'what is 5+5'"
echo ""

curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "invoke_agent",
      "arguments": {
        "prompt": "what is 5+5"
      }
    }
  }' | jq '.'

echo ""
echo "=== Test Complete ==="
