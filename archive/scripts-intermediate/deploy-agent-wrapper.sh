#!/bin/bash

# Deploy Agent Wrapper Lambda
# This Lambda accepts natural language and calls the Spark Supervisor Agent

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"
FUNCTION_NAME="${ENVIRONMENT:-dev}-spark-agent-wrapper"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy Agent Wrapper Lambda${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
LAMBDA_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SparkLambdaFunctionArn`].OutputValue' --output text | xargs aws lambda get-function --function-name --region $REGION --query 'Configuration.Role' --output text 2>/dev/null)

# If that fails, get the role ARN directly
if [ -z "$LAMBDA_ROLE_ARN" ]; then
    LAMBDA_ROLE_ARN=$(aws iam get-role --role-name "${ENVIRONMENT:-dev}-spark-lambda-role" --query 'Role.Arn' --output text 2>/dev/null)
fi

# Get agent ARN
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"
if [ -f "config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark_supervisor_arn' config/deployment-config.json 2>/dev/null || echo "$AGENT_ARN")
fi

echo "Lambda Role ARN: $LAMBDA_ROLE_ARN"
echo "Agent ARN: $AGENT_ARN"
echo "Function Name: $FUNCTION_NAME"
echo ""

# Create deployment package
echo -e "${YELLOW}Creating deployment package...${NC}"

# Go to project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

if [ ! -d "agent-wrapper" ]; then
    echo -e "${RED}❌ agent-wrapper directory not found${NC}"
    exit 1
fi

cd agent-wrapper

# Create a clean package
rm -f agent_wrapper.zip
zip agent_wrapper.zip agent_wrapper.py

echo -e "${GREEN}✅ Deployment package created${NC}"
echo ""

# Check if function exists
echo -e "${YELLOW}Checking if function exists...${NC}"
FUNCTION_EXISTS=$(aws lambda get-function --function-name $FUNCTION_NAME --region $REGION 2>&1)

if echo "$FUNCTION_EXISTS" | grep -q "ResourceNotFoundException"; then
    echo "Function does not exist, creating new function..."
    
    # Create new function
    CREATE_RESPONSE=$(aws lambda create-function \
      --function-name $FUNCTION_NAME \
      --runtime python3.11 \
      --role $LAMBDA_ROLE_ARN \
      --handler agent_wrapper.lambda_handler \
      --zip-file fileb://agent_wrapper.zip \
      --timeout 900 \
      --memory-size 512 \
      --environment "Variables={AGENT_ARN=$AGENT_ARN}" \
      --description "Wrapper Lambda that accepts natural language and invokes Spark Supervisor Agent" \
      --region $REGION 2>&1)
    
    if echo "$CREATE_RESPONSE" | jq -e '.FunctionArn' > /dev/null 2>&1; then
        FUNCTION_ARN=$(echo "$CREATE_RESPONSE" | jq -r '.FunctionArn')
        echo -e "${GREEN}✅ Function created successfully${NC}"
        echo "Function ARN: $FUNCTION_ARN"
    else
        echo -e "${RED}❌ Failed to create function${NC}"
        echo "$CREATE_RESPONSE"
        cd ..
        exit 1
    fi
else
    echo "Function exists, updating code..."
    
    # Update existing function
    UPDATE_RESPONSE=$(aws lambda update-function-code \
      --function-name $FUNCTION_NAME \
      --zip-file fileb://agent_wrapper.zip \
      --region $REGION 2>&1)
    
    if echo "$UPDATE_RESPONSE" | jq -e '.FunctionArn' > /dev/null 2>&1; then
        FUNCTION_ARN=$(echo "$UPDATE_RESPONSE" | jq -r '.FunctionArn')
        echo -e "${GREEN}✅ Function code updated${NC}"
        
        # Update environment variables
        aws lambda update-function-configuration \
          --function-name $FUNCTION_NAME \
          --environment "Variables={AGENT_ARN=$AGENT_ARN}" \
          --region $REGION > /dev/null 2>&1
        
        echo -e "${GREEN}✅ Function configuration updated${NC}"
        echo "Function ARN: $FUNCTION_ARN"
    else
        echo -e "${RED}❌ Failed to update function${NC}"
        echo "$UPDATE_RESPONSE"
        cd ..
        exit 1
    fi
fi

cd ..

echo ""
echo -e "${YELLOW}Waiting for function to be ready...${NC}"
sleep 5

# Test the function
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Function${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

TEST_PAYLOAD='{"prompt":"what is 5+5"}'
echo "Test payload: $TEST_PAYLOAD"
echo ""

TEST_RESPONSE=$(aws lambda invoke \
  --function-name $FUNCTION_NAME \
  --payload "$TEST_PAYLOAD" \
  --region $REGION \
  /tmp/wrapper_response.json 2>&1)

if [ -f /tmp/wrapper_response.json ]; then
    echo "Response:"
    cat /tmp/wrapper_response.json | jq '.'
    rm /tmp/wrapper_response.json
    echo ""
    echo -e "${GREEN}✅ Function test successful${NC}"
else
    echo -e "${YELLOW}⚠️  Could not test function${NC}"
    echo "$TEST_RESPONSE"
fi

# Return to scripts directory
cd "$SCRIPT_DIR"

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Next Steps${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "1. Add this Lambda as a Gateway Target:"
echo ""
echo "   Go to AWS Console:"
echo "   https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
echo ""
echo "   Gateway: dev-spark-gateway-0y5eyw5mag"
echo "   Click 'Add target'"
echo ""
echo "   Configuration:"
echo "   - Name: spark-agent"
echo "   - Type: Lambda"
echo "   - Lambda ARN: $FUNCTION_ARN"
echo "   - Tool Schema:"
echo ""
cat <<'EOF'
[
  {
    "name": "ask_agent",
    "description": "Ask Spark Supervisor Agent a natural language question about data processing",
    "inputSchema": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "Natural language query or question"
        }
      },
      "required": ["prompt"]
    }
  }
]
EOF
echo ""
echo "2. Test via Gateway:"
echo "   cd scripts"
echo "   ./list-gateway-tools.sh"
echo "   ./ask-gateway.sh \"what is 5+5\""
echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Function ARN: $FUNCTION_ARN"
echo ""
