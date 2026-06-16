#!/bin/bash
set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

echo "🚀 Deploying Spark Gateway Stack with Cognito"
echo ""

# Configuration
export AWS_REGION=${AWS_REGION:-us-east-1}
export ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Get Cognito outputs from CloudFormation
echo "📋 Getting Cognito configuration..."
COGNITO_USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
    --output text 2>/dev/null || echo "")

COGNITO_APP_CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $AWS_REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' \
    --output text 2>/dev/null || echo "")

if [ -z "$COGNITO_USER_POOL_ID" ] || [ -z "$COGNITO_APP_CLIENT_ID" ]; then
    echo "❌ Cognito not found in CloudFormation stack"
    echo "   Please run deploy-complete-stack.sh first to create the infrastructure"
    exit 1
fi

echo "✅ Cognito User Pool ID: $COGNITO_USER_POOL_ID"
echo "✅ Cognito App Client ID: $COGNITO_APP_CLIENT_ID"
echo ""

# Deploy gateway
echo "🚀 Deploying Gateway Lambda..."
cd backend/backend
./deploy-gateway.sh

echo ""
echo "✅ Gateway deployment complete!"
echo ""
echo "Next steps:"
echo "1. Create a test user: ./create-test-user.sh"
echo "2. Get JWT token: ./get-jwt-token.sh"
echo "3. Test the gateway with the JWT token"
