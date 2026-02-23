#!/bin/bash
set -e

# Get Cognito configuration from CloudFormation
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo "🔐 Getting JWT Token from Cognito"
echo ""

# Get Cognito details from CloudFormation
USER_POOL_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
    --output text)

APP_CLIENT_ID=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' \
    --output text)

if [ -z "$USER_POOL_ID" ] || [ -z "$APP_CLIENT_ID" ]; then
    echo "❌ Failed to get Cognito configuration from CloudFormation"
    exit 1
fi

echo "User Pool ID: $USER_POOL_ID"
echo "App Client ID: $APP_CLIENT_ID"
echo ""

# Prompt for credentials
read -p "Username (email): " USERNAME
read -sp "Password: " PASSWORD
echo ""
echo ""

# Authenticate and get tokens
echo "🔄 Authenticating..."
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
    --auth-flow USER_PASSWORD_AUTH \
    --client-id $APP_CLIENT_ID \
    --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD \
    --region $REGION \
    --output json 2>&1)

if [ $? -ne 0 ]; then
    echo "❌ Authentication failed:"
    echo "$AUTH_RESPONSE"
    exit 1
fi

# Extract tokens
ID_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')
ACCESS_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.AccessToken')
REFRESH_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.RefreshToken')

if [ "$ID_TOKEN" == "null" ]; then
    echo "❌ Failed to get tokens"
    echo "$AUTH_RESPONSE"
    exit 1
fi

echo "✅ Authentication successful!"
echo ""
echo "ID Token (use this for API calls):"
echo "$ID_TOKEN"
echo ""
echo "Access Token:"
echo "$ACCESS_TOKEN"
echo ""
echo "Refresh Token (valid for 30 days):"
echo "$REFRESH_TOKEN"
echo ""
echo "Export as environment variable:"
echo "export SPARK_JWT_TOKEN=\"$ID_TOKEN\""
echo ""
echo "Test the gateway:"
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
    --output text)
echo "curl -H 'Authorization: Bearer $ID_TOKEN' $ALB_URL/health"
