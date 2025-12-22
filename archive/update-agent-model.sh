#!/bin/bash

# Update Spark Supervisor Agent with new model_id

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Update Agent Model to Claude Sonnet 4.5${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Model: us.anthropic.claude-sonnet-4-5-20250929-v1:0${NC}"
echo ""

# Get agent ARN from config
if [ -f "config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark_supervisor_arn' config/deployment-config.json 2>/dev/null)
    echo "Agent ARN: $AGENT_ARN"
else
    echo -e "${RED}❌ config/deployment-config.json not found${NC}"
    echo "Please provide the Spark Supervisor Agent ARN:"
    read AGENT_ARN
fi

if [ -z "$AGENT_ARN" ] || [ "$AGENT_ARN" == "null" ]; then
    echo -e "${RED}❌ No agent ARN found${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}The agent code has been updated with default model_id.${NC}"
echo -e "${YELLOW}You need to redeploy the agent for changes to take effect.${NC}"
echo ""
echo "To redeploy the agent:"
echo "1. Go to Bedrock AgentCore Console"
echo "2. Find agent: spark_supervisor_agent"
echo "3. Update the agent code with the modified spark_supervisor_agent.py"
echo "4. Or use the AWS CLI/SDK to update the agent"
echo ""
echo -e "${BLUE}Agent code location:${NC}"
echo "agent-code/spark-supervisor-agent/spark_supervisor_agent.py"
echo ""
echo -e "${GREEN}✅ Code updated with default model_id${NC}"
echo ""
