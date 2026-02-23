#!/bin/bash

# Test Gateway with USER authentication (ID token)
# This is what the Gateway expects based on its JWT configuration

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gateway Test with User Token${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Step 1: Getting configuration...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)

echo -e "${GREEN}✅ Configuration retrieved${NC}"
echo "  User Pool ID: $USER_POOL_ID"
echo "  Client ID: $CLIENT_ID"
echo "  Gateway URL: $GATEWAY_URL"
echo ""

# Check if test user exists, if not create one
echo -e "${YELLOW}Step 2: Setting up test user...${NC}"
TEST_USER="gateway-test@example.com"
TEST_PASSWORD="TestPass123!"

# Try to create user (ignore if exists)
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_USER \
  --user-attributes Name=email,Value=$TEST_USER Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --region $REGION > /dev/null 2>&1

# Set password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $TEST_USER \
  --password "$TEST_PASSWORD" \
  --permanent \
  --region $REGION > /dev/null 2>&1

echo -e "${GREEN}✅ Test user ready: $TEST_USER${NC}"
echo ""

# Get ID token (this is what Gateway expects)
echo -e "${YELLOW}Step 3: Getting ID token...${NC}"

# Get client secret for SECRET_HASH calculation
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

# Calculate SECRET_HASH (required when client has a secret)
SECRET_HASH=$(echo -n "${TEST_USER}${CLIENT_ID}" | openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | base64)

AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$TEST_USER,PASSWORD=$TEST_PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json 2>&1)

if echo "$AUTH_RESPONSE" | jq -e '.AuthenticationResult.IdToken' > /dev/null 2>&1; then
    ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')
    echo -e "${GREEN}✅ ID token obtained${NC}"
    echo "  Token (first 30 chars): ${ID_TOKEN:0:30}..."
    
    # Decode and show token
    echo ""
    echo -e "${YELLOW}Token Claims:${NC}"
    echo "$ID_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.' || echo "Could not decode"
else
    echo -e "${RED}❌ Failed to get ID token${NC}"
    echo "$AUTH_RESPONSE"
    exit 1
fi
echo ""

# Save token
echo "$ID_TOKEN" > /tmp/gateway_id_token.txt
echo -e "${GREEN}Token saved to: /tmp/gateway_id_token.txt${NC}"
echo ""

# Test MCP request
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 4: Sending MCP Request${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

PROMPT=${1:-"what is 5+5"}
echo -e "${YELLOW}Prompt:${NC} $PROMPT"
echo ""

MCP_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "invoke_agent",
    "arguments": {
      "prompt": "$PROMPT"
    }
  }
}
EOF
)

echo -e "${YELLOW}Request:${NC}"
echo "$MCP_PAYLOAD" | jq '.'
echo ""

echo -e "${YELLOW}Sending to Gateway...${NC}"
RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$MCP_PAYLOAD")

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Response${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if echo "$RESPONSE" | jq -e '.error' > /dev/null 2>&1; then
    echo -e "${RED}❌ Error Response:${NC}"
    echo "$RESPONSE" | jq '.'
    
    ERROR_CODE=$(echo "$RESPONSE" | jq -r '.error.code')
    ERROR_MSG=$(echo "$RESPONSE" | jq -r '.error.message')
    
    echo ""
    echo -e "${YELLOW}Troubleshooting:${NC}"
    if [ "$ERROR_CODE" == "-32001" ]; then
        echo "  Error -32001: Invalid Bearer token"
        echo "  This means the Gateway rejected the token."
        echo ""
        echo "  Possible causes:"
        echo "  1. Token audience doesn't match Gateway configuration"
        echo "  2. Token issuer doesn't match"
        echo "  3. Token has expired"
        echo ""
        echo "  Token audience (aud): $(echo "$ID_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq -r '.aud')"
        echo "  Expected audience: $CLIENT_ID"
    fi
elif echo "$RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Success!${NC}"
    echo "$RESPONSE" | jq '.'
else
    echo -e "${YELLOW}⚠️  Unexpected response format:${NC}"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
fi

echo ""
echo -e "${GREEN}Test complete!${NC}"
