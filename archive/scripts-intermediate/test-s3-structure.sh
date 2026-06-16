#!/bin/bash

# Test the new S3 structure with session-based folders
# Run this after the Lambda has been updated

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

BUCKET="spark-data-817323390093-us-east-1"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test S3 Session-Based Structure${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Step 1: Invoke Lambda
echo -e "${YELLOW}Step 1: Invoking Lambda...${NC}"
echo "This will take ~60 seconds..."
echo ""

aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"calculate 10 + 20"}' \
  --region us-east-1 \
  /tmp/test_response.json > /dev/null 2>&1 &

LAMBDA_PID=$!

# Wait for Lambda to complete
echo -e "${YELLOW}Waiting for Lambda to complete...${NC}"
for i in {1..70}; do
    if ! kill -0 $LAMBDA_PID 2>/dev/null; then
        break
    fi
    echo -n "."
    sleep 1
done
echo ""
echo ""

# Step 2: Get session ID from response
echo -e "${YELLOW}Step 2: Getting session ID...${NC}"
if [ -f /tmp/test_response.json ]; then
    SESSION_ID=$(cat /tmp/test_response.json | jq -r '.body' | jq -r '.sessionId' 2>/dev/null)
    
    if [ -z "$SESSION_ID" ] || [ "$SESSION_ID" == "null" ]; then
        echo -e "${RED}Could not extract session ID from response${NC}"
        echo "Response:"
        cat /tmp/test_response.json | jq '.'
        exit 1
    fi
    
    echo -e "${GREEN}✅ Session ID: $SESSION_ID${NC}"
else
    echo -e "${RED}Response file not found${NC}"
    exit 1
fi

echo ""

# Step 3: Check S3 structure
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Checking S3 Structure${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Looking for session folder: s3://$BUCKET/$SESSION_ID/${NC}"
echo ""

# Check if session folder exists
if aws s3 ls s3://$BUCKET/$SESSION_ID/ > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Session folder exists!${NC}"
    echo ""
    
    # List contents
    echo -e "${YELLOW}Contents of session folder:${NC}"
    aws s3 ls s3://$BUCKET/$SESSION_ID/ --recursive --human-readable
    echo ""
    
    # Check for scripts
    if aws s3 ls s3://$BUCKET/$SESSION_ID/scripts/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Scripts folder found${NC}"
        echo ""
        echo "Generated code:"
        aws s3 ls s3://$BUCKET/$SESSION_ID/scripts/ --recursive --human-readable
        echo ""
        
        # Download and show the code
        CODE_FILE=$(aws s3 ls s3://$BUCKET/$SESSION_ID/scripts/ --recursive | tail -1 | awk '{print $4}')
        if [ ! -z "$CODE_FILE" ]; then
            echo -e "${BLUE}Generated PySpark Code:${NC}"
            echo "----------------------------------------"
            aws s3 cp s3://$BUCKET/$CODE_FILE - 2>/dev/null
            echo "----------------------------------------"
            echo ""
        fi
    else
        echo -e "${YELLOW}⚠️  Scripts folder not found${NC}"
    fi
    
    # Check for output
    if aws s3 ls s3://$BUCKET/$SESSION_ID/output/ > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Output folder found${NC}"
        echo ""
        echo "Execution results:"
        aws s3 ls s3://$BUCKET/$SESSION_ID/output/ --recursive --human-readable
        echo ""
    else
        echo -e "${YELLOW}⚠️  Output folder not found (execution may have failed)${NC}"
    fi
    
else
    echo -e "${RED}❌ Session folder not found${NC}"
    echo ""
    echo "Checking recent S3 activity..."
    aws s3 ls s3://$BUCKET/ --recursive --human-readable | tail -10
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Lambda Response${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cat /tmp/test_response.json | jq '.body' -r | jq '.' 2>/dev/null || cat /tmp/test_response.json

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Expected S3 structure:"
echo "  s3://$BUCKET/"
echo "    └── $SESSION_ID/"
echo "        ├── scripts/"
echo "        │   └── {session_id}_code.py"
echo "        └── output/"
echo "            └── (execution results)"
echo ""

# Cleanup
rm -f /tmp/test_response.json
