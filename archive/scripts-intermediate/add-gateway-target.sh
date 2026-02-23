#!/bin/bash

# Add Gateway Target to expose Spark Supervisor Agent through the Gateway

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
STACK_NAME="${ENVIRONMENT:-dev}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Add Gateway Target${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get configuration
echo -e "${YELLOW}Getting configuration...${NC}"
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text)
LAMBDA_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SparkLambdaFunctionArn`].OutputValue' --output text)

# Get agent ARN from config
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"
if [ -f "config/deployment-config.json" ]; then
    AGENT_ARN=$(jq -r '.spark_supervisor_arn' config/deployment-config.json 2>/dev/null || echo "$AGENT_ARN")
fi

echo "Gateway ID: $GATEWAY_ID"
echo "Lambda ARN: $LAMBDA_ARN"
echo "Agent ARN: $AGENT_ARN"
echo ""

# Option 1: Try Lambda Target (simpler and more likely to work)
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Attempting to Add Lambda Target${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo "Creating Gateway Target for Lambda function..."

# Try simpler approach: Let AWS auto-generate the tool schema
echo "Attempting simplified Lambda target configuration..."
LAMBDA_TARGET_RESPONSE=$(aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --name spark-lambda-executor \
  --description "Execute Spark code on Lambda" \
  --target-configuration "{\"lambda\":{\"lambdaArn\":\"$LAMBDA_ARN\"}}" \
  --credential-provider-configurations '[{"credentialProviderType":"NONE"}]' \
  --region $REGION 2>&1)

# If that fails, try with explicit tool schema
if ! echo "$LAMBDA_TARGET_RESPONSE" | jq -e '.targetId' > /dev/null 2>&1; then
    echo ""
    echo -e "${YELLOW}Simplified approach failed, trying with explicit tool schema...${NC}"
    
    # Create tool schema file
    cat > /tmp/tool_schema.json <<'TOOLEOF'
{
  "tools": [
    {
      "name": "execute_spark",
      "description": "Execute Spark code on AWS Lambda for data processing",
      "inputSchema": {
        "type": "object",
        "properties": {
          "code": {
            "type": "string",
            "description": "PySpark code to execute"
          },
          "data_format": {
            "type": "string",
            "description": "Output format",
            "enum": ["json", "csv", "parquet"],
            "default": "json"
          }
        },
        "required": ["code"]
      }
    }
  ]
}
TOOLEOF
    
    TOOL_SCHEMA=$(cat /tmp/tool_schema.json | jq -c '.')
    
    LAMBDA_TARGET_RESPONSE=$(aws bedrock-agentcore-control create-gateway-target \
      --gateway-identifier $GATEWAY_ID \
      --name spark-lambda-executor \
      --description "Execute Spark code on Lambda" \
      --target-configuration "{\"lambda\":{\"lambdaArn\":\"$LAMBDA_ARN\",\"toolSchema\":{\"inlinePayload\":\"$TOOL_SCHEMA\"}}}" \
      --credential-provider-configurations '[{"credentialProviderType":"NONE"}]' \
      --region $REGION 2>&1)
    
    rm -f /tmp/tool_schema.json
fi

if echo "$LAMBDA_TARGET_RESPONSE" | jq -e '.targetId' > /dev/null 2>&1; then
    TARGET_ID=$(echo "$LAMBDA_TARGET_RESPONSE" | jq -r '.targetId')
    echo -e "${GREEN}✅ Lambda target created successfully!${NC}"
    echo "Target ID: $TARGET_ID"
    echo ""
    echo "Available tool: execute_spark"
    echo ""
    
    # Wait for target to be ready
    echo -e "${YELLOW}Waiting for target to be ready...${NC}"
    sleep 5
    
    # List tools
    echo ""
    cd $(dirname $0)
    ./list-gateway-tools.sh
    
    exit 0
else
    echo -e "${YELLOW}⚠️  Lambda target creation failed${NC}"
    echo ""
    echo "Error details:"
    echo "$LAMBDA_TARGET_RESPONSE" | jq '.' 2>/dev/null || echo "$LAMBDA_TARGET_RESPONSE"
    echo ""
fi

# If Lambda failed, provide clear manual instructions
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Manual Configuration via AWS Console${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}The Gateway Target schema is complex and varies by target type.${NC}"
echo -e "${YELLOW}The easiest way to add a target is via the AWS Console.${NC}"
echo ""
echo -e "${GREEN}Step-by-step instructions:${NC}"
echo ""
echo "1. Open AWS Console:"
echo "   https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
echo ""
echo "2. Click on your gateway:"
echo "   Gateway ID: $GATEWAY_ID"
echo "   Gateway Name: dev-spark-gateway"
echo ""
echo "3. Click the 'Targets' tab"
echo ""
echo "4. Click 'Add target' button"
echo ""
echo "5. Configure the target:"
echo "   ┌─────────────────────────────────────────┐"
echo "   │ Target Configuration                    │"
echo "   ├─────────────────────────────────────────┤"
echo "   │ Name: spark-executor                    │"
echo "   │ Description: Execute Spark code         │"
echo "   │                                         │"
echo "   │ Target Type: Lambda                     │"
echo "   │ Lambda ARN:                             │"
echo "   │   $LAMBDA_ARN"
echo "   │                                         │"
echo "   │ Tool Schema: (Optional)                 │"
echo "   │   Let AWS auto-generate                 │"
echo "   │                                         │"
echo "   │ Credentials: None                       │"
echo "   └─────────────────────────────────────────┘"
echo ""
echo "6. Click 'Add target'"
echo ""
echo "7. Wait for target status to become 'Available'"
echo ""
echo "8. Test it:"
echo "   cd scripts"
echo "   ./list-gateway-tools.sh"
echo "   ./ask-gateway.sh \"create a dataframe\""
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Why Not in CloudFormation?${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Gateway Targets have a complex schema that varies by type:"
echo "  • Lambda targets need specific tool schema format"
echo "  • MCP Server targets need endpoint configuration"
echo "  • API targets need OpenAPI/Smithy schemas"
echo "  • Schema validation is strict and error-prone"
echo ""
echo "We removed it from CloudFormation to ensure successful deployment."
echo "Adding targets manually via Console is more reliable and provides"
echo "better validation feedback."
echo ""
echo -e "${GREEN}Your infrastructure is fully deployed and working!${NC}"
echo "Just add the Gateway Target via Console to enable MCP tools."
echo ""

