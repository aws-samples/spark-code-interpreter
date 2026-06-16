#!/bin/bash

# Deploy Spark Supervisor Agent using Python script

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy Spark Supervisor Agent${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT/agent-code/spark-supervisor-agent"

echo -e "${YELLOW}Deploying agent with Python script...${NC}"
echo ""

python3 agent_deployment.py

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}❌ Deployment failed${NC}"
    echo ""
    echo "Troubleshooting:"
    echo "1. Check if bedrock_agentcore_starter_toolkit is installed:"
    echo "   pip3 install bedrock-agentcore-starter-toolkit"
    echo ""
    echo "2. Check AWS credentials are valid"
    echo ""
    echo "3. Check you have permissions for Bedrock AgentCore"
    exit 1
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get the ARN from config
if [ -f "$PROJECT_ROOT/config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark.supervisor_arn' "$PROJECT_ROOT/config/deployment-config.json" 2>/dev/null)
    if [ ! -z "$AGENT_ARN" ] && [ "$AGENT_ARN" != "null" ]; then
        echo "Agent ARN: $AGENT_ARN"
        echo ""
    fi
fi

echo "Next steps:"
echo "1. Deploy wrapper Lambda: ./scripts/deploy-agent-wrapper.sh"
echo "2. Test: ./scripts/test-calculation.sh \"what is 7*10\""
echo ""
