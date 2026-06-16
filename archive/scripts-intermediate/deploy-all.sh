#!/bin/bash

# Master Deployment Script
# Deploys the complete Spark Code Interpreter system in the correct order:
# 1. Infrastructure (CloudFormation stack + Lambda)
# 2. AgentCore agents (Spark Supervisor + Code Generation)

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to the parent directory (us-east-1-stable)
cd "$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Spark Code Interpreter${NC}"
echo -e "${BLUE}Master Deployment Script${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "This script will deploy the complete system in the following order:"
echo "  1. Infrastructure (CloudFormation + Spark Lambda)"
echo "  2. AgentCore Agents (Spark Supervisor + Code Generation)"
echo "  3. Backend API (FastAPI Lambda + ALB integration)"
echo ""
echo -e "${YELLOW}Press Ctrl+C to cancel, or Enter to continue...${NC}"
read

# Step 1: Deploy infrastructure
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 1: Deploying Infrastructure${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

./scripts/deploy-complete-stack.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Infrastructure deployment failed${NC}"
    echo "Please fix the errors and try again"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Infrastructure deployment completed successfully${NC}"
echo ""
echo -e "${YELLOW}Waiting 10 seconds before deploying agents...${NC}"
sleep 10

# Step 2: Deploy agents
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 2: Deploying AgentCore Agents${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

./scripts/deploy-agents.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Agent deployment failed${NC}"
    echo "Infrastructure is deployed, but agents need to be deployed manually"
    echo "Run: ./scripts/deploy-agents.sh"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Agent deployment completed successfully${NC}"
echo ""
echo -e "${YELLOW}Waiting 10 seconds before deploying backend...${NC}"
sleep 10

# Step 3: Deploy backend
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}STEP 3: Deploying Backend API${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

./scripts/deploy-backend.sh

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Backend deployment failed${NC}"
    echo "Infrastructure and agents are deployed, but backend needs to be deployed manually"
    echo "Run: ./scripts/deploy-backend.sh"
    exit 1
fi

echo ""
echo -e "${GREEN}✅ Backend deployment completed successfully${NC}"
echo ""

# Final summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${GREEN}All components have been deployed successfully:${NC}"
echo "  ✅ CloudFormation Stack"
echo "  ✅ S3 Bucket"
echo "  ✅ Spark Lambda Function (with actual Spark code)"
echo "  ✅ EMR Serverless Application"
echo "  ✅ Application Load Balancer"
echo "  ✅ Spark Supervisor Agent"
echo "  ✅ Code Generation Agent"
echo "  ✅ Backend API (ECS Fargate)"
echo ""

# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name ${ENVIRONMENT}-spark-complete-stack \
    --region ${REGION:-us-east-1} \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
    --output text 2>/dev/null)

# Display configuration
if [ -f "config/deployment-config.json" ]; then
    echo -e "${YELLOW}Deployment Configuration:${NC}"
    cat config/deployment-config.json | python3 -m json.tool 2>/dev/null || cat config/deployment-config.json
    echo ""
fi

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}🌐 API Endpoint${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${GREEN}Your Spark Code Interpreter API is live at:${NC}"
echo -e "${GREEN}${ALB_URL}${NC}"
echo ""
echo -e "${YELLOW}Quick Test:${NC}"
echo "  curl ${ALB_URL}/health"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Test the deployment: ./scripts/test-deployment.sh"
echo "2. Access the API at: ${ALB_URL}"
echo "3. Try the /spark/generate endpoint for code generation"
echo ""
echo -e "${GREEN}Happy coding with Spark! 🚀${NC}"
echo ""
