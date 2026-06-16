#!/bin/bash

# Replace Lambda target with Agent target
# This allows natural language queries instead of PySpark code

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Add Agent Target to Gateway${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text)

# Get agent ARN from config
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"
if [ -f "config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark_supervisor_arn' config/deployment-config.json 2>/dev/null || echo "$AGENT_ARN")
fi

echo "Gateway ID: $GATEWAY_ID"
echo "Agent ARN: $AGENT_ARN"
echo ""

# List current targets
echo -e "${YELLOW}Checking current targets...${NC}"
TARGETS=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region $REGION 2>&1)

if echo "$TARGETS" | jq -e '.items' > /dev/null 2>&1; then
    TARGET_COUNT=$(echo "$TARGETS" | jq '.items | length')
    echo "Found $TARGET_COUNT existing target(s)"
    
    if [ "$TARGET_COUNT" -gt 0 ]; then
        echo ""
        echo -e "${YELLOW}Current targets:${NC}"
        echo "$TARGETS" | jq -r '.items[] | "  - \(.name) (\(.targetId)) - \(.status)"'
        echo ""
        
        # Ask to remove old targets
        echo -e "${YELLOW}Removing existing targets...${NC}"
        echo "$TARGETS" | jq -r '.items[].targetId' | while read TARGET_ID; do
            echo "Deleting target: $TARGET_ID"
            aws bedrock-agentcore-control delete-gateway-target \
              --gateway-identifier $GATEWAY_ID \
              --target-id $TARGET_ID \
              --region $REGION > /dev/null 2>&1
        done
        
        echo -e "${GREEN}✅ Old targets removed${NC}"
        echo ""
        
        # Wait for deletion
        echo "Waiting 5 seconds for deletion to complete..."
        sleep 5
    fi
fi

# Add Agent target
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Adding Agent Target${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Creating Gateway Target for Spark Supervisor Agent..."
echo ""

# Try Agent target configuration
AGENT_TARGET_RESPONSE=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --name spark-agent \
  --description "Spark Supervisor Agent for natural language data processing queries" \
  --target-configuration "{\"agent\":{\"agentArn\":\"$AGENT_ARN\"}}" \
  --credential-provider-configurations '[{"credentialProviderType":"NONE"}]' \
  --region $REGION 2>&1)

if echo "$AGENT_TARGET_RESPONSE" | jq -e '.targetId' > /dev/null 2>&1; then
    TARGET_ID=$(echo "$AGENT_TARGET_RESPONSE" | jq -r '.targetId')
    echo -e "${GREEN}✅ Agent target created successfully!${NC}"
    echo "Target ID: $TARGET_ID"
    echo ""
    echo "This target accepts natural language queries."
    echo "The agent will convert them to PySpark code automatically."
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
    echo "Your Gateway now exposes the Spark Supervisor Agent."
    echo ""
    echo "Test it with natural language:"
    echo "  ./ask-gateway.sh \"create a dataframe with sample data\""
    echo "  ./ask-gateway.sh \"what is 5+5\""
    echo ""
    
    exit 0
else
    echo -e "${RED}❌ Agent target creation failed${NC}"
    echo ""
    echo "Error details:"
    echo "$AGENT_TARGET_RESPONSE" | jq '.' 2>/dev/null || echo "$AGENT_TARGET_RESPONSE"
    echo ""
    
    # Check if it's a schema issue
    if echo "$AGENT_TARGET_RESPONSE" | grep -q "agent"; then
        echo -e "${YELLOW}The 'agent' target type might not be supported in your region/CLI version.${NC}"
        echo ""
    fi
    
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Manual Configuration via AWS Console${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "1. Open AWS Console:"
    echo "   https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
    echo ""
    echo "2. Click on gateway: $GATEWAY_ID"
    echo ""
    echo "3. Click 'Targets' tab → 'Add target'"
    echo ""
    echo "4. Configure:"
    echo "   Name: spark-agent"
    echo "   Type: Agent (or Bedrock Agent)"
    echo "   Agent ARN: $AGENT_ARN"
    echo "   Credentials: None"
    echo ""
    echo "5. Click 'Add target'"
    echo ""
    
    exit 1
fi
