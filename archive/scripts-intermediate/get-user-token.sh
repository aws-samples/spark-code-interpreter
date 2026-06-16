#!/bin/bash

# Helper script to get a user ID token with proper SECRET_HASH
# Usage: ./get-user-token.sh [username] [password]

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

# Get username and password from args or use defaults
USERNAME=${1:-"gateway-test@example.com"}
PASSWORD=${2:-"TestPass123!"}

echo -e "${BLUE}Getting User ID Token${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)

echo "  User Pool ID: $USER_POOL_ID"
echo "  Client ID: $CLIENT_ID"
echo "  Username: $USERNAME"
echo ""

# Get client secret
echo -e "${YELLOW}Getting client secret...${NC}"
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

if [ -z "$CLIENT_SECRET" ] || [ "$CLIENT_SECRET" == "None" ]; then
    echo -e "${RED}❌ Failed to get client secret${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Client secret retrieved${NC}"
echo ""

# Create user if doesn't exist
echo -e "${YELLOW}Ensuring user exists...${NC}"
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --user-attributes Name=email,Value=$USERNAME Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --region $REGION > /dev/null 2>&1

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password "$PASSWORD" \
  --permanent \
  --region $REGION > /dev/null 2>&1

echo -e "${GREEN}✅ User ready${NC}"
echo ""

# Calculate SECRET_HASH
echo -e "${YELLOW}Calculating SECRET_HASH...${NC}"
echo "  Formula: HMAC-SHA256(username + clientId, clientSecret)"
echo "  Input: ${USERNAME}${CLIENT_ID}"

SECRET_HASH=$(echo -n "${USERNAME}${CLIENT_ID}" | openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | base64)

echo "  SECRET_HASH: ${SECRET_HASH:0:30}..."
echo ""

# Get ID token
echo -e "${YELLOW}Getting ID token...${NC}"
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json 2>&1)

if echo "$AUTH_RESPONSE" | jq -e '.AuthenticationResult.IdToken' > /dev/null 2>&1; then
    ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')
    ACCESS_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.AccessToken')
    REFRESH_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.RefreshToken')
    EXPIRES_IN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.ExpiresIn')
    
    echo -e "${GREEN}✅ Tokens obtained successfully!${NC}"
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Token Information${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo -e "${YELLOW}ID Token (use this for Gateway):${NC}"
    echo "$ID_TOKEN"
    echo ""
    echo -e "${YELLOW}Access Token:${NC}"
    echo "$ACCESS_TOKEN"
    echo ""
    echo -e "${YELLOW}Expires In:${NC} $EXPIRES_IN seconds"
    echo ""
    
    # Save tokens
    echo "$ID_TOKEN" > /tmp/id_token.txt
    echo "$ACCESS_TOKEN" > /tmp/access_token.txt
    echo "$REFRESH_TOKEN" > /tmp/refresh_token.txt
    
    echo -e "${GREEN}✅ Tokens saved:${NC}"
    echo "  ID Token: /tmp/id_token.txt"
    echo "  Access Token: /tmp/access_token.txt"
    echo "  Refresh Token: /tmp/refresh_token.txt"
    echo ""
    
    # Decode ID token
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}ID Token Claims${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "$ID_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.'
    echo ""
    
    # Show usage
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}Usage${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
    echo "Use the ID token to call the Gateway:"
    echo ""
    echo "curl -X POST \$GATEWAY_URL \\"
    echo "  -H \"Authorization: Bearer $ID_TOKEN\" \\"
    echo "  -H \"Content-Type: application/json\" \\"
    echo "  -d '{...}'"
    echo ""
    
else
    echo -e "${RED}❌ Failed to get tokens${NC}"
    echo ""
    echo "Error response:"
    echo "$AUTH_RESPONSE" | jq '.' 2>/dev/null || echo "$AUTH_RESPONSE"
    echo ""
    echo -e "${YELLOW}Common issues:${NC}"
    echo "  1. Client secret mismatch"
    echo "  2. Incorrect SECRET_HASH calculation"
    echo "  3. User doesn't exist or password is wrong"
    echo "  4. Auth flow not enabled on client"
    exit 1
fi

echo -e "${GREEN}Done! 🎉${NC}"
