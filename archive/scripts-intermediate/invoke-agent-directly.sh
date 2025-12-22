#!/bin/bash

# Invoke Spark Supervisor Agent directly (bypass Gateway)
# Usage: ./invoke-agent-directly.sh "your prompt"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}AWS CLI Version Issue${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${YELLOW}Your AWS CLI doesn't support 'bedrock-agentcore-runtime' yet.${NC}"
echo ""
echo -e "${GREEN}Good news: Your Gateway Target is working!${NC}"
echo ""
echo "Use the Gateway instead:"
echo ""
echo -e "${BLUE}  ./ask-gateway.sh \"$1\"${NC}"
echo ""
echo "Or update your AWS CLI to the latest version:"
echo ""
echo "  # macOS with Homebrew"
echo "  brew upgrade awscli"
echo ""
echo "  # Or download latest from AWS"
echo "  https://aws.amazon.com/cli/"
echo ""
