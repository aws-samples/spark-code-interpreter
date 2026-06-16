#!/bin/bash

# Add Agent as MCP Server target
# This exposes the agent through the Gateway's MCP protocol

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Add Agent as MCP Target${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text)
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text)

# Get agent ARN from config
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"
if [ -f "config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark_supervisor_arn' config/deployment-config.json 2>/dev/null || echo "$AGENT_ARN")
fi

# Extract agent ID from ARN
AGENT_ID=$(echo $AGENT_ARN | awk -F'/' '{print $NF}')

echo "Gateway ID: $GATEWAY_ID"
echo "Gateway URL: $GATEWAY_URL"
echo "Agent ARN: $AGENT_ARN"
echo "Agent ID: $AGENT_ID"
echo ""

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Important Discovery${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo "Gateway Targets only support 'mcp' configuration type."
echo "Direct 'agent' targets are not supported via the API."
echo ""
echo "However, Bedrock Agents can expose themselves as MCP servers!"
echo ""
echo -e "${BLUE}Solution: Use the Agent's MCP endpoint${NC}"
echo ""
echo "Agents in Bedrock AgentCore have built-in MCP endpoints at:"
echo "  https://<agent-id>.agent.bedrock-agentcore.<region>.amazonaws.com/mcp"
echo ""
echo "For your agent:"
echo "  https://${AGENT_ID}.agent.bedrock-agentcore.us-east-1.amazonaws.com/mcp"
echo ""

# Try to add agent as MCP server target
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Adding Agent MCP Target${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

AGENT_MCP_ENDPOINT="https://${AGENT_ID}.agent.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

echo "Creating Gateway Target for Agent MCP endpoint..."
echo "Endpoint: $AGENT_MCP_ENDPOINT"
echo ""

MCP_TARGET_RESPONSE=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --name spark-agent \
  --description "Spark Supervisor Agent via MCP for natural language queries" \
  --target-configuration "{\"mcp\":{\"mcpServer\":{\"endpoint\":\"$AGENT_MCP_ENDPOINT\"}}}" \
  --credential-provider-configurations '[{"credentialProviderType":"GATEWAY_IAM_ROLE"}]' \
  --region $REGION 2>&1)

if echo "$MCP_TARGET_RESPONSE" | jq -e '.targetId' > /dev/null 2>&1; then
    TARGET_ID=$(echo "$MCP_TARGET_RESPONSE" | jq -r '.targetId')
    echo -e "${GREEN}✅ Agent MCP target created successfully!${NC}"
    echo "Target ID: $TARGET_ID"
    echo ""
    
    # Wait for target to be ready
    echo -e "${YELLOW}Waiting for target to be ready...${NC}"
    sleep 10
    
    # List tools
    echo ""
    cd $(dirname $0)
    ./list-gateway-tools.sh
    
    echo ""
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}Success!${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    echo "Your Gateway now connects to the Spark Supervisor Agent via MCP."
    echo ""
    echo "Test it:"
    echo "  ./ask-gateway.sh \"what is 5+5\""
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ MCP target creation failed${NC}"
    echo ""
    echo "Error details:"
    echo "$MCP_TARGET_RESPONSE" | jq '.' 2>/dev/null || echo "$MCP_TARGET_RESPONSE"
    echo ""
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Alternative: Manual Console Configuration${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Try adding via AWS Console:"
    echo ""
    echo "1. Open: https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
    echo "2. Click gateway: $GATEWAY_ID"
    echo "3. Targets tab → Add target"
    echo "4. Configure:"
    echo "   Name: spark-agent"
    echo "   Type: MCP Server"
    echo "   Endpoint: $AGENT_MCP_ENDPOINT"
    echo "   Credentials: None (or IAM if required)"
    echo ""
    
    exit 1
fi
