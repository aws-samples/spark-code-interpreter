#!/bin/bash

# Test Deployment Script - Verify all components are working

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

REGION="us-east-1"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Spark Code Interpreter - Deployment Test${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
  --output text 2>/dev/null)

if [ -z "$ALB_URL" ]; then
    echo -e "${RED}❌ Could not get ALB URL. Is the stack deployed?${NC}"
    exit 1
fi

echo "Testing ALB URL: $ALB_URL"
echo ""

# Test 1: Health Check
echo -e "${YELLOW}Test 1: Health Check${NC}"
response=$(curl -s -w "\n%{http_code}" $ALB_URL/health)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ Health check passed${NC}"
    echo "Response: $body"
else
    echo -e "${RED}❌ Health check failed (HTTP $http_code)${NC}"
    echo "Response: $body"
fi
echo ""

# Test 2: API Info
echo -e "${YELLOW}Test 2: API Info${NC}"
response=$(curl -s -w "\n%{http_code}" $ALB_URL/)
http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" == "200" ]; then
    echo -e "${GREEN}✅ API info endpoint working${NC}"
    echo "$body" | jq '.' 2>/dev/null || echo "$body"
else
    echo -e "${RED}❌ API info endpoint failed (HTTP $http_code)${NC}"
fi
echo ""

# Test 3: Spark Code Generation
echo -e "${YELLOW}Test 3: Spark Code Generation${NC}"
SESSION_ID="test-$(date +%s)"

response=$(curl -s -w "\n%{http_code}" -X POST $ALB_URL/spark/generate \
  -H "Content-Type: application/json" \
  -d "{
    \"prompt\": \"create a dataset with 10 rows of sample data with columns: id, name, value\",
    \"session_id\": \"$SESSION_ID\",
    \"execution_platform\": \"lambda\"
  }")

http_code=$(echo "$response" | tail -n1)
body=$(echo "$response" | head -n-1)

if [ "$http_code" == "200" ]; then
    success=$(echo "$body" | jq -r '.success' 2>/dev/null)
    if [ "$success" == "true" ]; then
        echo -e "${GREEN}✅ Spark code generation successful${NC}"
        echo "$body" | jq '.result | {execution_result, s3_output_path}' 2>/dev/null || echo "$body"
    else
        echo -e "${RED}❌ Spark code generation failed${NC}"
        echo "$body" | jq '.' 2>/dev/null || echo "$body"
    fi
else
    echo -e "${RED}❌ Spark generation endpoint failed (HTTP $http_code)${NC}"
    echo "$body"
fi
echo ""

# Test 4: Check S3 Bucket
echo -e "${YELLOW}Test 4: S3 Bucket Access${NC}"
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`SparkDataBucketName`].OutputValue' \
  --output text 2>/dev/null)

if [ -n "$S3_BUCKET" ]; then
    aws s3 ls s3://$S3_BUCKET/ --region $REGION > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ S3 bucket accessible${NC}"
        echo "Bucket: $S3_BUCKET"
    else
        echo -e "${RED}❌ S3 bucket not accessible${NC}"
    fi
else
    echo -e "${RED}❌ Could not get S3 bucket name${NC}"
fi
echo ""

# Test 5: Lambda Function
echo -e "${YELLOW}Test 5: Lambda Function${NC}"
LAMBDA_FUNCTION=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`SparkLambdaFunctionName`].OutputValue' \
  --output text 2>/dev/null)

if [ -n "$LAMBDA_FUNCTION" ]; then
    state=$(aws lambda get-function \
      --function-name $LAMBDA_FUNCTION \
      --region $REGION \
      --query 'Configuration.State' \
      --output text 2>/dev/null)
    
    if [ "$state" == "Active" ]; then
        echo -e "${GREEN}✅ Lambda function active${NC}"
        echo "Function: $LAMBDA_FUNCTION"
    else
        echo -e "${RED}❌ Lambda function not active (State: $state)${NC}"
    fi
else
    echo -e "${RED}❌ Could not get Lambda function name${NC}"
fi
echo ""

# Test 6: EMR Application
echo -e "${YELLOW}Test 6: EMR Serverless Application${NC}"
EMR_APP_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`EMRApplicationId`].OutputValue' \
  --output text 2>/dev/null)

if [ -n "$EMR_APP_ID" ]; then
    state=$(aws emr-serverless get-application \
      --application-id $EMR_APP_ID \
      --region $REGION \
      --query 'application.state' \
      --output text 2>/dev/null)
    
    if [ "$state" == "CREATED" ]; then
        echo -e "${GREEN}✅ EMR application ready${NC}"
        echo "Application ID: $EMR_APP_ID"
    else
        echo -e "${RED}❌ EMR application not ready (State: $state)${NC}"
    fi
else
    echo -e "${RED}❌ Could not get EMR application ID${NC}"
fi
echo ""

# Summary
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "ALB URL: $ALB_URL"
echo "S3 Bucket: $S3_BUCKET"
echo "Lambda Function: $LAMBDA_FUNCTION"
echo "EMR Application: $EMR_APP_ID"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Check CloudWatch logs for any errors"
echo "2. Monitor Bedrock usage for throttling"
echo "3. Test with more complex queries"
echo "4. Set up monitoring and alerts"
echo ""
echo -e "${GREEN}Testing complete!${NC}"
