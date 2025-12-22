#!/bin/bash

# Check Gateway Status and Provide Next Steps

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Gateway Status Check${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get Gateway ID
echo -e "${YELLOW}Getting Gateway information...${NC}"
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text 2>/dev/null)

if [ -z "$GATEWAY_ID" ]; then
    echo -e "${RED}❌ Could not find Gateway ID${NC}"
    echo "Make sure the CloudFormation stack is deployed."
    exit 1
fi

echo -e "${GREEN}✅ Gateway found: $GATEWAY_ID${NC}"
echo ""

# Get Gateway details
echo -e "${YELLOW}Checking Gateway status...${NC}"
GATEWAY_INFO=$(aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$GATEWAY_INFO" | jq -e '.gateway' > /dev/null 2>&1; then
    GATEWAY_STATUS=$(echo "$GATEWAY_INFO" | jq -r '.gateway.status')
    GATEWAY_URL=$(echo "$GATEWAY_INFO" | jq -r '.gateway.gatewayUrl')
    
    echo -e "${GREEN}✅ Gateway Status: $GATEWAY_STATUS${NC}"
    echo "Gateway URL: $GATEWAY_URL"
else
    echo -e "${RED}❌ Could not get Gateway details${NC}"
    echo "$GATEWAY_INFO"
    exit 1
fi

echo ""

# List Gateway Targets
echo -e "${YELLOW}Checking Gateway Targets...${NC}"
TARGETS=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$TARGETS" | jq -e '.targets' > /dev/null 2>&1; then
    TARGET_COUNT=$(echo "$TARGETS" | jq '.targets | length')
    
    if [ "$TARGET_COUNT" -eq 0 ]; then
        echo -e "${YELLOW}⚠️  No Gateway Targets configured${NC}"
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}What This Means${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo "Your Gateway is deployed but has no targets."
        echo "Without targets, the Gateway cannot expose any tools via MCP."
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}Next Steps - Choose One${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo -e "${GREEN}Option 1: Add Target via AWS Console (Recommended)${NC}"
        echo ""
        echo "1. Open: https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
        echo "2. Click on gateway: $GATEWAY_ID"
        echo "3. Click 'Targets' tab → 'Add target'"
        echo "4. Configure:"
        echo "   - Name: spark-lambda-executor"
        echo "   - Type: Lambda"
        echo "   - Lambda ARN: (get from CloudFormation outputs)"
        echo "   - Credentials: None"
        echo "5. Wait for status: Available"
        echo ""
        echo -e "${GREEN}Option 2: Try Automated Script${NC}"
        echo ""
        echo "   cd scripts"
        echo "   ./add-gateway-target.sh"
        echo ""
        echo -e "${GREEN}Option 3: Use Direct Invocation (Works Now)${NC}"
        echo ""
        echo "   cd scripts"
        echo "   ./invoke-agent-directly.sh \"your prompt\""
        echo ""
    else
        echo -e "${GREEN}✅ Found $TARGET_COUNT Gateway Target(s)${NC}"
        echo ""
        echo "$TARGETS" | jq -r '.targets[] | "  - \(.name) (\(.status))"'
        echo ""
        echo -e "${BLUE}========================================${NC}"
        echo -e "${BLUE}Gateway is Ready!${NC}"
        echo -e "${BLUE}========================================${NC}"
        echo ""
        echo "Your Gateway has targets configured and is ready to use."
        echo ""
        echo -e "${GREEN}Test it:${NC}"
        echo "  cd scripts"
        echo "  ./list-gateway-tools.sh"
        echo "  ./ask-gateway.sh \"create a dataframe\""
        echo ""
        echo -e "${GREEN}Use as MCP endpoint:${NC}"
        echo "  Gateway URL: $GATEWAY_URL"
        echo "  Auth: Cognito JWT (ID token)"
        echo ""
    fi
else
    echo -e "${RED}❌ Could not list Gateway Targets${NC}"
    echo "$TARGETS"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Documentation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "See these files for more information:"
echo "  - CURRENT_STATUS.md           - Current state and next steps"
echo "  - WHY_NO_CLOUDFORMATION_TARGETS.md - Why targets aren't in CloudFormation"
echo "  - TESTING_GUIDE.md            - Complete testing guide"
echo ""
