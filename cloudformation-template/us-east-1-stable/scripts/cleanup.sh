#!/bin/bash

# Cleanup Script - Remove all Spark Code Interpreter resources

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REGION="us-east-1"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Spark Code Interpreter - Cleanup${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${RED}WARNING: This will delete all resources!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""

# Get S3 bucket name
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`SparkDataBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$S3_BUCKET" ]; then
    echo -e "${YELLOW}Emptying S3 bucket: $S3_BUCKET${NC}"
    aws s3 rm s3://$S3_BUCKET --recursive --region $REGION || true
    echo -e "${GREEN}✅ S3 bucket emptied${NC}"
fi

# Delete CloudFormation stack
echo -e "${YELLOW}Deleting CloudFormation stack: $STACK_NAME${NC}"
aws cloudformation delete-stack \
  --stack-name $STACK_NAME \
  --region $REGION || true

echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name $STACK_NAME \
  --region $REGION || true

echo -e "${GREEN}✅ CloudFormation stack deleted${NC}"

# Delete AgentCore agents (manual step)
echo ""
echo -e "${YELLOW}Manual cleanup required for AgentCore agents:${NC}"
echo "1. List agents:"
echo "   aws bedrock-agentcore list-runtimes --region $REGION"
echo ""
echo "2. Delete each agent:"
echo "   bedrock-agentcore delete --agent-id <AGENT_ID> --region $REGION"
echo ""

# Delete S3 bucket
if [ -n "$S3_BUCKET" ]; then
    echo -e "${YELLOW}Deleting S3 bucket: $S3_BUCKET${NC}"
    aws s3 rb s3://$S3_BUCKET --force --region $REGION || true
    echo -e "${GREEN}✅ S3 bucket deleted${NC}"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Cleanup Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "All resources have been removed."
echo "Don't forget to manually delete AgentCore agents if needed."
