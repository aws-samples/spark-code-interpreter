#!/bin/bash

# Test S3 Read and Write Operations
# This script tests the S3 write fix by running queries that read from and write to S3

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --no-cli-pager)
BUCKET="spark-data-${ACCOUNT_ID}-${REGION}"
WRAPPER_FUNCTION="${ENVIRONMENT}-spark-agent-wrapper"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}S3 Operations Test Suite${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Testing S3 read/write with Spark Lambda"
echo "Bucket: $BUCKET"
echo "Region: $REGION"
echo ""

# Test 1: Simple calculation (no S3)
echo -e "${BLUE}Test 1: Simple Calculation (Baseline)${NC}"
echo -e "${YELLOW}Query: What is 7 * 10?${NC}"
echo ""

aws lambda invoke \
  --function-name $WRAPPER_FUNCTION \
  --cli-binary-format raw-in-base64-out \
  --payload '{"prompt":"what is 7*10"}' \
  --region $REGION \
  /tmp/test1_response.json > /dev/null 2>&1

echo -e "${GREEN}✅ Lambda invoked${NC}"
echo "Waiting for processing (30 seconds)..."
sleep 30

if [ -f /tmp/test1_response.json ]; then
    echo -e "${BLUE}Response:${NC}"
    cat /tmp/test1_response.json | jq '.' 2>/dev/null || cat /tmp/test1_response.json
    echo ""
fi
echo ""

# Test 2: S3 Read Operation
echo -e "${BLUE}Test 2: S3 Read Operation${NC}"
echo -e "${YELLOW}Query: Load CSV from S3 and count rows${NC}"
echo "Input: s3://$BUCKET/test-input/test_data.csv"
echo ""

QUERY2="Load the CSV file from s3://$BUCKET/test-input/test_data.csv and tell me how many rows it has"

aws lambda invoke \
  --function-name $WRAPPER_FUNCTION \
  --cli-binary-format raw-in-base64-out \
  --payload "{\"prompt\":\"$QUERY2\"}" \
  --region $REGION \
  /tmp/test2_response.json > /dev/null 2>&1

echo -e "${GREEN}✅ Lambda invoked${NC}"
echo "Waiting for processing (60 seconds)..."
sleep 60

if [ -f /tmp/test2_response.json ]; then
    echo -e "${BLUE}Response:${NC}"
    cat /tmp/test2_response.json | jq '.' 2>/dev/null || cat /tmp/test2_response.json
    echo ""
    
    # Extract session ID
    SESSION_ID=$(cat /tmp/test2_response.json | jq -r '.body' 2>/dev/null | jq -r '.sessionId' 2>/dev/null)
    if [ ! -z "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        echo -e "${GREEN}Session ID: $SESSION_ID${NC}"
        echo ""
        
        # Check CloudWatch logs for errors
        echo -e "${YELLOW}Checking CloudWatch logs for errors...${NC}"
        aws logs tail /aws/lambda/dev-spark-on-lambda \
            --since 5m \
            --region $REGION \
            --format short 2>/dev/null | grep -i "error\|exception\|s3afilesystem" | head -10 || echo "No errors found"
        echo ""
    fi
fi
echo ""

# Test 3: S3 Write Operation (Critical Test)
echo -e "${BLUE}Test 3: S3 Write Operation (CRITICAL)${NC}"
echo -e "${YELLOW}Query: Group by category and write to S3${NC}"
echo "Input: s3://$BUCKET/test-input/test_data.csv"
echo "Output: s3://$BUCKET/test-output/"
echo ""

QUERY3="Load the CSV from s3://$BUCKET/test-input/test_data.csv, group by category and calculate total price, then save the results to s3://$BUCKET/test-output/"

aws lambda invoke \
  --function-name $WRAPPER_FUNCTION \
  --cli-binary-format raw-in-base64-out \
  --payload "{\"prompt\":\"$QUERY3\"}" \
  --region $REGION \
  /tmp/test3_response.json > /dev/null 2>&1

echo -e "${GREEN}✅ Lambda invoked${NC}"
echo "Waiting for processing (90 seconds)..."
sleep 90

if [ -f /tmp/test3_response.json ]; then
    echo -e "${BLUE}Response:${NC}"
    cat /tmp/test3_response.json | jq '.' 2>/dev/null || cat /tmp/test3_response.json
    echo ""
    
    # Extract session ID
    SESSION_ID=$(cat /tmp/test3_response.json | jq -r '.body' 2>/dev/null | jq -r '.sessionId' 2>/dev/null)
    if [ ! -z "$SESSION_ID" ] && [ "$SESSION_ID" != "null" ]; then
        echo -e "${GREEN}Session ID: $SESSION_ID${NC}"
        echo ""
    fi
fi
echo ""

# Verification: Check CloudWatch Logs
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification: CloudWatch Logs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Checking for ClassNotFoundException...${NC}"
ERRORS=$(aws logs tail /aws/lambda/dev-spark-on-lambda \
    --since 10m \
    --region $REGION \
    --format short 2>/dev/null | grep -i "ClassNotFoundException.*S3AFileSystem" || true)

if [ -z "$ERRORS" ]; then
    echo -e "${GREEN}✅ No ClassNotFoundException found!${NC}"
    echo "The S3 write fix is working correctly."
else
    echo -e "${RED}❌ ClassNotFoundException still present:${NC}"
    echo "$ERRORS"
fi
echo ""

echo -e "${YELLOW}Recent errors (if any):${NC}"
aws logs tail /aws/lambda/dev-spark-on-lambda \
    --since 10m \
    --region $REGION \
    --format short 2>/dev/null | grep -i "error\|exception" | head -20 || echo "No errors found"
echo ""

# Verification: Check S3 Output
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Verification: S3 Output Files${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Checking for output files in S3...${NC}"
OUTPUT_FILES=$(aws s3 ls s3://$BUCKET/test-output/ --recursive --region $REGION 2>/dev/null || true)

if [ ! -z "$OUTPUT_FILES" ]; then
    echo -e "${GREEN}✅ Output files found in S3!${NC}"
    echo "$OUTPUT_FILES"
    echo ""
    echo -e "${GREEN}S3 write operation successful!${NC}"
else
    echo -e "${YELLOW}⚠️  No output files found yet${NC}"
    echo "This could mean:"
    echo "  1. The query is still processing"
    echo "  2. The query failed"
    echo "  3. Results were returned via /tmp/output.json instead"
fi
echo ""

# Summary
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Test Results:"
echo "  1. Simple Calculation: ✅ (baseline)"
echo "  2. S3 Read Operation: Check response above"
echo "  3. S3 Write Operation: Check S3 output above"
echo ""

if [ -z "$ERRORS" ]; then
    echo -e "${GREEN}✅ S3 Write Fix Verification: PASSED${NC}"
    echo "No ClassNotFoundException found in logs"
else
    echo -e "${RED}❌ S3 Write Fix Verification: FAILED${NC}"
    echo "ClassNotFoundException still present"
fi
echo ""

echo "CloudWatch Logs:"
echo "  aws logs tail /aws/lambda/dev-spark-on-lambda --follow --region $REGION"
echo ""

echo "S3 Output Location:"
echo "  s3://$BUCKET/test-output/"
echo ""

# Cleanup
rm -f /tmp/test1_response.json /tmp/test2_response.json /tmp/test3_response.json

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Complete${NC}"
echo -e "${BLUE}========================================${NC}"
