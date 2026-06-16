#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cognito Client Credentials${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get stack outputs
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)
TOKEN_ENDPOINT=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoTokenEndpoint`].OutputValue' --output text)

echo -e "${YELLOW}User Pool ID:${NC} $USER_POOL_ID"
echo -e "${YELLOW}Client ID:${NC} $CLIENT_ID"
echo ""

# Get client secret
echo -e "${YELLOW}Retrieving client secret...${NC}"
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

if [ -z "$CLIENT_SECRET" ] || [ "$CLIENT_SECRET" == "None" ]; then
    echo -e "${RED}❌ Failed to retrieve client secret${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Client secret retrieved${NC}"
echo ""

# Display credentials
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Client Credentials${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Client ID:${NC}"
echo "$CLIENT_ID"
echo ""
echo -e "${YELLOW}Client Secret:${NC}"
echo "$CLIENT_SECRET"
echo ""
echo -e "${YELLOW}Token Endpoint:${NC}"
echo "$TOKEN_ENDPOINT"
echo ""

# Save to file
mkdir -p config
cat > config/client-credentials.json <<EOF
{
  "user_pool_id": "$USER_POOL_ID",
  "client_id": "$CLIENT_ID",
  "client_secret": "$CLIENT_SECRET",
  "token_endpoint": "$TOKEN_ENDPOINT",
  "region": "$REGION"
}
EOF

echo -e "${GREEN}✅ Credentials saved to config/client-credentials.json${NC}"
echo ""

# Test getting a token
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Client Credentials Flow${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Getting access token...${NC}"

# Encode credentials for Basic Auth
AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)

TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $AUTH_HEADER" \
  -d "grant_type=client_credentials" \
  -d "scope=spark-api/spark.execute")

# Check if we got a token
if echo "$TOKEN_RESPONSE" | jq -e '.access_token' > /dev/null 2>&1; then
    ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')
    TOKEN_TYPE=$(echo "$TOKEN_RESPONSE" | jq -r '.token_type')
    EXPIRES_IN=$(echo "$TOKEN_RESPONSE" | jq -r '.expires_in')
    
    echo -e "${GREEN}✅ Access token obtained successfully!${NC}"
    echo ""
    echo -e "${YELLOW}Token Type:${NC} $TOKEN_TYPE"
    echo -e "${YELLOW}Expires In:${NC} $EXPIRES_IN seconds"
    echo ""
    echo -e "${YELLOW}Access Token (first 50 chars):${NC}"
    echo "${ACCESS_TOKEN:0:50}..."
    echo ""
    
    # Save token
    echo "$ACCESS_TOKEN" > /tmp/service_access_token.txt
    echo -e "${GREEN}✅ Token saved to /tmp/service_access_token.txt${NC}"
    echo ""
    
    # Decode and display token claims
    echo -e "${YELLOW}Token Claims:${NC}"
    echo "$ACCESS_TOKEN" | cut -d'.' -f2 | base64 -d 2>/dev/null | jq '.' || echo "Could not decode token"
else
    echo -e "${RED}❌ Failed to get access token${NC}"
    echo ""
    echo -e "${YELLOW}Response:${NC}"
    echo "$TOKEN_RESPONSE" | jq '.' || echo "$TOKEN_RESPONSE"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Usage Example${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "# Get access token"
echo "curl -X POST '$TOKEN_ENDPOINT' \\"
echo "  -H 'Content-Type: application/x-www-form-urlencoded' \\"
echo "  -H 'Authorization: Basic \$(echo -n \"$CLIENT_ID:$CLIENT_SECRET\" | base64)' \\"
echo "  -d 'grant_type=client_credentials' \\"
echo "  -d 'scope=spark-api/spark.execute'"
echo ""
echo "# Use token with Gateway"
echo "curl -X POST <gateway-url> \\"
echo "  -H 'Authorization: Bearer \$ACCESS_TOKEN' \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"prompt\": \"your request\"}'"
echo ""
