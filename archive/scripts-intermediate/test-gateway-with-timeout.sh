#!/bin/bash
# Test Gateway with extended timeout
# Usage: ./test-gateway-with-timeout.sh "your prompt"

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"
PROMPT=${1:-"what is 5+5"}

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Gateway with Extended Timeout${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get config
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)

echo "Gateway URL: $GATEWAY_URL"
echo "Prompt: $PROMPT"
echo ""

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
echo -e "${YELLOW}Getting authentication token...${NC}"
ID_TOKEN=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$TEST_USER,PASSWORD=$TEST_PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json | jq -r '.AuthenticationResult.IdToken')

if [ -z "$ID_TOKEN" ] || [ "$ID_TOKEN" == "null" ]; then
    echo -e "${RED}Error: Failed to get ID token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token obtained${NC}"
echo ""

# Send request with extended timeout (120 seconds)
echo -e "${YELLOW}Sending request to Gateway...${NC}"
echo "Question: $PROMPT"
echo ""
echo -e "${YELLOW}⏱️  This may take up to 60 seconds...${NC}"
echo ""

START_TIME=$(date +%s)

curl -s --max-time 120 -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"tools/call\",\"params\":{\"name\":\"spark-agent___ask_agent\",\"arguments\":{\"prompt\":\"$PROMPT\"}}}" | jq '.'

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Response Time: ${DURATION} seconds${NC}"
echo -e "${BLUE}========================================${NC}"
