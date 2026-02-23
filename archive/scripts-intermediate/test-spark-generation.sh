#!/bin/bash

# Test Spark Code Generation
# Sends a request to generate and execute Spark code

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
    --output text 2>/dev/null)

if [ -z "$ALB_URL" ]; then
    echo -e "${RED}❌ Could not get ALB URL${NC}"
    exit 1
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Spark Code Generation Test${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "API URL: $ALB_URL"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
HEALTH_RESPONSE=$(curl -s -w "\n%{http_code}" $ALB_URL/health)
HTTP_CODE=$(echo "$HEALTH_RESPONSE" | tail -n 1)
BODY=$(echo "$HEALTH_RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
else
    echo -e "${RED}❌ Health check failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
    exit 1
fi
echo ""

# Test 2: Generate Sample Dataset
echo -e "${YELLOW}Test 2: Generate Sample Dataset${NC}"
echo "Prompt: Generate a dataset with 100 rows containing user names, emails, phone numbers, addresses, state, and country"
echo ""

SESSION_ID="test-$(date +%s)"

REQUEST_BODY=$(cat <<EOF
{
  "prompt": "Create a Spark DataFrame with 100 rows of sample data containing the following columns: user_name (full name), email (valid email format), phone_number (US format), address (street address), city, state (US state), country (USA), and user_id (sequential numbers 1-100). Use realistic fake data. Show the first 10 rows and save the full dataset to S3.",
  "session_id": "$SESSION_ID",
  "execution_platform": "lambda"
}
EOF
)

echo "Sending request..."
echo ""

RESPONSE=$(curl -s -w "\n%{http_code}" -X POST $ALB_URL/spark/generate \
  -H "Content-Type: application/json" \
  -d "$REQUEST_BODY")

HTTP_CODE=$(echo "$RESPONSE" | tail -n 1)
BODY=$(echo "$RESPONSE" | sed '$d')

if [ "$HTTP_CODE" == "200" ]; then
    echo -e "${GREEN}✅ Request successful (HTTP $HTTP_CODE)${NC}"
    echo ""
    
    # Parse response
    SUCCESS=$(echo "$BODY" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('success', False))" 2>/dev/null)
    
    if [ "$SUCCESS" == "True" ]; then
        echo -e "${GREEN}✅ Spark code generation and execution successful!${NC}"
        echo ""
        
        # Extract key information
        echo -e "${BLUE}Results:${NC}"
        echo "$BODY" | python3 -c "
import sys, json
data = json.load(sys.stdin)
result = data.get('result', {})
print(f\"Execution Result: {result.get('execution_result', 'N/A')}\")
print(f\"S3 Output Path: {result.get('s3_output_path', 'N/A')}\")
print(f\"Generated Code Preview:\")
code = result.get('generated_code', '')
if code:
    lines = code.split('\n')[:15]
    for line in lines:
        print(f\"  {line}\")
    if len(code.split('\n')) > 15:
        print(f\"  ... ({len(code.split('\n')) - 15} more lines)\")
" 2>/dev/null || echo "$BODY" | python3 -m json.tool
        
    else
        echo -e "${RED}❌ Spark execution failed${NC}"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    fi
else
    echo -e "${RED}❌ Request failed (HTTP $HTTP_CODE)${NC}"
    echo "$BODY"
fi

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
