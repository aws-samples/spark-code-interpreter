#!/bin/bash
set -e

# Configuration
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo "🚀 AgentCore Gateway Deployment"
echo "   Region: $REGION"
echo "   Environment: $ENVIRONMENT"
echo ""

echo "ℹ️  Note: AgentCore Gateway is managed by AWS and deployed via CloudFormation."
echo "   No Docker image or Lambda deployment needed!"
echo ""

# Get Gateway information from CloudFormation
echo "📋 Getting Gateway information..."

GATEWAY_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
    --output text 2>/dev/null || echo "")

GATEWAY_HTTP_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

GATEWAY_MCP_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayMcpUrl`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$GATEWAY_ID" ]; then
    echo "❌ Gateway not found in CloudFormation stack"
    echo "   Please run: cd ../../scripts && ./deploy-complete-stack.sh"
    exit 1
fi

echo "✅ Gateway ID: $GATEWAY_ID"
echo "✅ HTTP URL: $GATEWAY_HTTP_URL"
echo "✅ MCP URL: $GATEWAY_MCP_URL"
echo ""

echo "✅ Gateway is ready!"
echo ""
echo "Next steps:"
echo "1. Create a test user: ./create-test-user.sh"
echo "2. Get JWT token: ./get-jwt-token.sh"
echo "3. Test HTTP endpoint: curl -H 'Authorization: Bearer <token>' $GATEWAY_HTTP_URL/health"
echo "4. Configure MCP client with: $GATEWAY_MCP_URL"
