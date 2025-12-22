#!/bin/bash

# Simple script to send MCP requests to the Gateway
# Usage: ./send-mcp-request.sh "your prompt here"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

# Get prompt from argument or use default
PROMPT=${1:-"what is 5+5"}

echo -e "${BLUE}Sending MCP Request${NC}"
echo -e "${YELLOW}Prompt:${NC} $PROMPT"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)
TOKEN_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoTokenEndpoint`].OutputValue' --output text)
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)

# Get access token
echo -e "${YELLOW}Getting access token...${NC}"
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)
TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $AUTH_HEADER" \
  -d "grant_type=client_credentials" \
  -d "scope=spark-api/spark.execute")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

if [ -z "$ACCESS_TOKEN" ] || [ "$ACCESS_TOKEN" == "null" ]; then
    echo -e "${RED}❌ Failed to get access token${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Token obtained${NC}"
echo ""

# Send MCP request
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Sending Request to Gateway${NC}"
echo -e "${BLUE}========================================${NC}"
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

echo -e "${YELLOW}Sending to:${NC} $GATEWAY_URL"
echo ""

RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$MCP_PAYLOAD")

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Response${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
echo ""

# Also try direct invocation (non-MCP)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Alternative: Direct Invocation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

DIRECT_PAYLOAD=$(cat <<EOF
{
  "prompt": "$PROMPT",
  "execution_platform": "lambda"
}
EOF
)

echo -e "${YELLOW}Request:${NC}"
echo "$DIRECT_PAYLOAD" | jq '.'
echo ""

DIRECT_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/invoke" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$DIRECT_PAYLOAD")

echo -e "${YELLOW}Response:${NC}"
echo "$DIRECT_RESPONSE" | jq '.' 2>/dev/null || echo "$DIRECT_RESPONSE"
echo ""

echo -e "${GREEN}Done!${NC}"
