#!/bin/bash

# List available tools in the Gateway

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gateway Tools Discovery${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text)
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)

echo "Gateway ID: $GATEWAY_ID"
echo "Gateway URL: $GATEWAY_URL"
echo ""

# Get token
echo -e "${YELLOW}Getting authentication token...${NC}"
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client --user-pool-id $USER_POOL_ID --client-id $CLIENT_ID --query 'UserPoolClient.ClientSecret' --output text --region $REGION)
TEST_USER="gateway-test@example.com"
TEST_PASSWORD="TestPass123!"
aws cognito-idp admin-create-user --user-pool-id $USER_POOL_ID --username $TEST_USER --user-attributes Name=email,Value=$TEST_USER Name=email_verified,Value=true --message-action SUPPRESS --region $REGION > /dev/null 2>&1
aws cognito-idp admin-set-user-password --user-pool-id $USER_POOL_ID --username $TEST_USER --password "$TEST_PASSWORD" --permanent --region $REGION > /dev/null 2>&1
SECRET_HASH=$(echo -n "${TEST_USER}${CLIENT_ID}" | openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | base64)
ID_TOKEN=$(aws cognito-idp initiate-auth --auth-flow USER_PASSWORD_AUTH --client-id $CLIENT_ID --auth-parameters USERNAME=$TEST_USER,PASSWORD=$TEST_PASSWORD,SECRET_HASH=$SECRET_HASH --region $REGION --output json | jq -r '.AuthenticationResult.IdToken')

echo -e "${GREEN}✅ Token obtained${NC}"
echo ""

# List tools via MCP
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MCP tools/list Request${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

LIST_TOOLS_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }')

echo "Response:"
echo "$LIST_TOOLS_RESPONSE" | jq '.'
echo ""

# Check if tools exist
TOOL_COUNT=$(echo "$LIST_TOOLS_RESPONSE" | jq -r '.result.tools | length' 2>/dev/null)

if [ "$TOOL_COUNT" == "null" ] || [ "$TOOL_COUNT" == "0" ] || [ -z "$TOOL_COUNT" ]; then
    echo -e "${YELLOW}⚠️  No tools found in Gateway${NC}"
    echo ""
    echo "This means the Gateway doesn't have any Gateway Targets configured."
    echo ""
else
    echo -e "${GREEN}✅ Found $TOOL_COUNT tool(s)${NC}"
    echo ""
    echo "Available tools:"
    echo "$LIST_TOOLS_RESPONSE" | jq -r '.result.tools[] | "  - \(.name): \(.description)"'
    echo ""
fi

# List Gateway Targets via AWS API
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gateway Targets (AWS API)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TARGETS=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$TARGETS" | jq -e '.gatewaySummaries' > /dev/null 2>&1; then
    TARGET_COUNT=$(echo "$TARGETS" | jq '.gatewaySummaries | length')
    echo "Gateway Targets: $TARGET_COUNT"
    
    if [ "$TARGET_COUNT" -gt 0 ]; then
        echo ""
        echo "$TARGETS" | jq -r '.gatewaySummaries[] | "  - \(.name) (\(.targetId)): \(.status)"'
    else
        echo ""
        echo -e "${YELLOW}No Gateway Targets configured${NC}"
    fi
else
    echo -e "${RED}Could not list Gateway Targets${NC}"
    echo "$TARGETS"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

if [ "$TOOL_COUNT" == "null" ] || [ "$TOOL_COUNT" == "0" ] || [ -z "$TOOL_COUNT" ]; then
    echo -e "${YELLOW}The Gateway is deployed but has no tools configured.${NC}"
    echo ""
    echo "To use the Gateway, you need to add Gateway Targets."
    echo ""
    echo -e "${YELLOW}Options:${NC}"
    echo ""
    echo "1. Add Gateway Target via AWS Console:"
    echo "   - Go to: AWS Console → Bedrock → AgentCore → Gateways"
    echo "   - Select your gateway: $GATEWAY_ID"
    echo "   - Click 'Add target'"
    echo ""
    echo "2. Add Gateway Target via CLI:"
    echo "   aws bedrock-agentcore-control create-gateway-target \\"
    echo "     --gateway-identifier $GATEWAY_ID \\"
    echo "     --name my-target \\"
    echo "     --target-configuration '{...}'"
    echo ""
    echo "3. Invoke Spark Supervisor Agent directly (bypass Gateway):"
    echo "   aws bedrock-agentcore-runtime invoke-agent \\"
    echo "     --agent-id <agent-id> \\"
    echo "     --input-text 'your prompt'"
    echo ""
else
    echo -e "${GREEN}✅ Gateway has tools configured and ready to use!${NC}"
    echo ""
    echo "Use these tool names in your requests:"
    echo "$LIST_TOOLS_RESPONSE" | jq -r '.result.tools[] | "  - \(.name)"'
fi

echo ""
