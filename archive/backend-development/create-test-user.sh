#!/bin/bash
set -e

# Get Cognito configuration from CloudFormation
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo "👤 Creating Test User in Cognito"
echo ""

# Get User Pool ID from CloudFormation
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
    --output text)

if [ -z "$USER_POOL_ID" ]; then
    echo "❌ Failed to get User Pool ID from CloudFormation"
    exit 1
fi

echo "User Pool ID: $USER_POOL_ID"
echo ""

# Prompt for user details
read -p "Email address: " EMAIL
read -sp "Password (min 8 chars, uppercase, lowercase, number, symbol): " PASSWORD
echo ""
echo ""

# Create user
echo "🔄 Creating user..."
aws cognito-idp admin-create-user \
    --user-pool-id $USER_POOL_ID \
    --username $EMAIL \
    --user-attributes Name=email,Value=$EMAIL Name=email_verified,Value=true \
    --message-action SUPPRESS \
    --region $REGION

# Set permanent password
echo "🔑 Setting password..."
aws cognito-idp admin-set-user-password \
    --user-pool-id $USER_POOL_ID \
    --username $EMAIL \
    --password "$PASSWORD" \
    --permanent \
    --region $REGION

echo ""
echo "✅ User created successfully!"
echo ""
echo "Username: $EMAIL"
echo "Password: [hidden]"
echo ""
echo "Next steps:"
echo "1. Run ./get-jwt-token.sh to get a JWT token"
echo "2. Use the token to authenticate API requests"
