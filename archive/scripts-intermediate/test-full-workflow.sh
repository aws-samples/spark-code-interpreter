#!/bin/bash

# Test full Spark workflow: Generate code, then execute it
# This demonstrates the complete end-to-end flow

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
CONFIG_FILE="../config/deployment-config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Deployment config not found${NC}"
    exit 1
fi

ALB_URL=$(jq -r '.alb_url' $CONFIG_FILE)
SESSION_ID="full-workflow-$(date +%s)"

echo "========================================"
echo "Spark Full Workflow Test"
echo "========================================"
echo "API URL: $ALB_URL"
echo "Session ID: $SESSION_ID"
echo ""

# Step 1: Generate Spark code
echo -e "${BLUE}Step 1: Generating Spark code...${NC}"
PROMPT="Create a dataset with 10 rows containing: id (1-10), name (random names), age (20-60), and city (random US cities). Show the first 5 rows and save to S3."

GENERATE_RESPONSE=$(curl -s -X POST "${ALB_URL}/spark/generate" \
    -H "Content-Type: application/json" \
    -d "{
        \"prompt\": \"$PROMPT\",
        \"session_id\": \"$SESSION_ID\",
        \"execution_platform\": \"lambda\"
    }")

echo "$GENERATE_RESPONSE" | jq '.' > /tmp/generate_response.json

SUCCESS=$(echo "$GENERATE_RESPONSE" | jq -r '.success')
if [ "$SUCCESS" != "true" ]; then
    echo -e "${RED}❌ Code generation failed${NC}"
    echo "$GENERATE_RESPONSE" | jq '.'
    exit 1
fi

echo -e "${GREEN}✅ Code generated successfully${NC}"

# Extract the generated code
SPARK_CODE=$(echo "$GENERATE_RESPONSE" | jq -r '.result.spark_code')
S3_OUTPUT_PATH=$(echo "$GENERATE_RESPONSE" | jq -r '.result.s3_output_path')

echo ""
echo -e "${YELLOW}Generated Code Preview:${NC}"
echo "$SPARK_CODE" | head -20
echo "..."
echo ""
echo "S3 Output Path: $S3_OUTPUT_PATH"
echo ""

# Step 2: Execute the generated code
echo -e "${BLUE}Step 2: Executing Spark code on Lambda...${NC}"

EXECUTE_RESPONSE=$(curl -s -X POST "${ALB_URL}/spark/execute" \
    -H "Content-Type: application/json" \
    -d "{
        \"spark_code\": $(echo "$SPARK_CODE" | jq -Rs .),
        \"session_id\": \"$SESSION_ID\",
        \"s3_output_path\": \"$S3_OUTPUT_PATH\",
        \"execution_platform\": \"lambda\"
    }")

echo "$EXECUTE_RESPONSE" | jq '.' > /tmp/execute_response.json

EXEC_SUCCESS=$(echo "$EXECUTE_RESPONSE" | jq -r '.success')
if [ "$EXEC_SUCCESS" != "true" ]; then
    echo -e "${RED}❌ Execution failed${NC}"
    echo "$EXECUTE_RESPONSE" | jq '.'
    exit 1
fi

echo -e "${GREEN}✅ Code executed successfully${NC}"
echo ""

# Display execution results
echo -e "${YELLOW}Execution Results:${NC}"
EXEC_RESULT=$(echo "$EXECUTE_RESPONSE" | jq -r '.result.execution_result')
EXEC_MESSAGE=$(echo "$EXECUTE_RESPONSE" | jq -r '.result.execution_message')

echo "Status: $EXEC_RESULT"
echo "Message: $EXEC_MESSAGE"
echo ""

# Display output
echo -e "${YELLOW}Execution Output:${NC}"
echo "$EXECUTE_RESPONSE" | jq -r '.result.execution_output[]' 2>/dev/null || echo "No output"
echo ""

# Display actual results (data)
echo -e "${YELLOW}Data Results:${NC}"
RESULTS=$(echo "$EXECUTE_RESPONSE" | jq '.result.actual_results')
RESULT_COUNT=$(echo "$RESULTS" | jq 'length')

if [ "$RESULT_COUNT" -gt 0 ]; then
    echo "Retrieved $RESULT_COUNT rows:"
    echo "$RESULTS" | jq '.[0:5]'  # Show first 5 rows
    if [ "$RESULT_COUNT" -gt 5 ]; then
        echo "... and $((RESULT_COUNT - 5)) more rows"
    fi
else
    echo "No data results returned (data may be in S3)"
fi

echo ""
echo -e "${YELLOW}S3 Location:${NC}"
echo "$S3_OUTPUT_PATH"
echo ""

# Check if data exists in S3
echo -e "${BLUE}Checking S3 for output files...${NC}"
S3_BUCKET=$(echo "$S3_OUTPUT_PATH" | sed 's|s3://\([^/]*\)/.*|\1|')
S3_PREFIX=$(echo "$S3_OUTPUT_PATH" | sed 's|s3://[^/]*/||')

aws s3 ls "s3://$S3_BUCKET/$S3_PREFIX/" --region us-east-1 2>/dev/null && \
    echo -e "${GREEN}✅ Files found in S3${NC}" || \
    echo -e "${YELLOW}⚠️  No files in S3 yet (may still be processing)${NC}"

echo ""
echo "========================================"
echo "Full Workflow Test Complete"
echo "========================================"
echo ""
echo "Summary:"
echo "  1. Code Generation: ✅"
echo "  2. Code Execution: $([ "$EXEC_RESULT" == "success" ] && echo "✅" || echo "⚠️ $EXEC_RESULT")"
echo "  3. S3 Output: $S3_OUTPUT_PATH"
echo ""
