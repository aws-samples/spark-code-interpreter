#!/bin/bash

# Deploy AgentCore Agents Script
# Deploys both Spark Supervisor and Code Generation agents

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to the parent directory (us-east-1-stable)
cd "$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}AgentCore Agents Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Check if bedrock-agentcore-starter-toolkit is installed
echo -e "${YELLOW}Checking prerequisites...${NC}"
if ! python3 -c "import bedrock_agentcore_starter_toolkit" 2>/dev/null; then
    echo -e "${YELLOW}bedrock-agentcore-starter-toolkit not found. Installing...${NC}"
    pip3 install bedrock-agentcore-starter-toolkit
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Failed to install bedrock-agentcore-starter-toolkit${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ bedrock-agentcore-starter-toolkit installed${NC}"
else
    echo -e "${GREEN}✅ bedrock-agentcore-starter-toolkit already installed${NC}"
fi
echo ""

# Create a simple config helper module with unique name
CONFIG_DIR="agent-code"
cat > $CONFIG_DIR/deployment_config_helper.py <<'EOF'
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'deployment-config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
EOF

echo -e "${GREEN}✅ Config helper created${NC}"
echo ""

# Deploy Spark Supervisor Agent
echo -e "${YELLOW}Deploying Spark Supervisor Agent...${NC}"
cd agent-code/spark-supervisor-agent

# Clean up stale agent ID from config
if [ -f ".bedrock_agentcore.yaml" ]; then
    echo "Cleaning up stale agent configuration..."
    # Remove agent_id and agent_arn lines to force fresh deployment
    sed -i.bak '/agent_id:/d' .bedrock_agentcore.yaml
    sed -i.bak '/agent_arn:/d' .bedrock_agentcore.yaml
fi

python3 agent_deployment.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Spark Supervisor Agent deployed${NC}"
else
    echo -e "${RED}❌ Spark Supervisor Agent deployment failed${NC}"
    exit 1
fi
echo ""

# Deploy Code Generation Agent
echo -e "${YELLOW}Deploying Code Generation Agent...${NC}"
cd ../code-generation-agent

# Clean up stale agent ID from config
if [ -f ".bedrock_agentcore.yaml" ]; then
    echo "Cleaning up stale agent configuration..."
    # Remove agent_id and agent_arn lines to force fresh deployment
    sed -i.bak '/agent_id:/d' .bedrock_agentcore.yaml
    sed -i.bak '/agent_arn:/d' .bedrock_agentcore.yaml
fi

python3 agent_deployment.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Code Generation Agent deployed${NC}"
else
    echo -e "${RED}❌ Code Generation Agent deployment failed${NC}"
    exit 1
fi
echo ""

cd ../../scripts

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Agent Deployment Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Both agents have been deployed successfully!"
echo "Agent ARNs have been saved to: ../config/deployment-config.json"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Verify agent ARNs in the config file"
echo "2. Deploy backend Lambda function with agent ARNs"
echo "3. Test the complete system"
echo ""
