#!/bin/bash

# Test the complete flow with a simple calculation

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

QUESTION=${1:-"what is 7*10"}
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Spark Agent with Calculation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Question: $QUESTION${NC}"
echo -e "${YELLOW}Profile:  ${AWS_PROFILE:-default}${NC}"
echo -e "${YELLOW}Region:   $REGION${NC}"
echo ""

# Resolve account ID and S3 bucket dynamically
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --no-cli-pager 2>/dev/null)
if [ -z "$ACCOUNT_ID" ]; then
    echo -e "${RED}❌ Could not resolve AWS account. Check AWS_PROFILE and credentials.${NC}"
    exit 1
fi
S3_BUCKET="spark-data-${ACCOUNT_ID}-${REGION}"

echo -e "${YELLOW}Step 1: Invoking wrapper Lambda...${NC}"
aws lambda invoke \
  --function-name "${ENVIRONMENT}-spark-agent-wrapper" \
  --payload "{\"prompt\":\"$QUESTION\"}" \
  --cli-binary-format raw-in-base64-out \
  --region "$REGION" \
  /tmp/test_calc.json > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lambda invocation failed${NC}"
    echo "Check your AWS credentials and that the wrapper Lambda is deployed."
    exit 1
fi

echo -e "${GREEN}✅ Lambda invoked${NC}"
echo ""

echo -e "${YELLOW}Step 2: Waiting for agent processing (~60 seconds)...${NC}"
for i in {1..60}; do
    echo -n "."
    sleep 1
done
echo ""
echo ""

echo -e "${YELLOW}Step 3: Checking response...${NC}"
if [ ! -f /tmp/test_calc.json ]; then
    echo -e "${RED}❌ Response file not found${NC}"
    exit 1
fi

echo ""
echo -e "${BLUE}Response:${NC}"
cat /tmp/test_calc.json | jq '.'
echo ""

# Extract session ID
SESSION_ID=$(cat /tmp/test_calc.json | jq -r '.body' 2>/dev/null | jq -r '.session_id // .sessionId' 2>/dev/null)

if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" == "null" ]; then
    echo -e "${YELLOW}⚠️  Could not extract session ID${NC}"
    echo "Full response body:"
    cat /tmp/test_calc.json | jq '.body' -r 2>/dev/null || cat /tmp/test_calc.json
    exit 0
fi

echo -e "${GREEN}✅ Session ID: $SESSION_ID${NC}"
echo ""

echo -e "${YELLOW}Step 4: Checking S3 for results...${NC}"
echo "Location: s3://${S3_BUCKET}/${SESSION_ID}/"
echo ""

aws s3 ls "s3://${S3_BUCKET}/${SESSION_ID}/" --recursive --human-readable 2>/dev/null

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Files found in S3${NC}"
    echo ""

    # Check for generated code
    if aws s3 ls "s3://${S3_BUCKET}/${SESSION_ID}/${SESSION_ID}_code.py" > /dev/null 2>&1; then
        echo -e "${BLUE}Generated PySpark Code:${NC}"
        echo "----------------------------------------"
        aws s3 cp "s3://${S3_BUCKET}/${SESSION_ID}/${SESSION_ID}_code.py" - 2>/dev/null
        echo "----------------------------------------"
        echo ""
    fi

    # Check for output
    if aws s3 ls "s3://${S3_BUCKET}/${SESSION_ID}/output/" > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Output folder exists${NC}"
        echo "Results written to S3 successfully!"
    else
        echo -e "${YELLOW}⚠️  No output folder found${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  No files found in S3 yet${NC}"
    echo "The agent may still be processing or encountered an error."
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Cleanup
rm -f /tmp/test_calc.json
