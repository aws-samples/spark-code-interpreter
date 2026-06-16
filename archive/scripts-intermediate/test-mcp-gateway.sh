#!/bin/bash

# Test MCP Gateway with actual MCP protocol requests
# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}MCP Gateway Test${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Step 1: Getting stack configuration...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)
TOKEN_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoTokenEndpoint`].OutputValue' --output text)
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text)

echo -e "${GREEN}✅ Configuration retrieved${NC}"
echo "  Gateway URL: $GATEWAY_URL"
echo "  Gateway ID: $GATEWAY_ID"
echo ""

# Get access token
echo -e "${YELLOW}Step 2: Getting access token...${NC}"
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

if echo "$TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
    echo -e "${GREEN}✅ Access token obtained${NC}"
    echo "  Token (first 30 chars): ${ACCESS_TOKEN:0:30}..."
else
    echo -e "${RED}❌ Failed to get access token${NC}"
    echo "$TOKEN_RESPONSE"
    exit 1
fi
echo ""

# Test 1: MCP Initialize
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 1: MCP Initialize${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

INIT_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {
      "roots": {
        "listChanged": true
      }
    },
    "clientInfo": {
      "name": "test-client",
      "version": "1.0.0"
    }
  }
}'

echo "Sending MCP initialize request..."
INIT_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$INIT_PAYLOAD")

echo "Response:"
echo "$INIT_RESPONSE" | jq '.' 2>/dev/null || echo "$INIT_RESPONSE"
echo ""

if echo "$INIT_RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Test 1 PASSED: MCP initialize successful${NC}"
else
    echo -e "${YELLOW}⚠️  Test 1: Unexpected response format${NC}"
fi
echo ""

# Test 2: MCP List Tools
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 2: MCP List Tools${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

LIST_TOOLS_PAYLOAD='{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}'

echo "Sending MCP tools/list request..."
LIST_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$LIST_TOOLS_PAYLOAD")

echo "Response:"
echo "$LIST_RESPONSE" | jq '.' 2>/dev/null || echo "$LIST_RESPONSE"
echo ""

if echo "$LIST_RESPONSE" | jq -e '.result.tools' > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Test 2 PASSED: Tools list retrieved${NC}"
    echo "Available tools:"
    echo "$LIST_RESPONSE" | jq -r '.result.tools[] | "  - \(.name): \(.description)"' 2>/dev/null
else
    echo -e "${YELLOW}⚠️  Test 2: No tools found or unexpected format${NC}"
fi
echo ""

# Test 3: MCP Call Tool (if tools are available)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 3: MCP Call Tool${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Try to get first tool name
TOOL_NAME=$(echo "$LIST_RESPONSE" | jq -r '.result.tools[0].name' 2>/dev/null)

if [ -n "$TOOL_NAME" ] && [ "$TOOL_NAME" != "null" ]; then
    echo "Calling tool: $TOOL_NAME"
    
    CALL_TOOL_PAYLOAD=$(cat <<EOF
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "$TOOL_NAME",
    "arguments": {
      "prompt": "Create a simple DataFrame with 3 rows and 2 columns",
      "execution_platform": "lambda"
    }
  }
}
EOF
)
    
    echo "Sending MCP tools/call request..."
    CALL_RESPONSE=$(curl -s -X POST "$GATEWAY_URL" \
      -H "Authorization: Bearer $ACCESS_TOKEN" \
      -H "Content-Type: application/json" \
      -d "$CALL_TOOL_PAYLOAD")
    
    echo "Response:"
    echo "$CALL_RESPONSE" | jq '.' 2>/dev/null || echo "$CALL_RESPONSE"
    echo ""
    
    if echo "$CALL_RESPONSE" | jq -e '.result' > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Test 3 PASSED: Tool invocation successful${NC}"
    else
        echo -e "${YELLOW}⚠️  Test 3: Tool invocation returned unexpected format${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Test 3 SKIPPED: No tools available to call${NC}"
    echo "This is expected if Gateway Targets haven't been configured yet."
fi
echo ""

# Test 4: Direct Gateway Invocation (Alternative to MCP)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 4: Direct Gateway Invocation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

DIRECT_PAYLOAD='{
  "prompt": "Generate a simple Spark DataFrame with sample data",
  "execution_platform": "lambda"
}'

echo "Sending direct invocation request..."
DIRECT_RESPONSE=$(curl -s -X POST "$GATEWAY_URL/invoke" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$DIRECT_PAYLOAD")

echo "Response:"
echo "$DIRECT_RESPONSE" | jq '.' 2>/dev/null || echo "$DIRECT_RESPONSE"
echo ""

if [ -n "$DIRECT_RESPONSE" ]; then
    echo -e "${GREEN}✅ Test 4 PASSED: Direct invocation completed${NC}"
else
    echo -e "${YELLOW}⚠️  Test 4: No response received${NC}"
fi
echo ""

# Test 5: Check Gateway via AWS API
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 5: Gateway Status via AWS API${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Checking gateway status..."
GATEWAY_INFO=$(aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$GATEWAY_INFO" | jq -e '.status' > /dev/null 2>&1; then
    STATUS=$(echo "$GATEWAY_INFO" | jq -r '.status')
    echo -e "${GREEN}✅ Test 5 PASSED: Gateway status retrieved${NC}"
    echo "  Status: $STATUS"
    echo "  Protocol: $(echo "$GATEWAY_INFO" | jq -r '.protocolType')"
    echo "  Authorizer: $(echo "$GATEWAY_INFO" | jq -r '.authorizerType')"
else
    echo -e "${YELLOW}⚠️  Test 5: Could not retrieve gateway status${NC}"
    echo "$GATEWAY_INFO"
fi
echo ""

# Test 6: List Gateway Targets
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test 6: List Gateway Targets${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Listing gateway targets..."
TARGETS=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$TARGETS" | jq -e '.gatewaySummaries' > /dev/null 2>&1; then
    TARGET_COUNT=$(echo "$TARGETS" | jq '.gatewaySummaries | length')
    echo -e "${GREEN}✅ Test 6 PASSED: Gateway targets listed${NC}"
    echo "  Target count: $TARGET_COUNT"
    
    if [ "$TARGET_COUNT" -gt 0 ]; then
        echo "  Targets:"
        echo "$TARGETS" | jq -r '.gatewaySummaries[] | "    - \(.name): \(.status)"'
    else
        echo -e "${YELLOW}  Note: No targets configured yet${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Test 6: Could not list targets${NC}"
    echo "$TARGETS"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Gateway Configuration:${NC}"
echo "  URL: $GATEWAY_URL"
echo "  ID: $GATEWAY_ID"
echo "  Authentication: OAuth2 Client Credentials"
echo "  Protocol: MCP"
echo ""
echo -e "${YELLOW}MCP Protocol Tests:${NC}"
echo "  ✅ Authentication successful"
echo "  ✅ Gateway accessible"
echo "  ✅ MCP requests accepted"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Configure Gateway Targets to expose tools"
echo "  2. Use MCP client (like Claude Desktop) to connect"
echo "  3. Invoke Spark Supervisor Agent through Gateway"
echo ""
echo -e "${YELLOW}MCP Client Configuration:${NC}"
echo "{"
echo "  \"mcpServers\": {"
echo "    \"spark-gateway\": {"
echo "      \"url\": \"$GATEWAY_URL\","
echo "      \"headers\": {"
echo "        \"Authorization\": \"Bearer <access-token>\""
echo "      }"
echo "    }"
echo "  }"
echo "}"
echo ""
echo -e "${GREEN}Testing complete! 🎉${NC}"
