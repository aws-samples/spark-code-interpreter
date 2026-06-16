#!/bin/bash

# Redeploy both Spark Supervisor Agent and Wrapper Lambda with Claude Sonnet 4.5

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Redeploy with Claude Sonnet 4.5${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0"
echo ""

# Check if bedrock-agentcore CLI is installed
if ! command -v bedrock-agentcore &> /dev/null; then
    echo -e "${RED}❌ bedrock-agentcore CLI not found${NC}"
    echo ""
    echo "Please install it first:"
    echo "  pip install bedrock-agentcore"
    echo ""
    echo "Or deploy the agent manually via AWS Console"
    exit 1
fi

# Step 1: Deploy Spark Supervisor Agent
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Deploy Spark Supervisor Agent${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/agent-code/spark-supervisor-agent"

echo -e "${YELLOW}Deploying agent with bedrock-agentcore CLI...${NC}"
bedrock-agentcore deploy

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Agent deployment failed${NC}"
    echo ""
    echo "You can deploy manually:"
    echo "1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/agents"
    echo "2. Find: spark_supervisor_agent"
    echo "3. Update the code with: agent-code/spark-supervisor-agent/spark_supervisor_agent.py"
    echo ""
    exit 1
fi

echo -e "${GREEN}✅ Agent deployed${NC}"
echo ""

# Get the agent ARN
if [ -f "get_arn.py" ]; then
    echo -e "${YELLOW}Getting agent ARN...${NC}"
    AGENT_ARN=$(python3 get_arn.py 2>/dev/null | grep "arn:aws:bedrock-agentcore" | tail -1)
    if [ ! -z "$AGENT_ARN" ]; then
        echo "Agent ARN: $AGENT_ARN"
        
        # Save to config
        mkdir -p "$PROJECT_ROOT/config"
        if [ -f "$PROJECT_ROOT/config/deployment-config.json" ]; then
            # Update existing config
            jq --arg arn "$AGENT_ARN" '.spark_supervisor_arn = $arn' \
                "$PROJECT_ROOT/config/deployment-config.json" > /tmp/config.json
            mv /tmp/config.json "$PROJECT_ROOT/config/deployment-config.json"
        else
            # Create new config
            echo "{\"spark_supervisor_arn\": \"$AGENT_ARN\"}" > "$PROJECT_ROOT/config/deployment-config.json"
        fi
        echo -e "${GREEN}✅ ARN saved to config${NC}"
    fi
fi

echo ""

# Step 2: Deploy Wrapper Lambda
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Deploy Wrapper Lambda${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"

echo -e "${YELLOW}Creating deployment package...${NC}"
zip -j /tmp/agent_wrapper_sonnet45.zip agent-wrapper/agent_wrapper.py > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Failed to create zip${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Package created${NC}"
echo ""

echo -e "${YELLOW}Updating Lambda function...${NC}"
aws lambda update-function-code \
  --function-name dev-spark-agent-wrapper \
  --zip-file fileb:///tmp/agent_wrapper_sonnet45.zip \
  --region us-east-1 \
  --query 'FunctionArn' \
  --output text

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lambda update failed${NC}"
    echo "Check your AWS credentials"
    exit 1
fi

echo -e "${GREEN}✅ Lambda updated${NC}"
echo ""

# Cleanup
rm -f /tmp/agent_wrapper_sonnet45.zip

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Both components updated with Claude Sonnet 4.5:"
echo "  ✅ Spark Supervisor Agent"
echo "  ✅ Wrapper Lambda"
echo ""
echo "Test with:"
echo "  ./scripts/test-calculation.sh \"what is 7*10\""
echo ""
echo "Or via AWS Console:"
echo "  Lambda: dev-spark-agent-wrapper"
echo "  Payload: {\"prompt\":\"what is 7*10\"}"
echo ""
