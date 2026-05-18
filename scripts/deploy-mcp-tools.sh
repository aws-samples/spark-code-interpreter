#!/bin/bash

# Deploy MCP Tool Lambdas and register them as Gateway targets
# Usage: ./scripts/deploy-mcp-tools.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --no-cli-pager)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deploy MCP Tool Lambdas${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Account: $ACCOUNT_ID"
echo ""

# Tool definitions: name, directory, timeout, memory
TOOLS=(
    "generate-spark-code:generate-spark-code:300:256"
    "execute-spark-on-lambda:execute-spark-on-lambda:320:256"
    "execute-spark-on-emr:execute-spark-on-emr:900:256"
    "get-glue-table-schema:get-glue-table-schema:60:256"
    "get-postgres-table-schema:get-postgres-table-schema:30:256"
    "fetch-spark-results:fetch-spark-results:60:256"
)

# Create or get the shared IAM role for MCP tool Lambdas
ROLE_NAME="${ENVIRONMENT}-spark-mcp-tools-role"
echo -e "${YELLOW}Setting up IAM role: $ROLE_NAME${NC}"

ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text --no-cli-pager 2>/dev/null || true)

if [ -z "$ROLE_ARN" ] || [ "$ROLE_ARN" == "None" ]; then
    echo "Creating IAM role..."
    TRUST_POLICY='{
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "lambda.amazonaws.com"},
            "Action": "sts:AssumeRole"
        }]
    }'

    ROLE_ARN=$(aws iam create-role \
        --role-name $ROLE_NAME \
        --assume-role-policy-document "$TRUST_POLICY" \
        --query 'Role.Arn' \
        --output text \
        --no-cli-pager)

    aws iam attach-role-policy \
        --role-name $ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole \
        --no-cli-pager

    # Add permissions for all tools
    TOOL_POLICY='{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["bedrock-agentcore:InvokeAgentRuntime"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["lambda:InvokeFunction"],
                "Resource": "arn:aws:lambda:'$REGION':'$ACCOUNT_ID':function:'$ENVIRONMENT'-spark-on-lambda"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "emr-serverless:StartJobRun",
                    "emr-serverless:GetJobRun"
                ],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["glue:GetTable", "glue:GetDatabase"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["secretsmanager:GetSecretValue"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": [
                    "s3:GetObject",
                    "s3:PutObject",
                    "s3:ListBucket"
                ],
                "Resource": [
                    "arn:aws:s3:::spark-data-'$ACCOUNT_ID'-'$REGION'",
                    "arn:aws:s3:::spark-data-'$ACCOUNT_ID'-'$REGION'/*"
                ]
            },
            {
                "Effect": "Allow",
                "Action": ["sts:GetCallerIdentity"],
                "Resource": "*"
            },
            {
                "Effect": "Allow",
                "Action": ["iam:PassRole"],
                "Resource": "arn:aws:iam::'$ACCOUNT_ID':role/*EMR*"
            }
        ]
    }'

    aws iam put-role-policy \
        --role-name $ROLE_NAME \
        --policy-name "${ENVIRONMENT}-spark-mcp-tools-policy" \
        --policy-document "$TOOL_POLICY" \
        --no-cli-pager

    echo "Waiting 10 seconds for IAM role propagation..."
    sleep 10
fi

echo -e "${GREEN}IAM Role: $ROLE_ARN${NC}"
echo ""

# Deploy each tool Lambda
for TOOL_DEF in "${TOOLS[@]}"; do
    IFS=':' read -r TOOL_NAME TOOL_DIR TIMEOUT MEMORY <<< "$TOOL_DEF"
    FUNCTION_NAME="${ENVIRONMENT}-spark-tool-${TOOL_NAME}"
    TOOL_PATH="${PROJECT_ROOT}/mcp-tools/${TOOL_DIR}"

    echo -e "${YELLOW}Deploying: $FUNCTION_NAME${NC}"
    echo "  Directory: $TOOL_PATH"
    echo "  Timeout: ${TIMEOUT}s, Memory: ${MEMORY}MB"

    # Create deployment package
    PACKAGE_DIR=$(mktemp -d)
    cp "${TOOL_PATH}/handler.py" "${PACKAGE_DIR}/"
    # Include shared progress helper if present
    if [ -f "${PROJECT_ROOT}/mcp-tools/progress.py" ]; then
        cp "${PROJECT_ROOT}/mcp-tools/progress.py" "${PACKAGE_DIR}/"
    fi

    # Install dependencies if requirements.txt has non-boto3 packages
    if grep -qvE "^boto3$|^$" "${TOOL_PATH}/requirements.txt" 2>/dev/null; then
        echo "  Installing dependencies..."
        pip install -r "${TOOL_PATH}/requirements.txt" -t "${PACKAGE_DIR}" --quiet --platform manylinux2014_x86_64 --only-binary=:all: 2>/dev/null || \
        pip install -r "${TOOL_PATH}/requirements.txt" -t "${PACKAGE_DIR}" --quiet 2>/dev/null || true
    fi

    # Create zip
    ZIP_FILE="/tmp/${FUNCTION_NAME}.zip"
    rm -f "$ZIP_FILE"
    (cd "$PACKAGE_DIR" && zip -r "$ZIP_FILE" . -x "*.pyc" "__pycache__/*" "boto3/*" "botocore/*" "s3transfer/*" "urllib3/*" > /dev/null 2>&1)

    # Create or update Lambda function
    EXISTING=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --no-cli-pager 2>/dev/null || true)

    if [ -z "$EXISTING" ]; then
        echo "  Creating Lambda function..."
        aws lambda create-function \
            --function-name "$FUNCTION_NAME" \
            --runtime python3.11 \
            --handler handler.lambda_handler \
            --role "$ROLE_ARN" \
            --zip-file "fileb://${ZIP_FILE}" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" \
            --no-cli-pager > /dev/null 2>&1
    else
        echo "  Updating Lambda function..."
        aws lambda update-function-code \
            --function-name "$FUNCTION_NAME" \
            --zip-file "fileb://${ZIP_FILE}" \
            --region "$REGION" \
            --no-cli-pager > /dev/null 2>&1

        # Wait for update to complete before updating config
        aws lambda wait function-updated \
            --function-name "$FUNCTION_NAME" \
            --region "$REGION" 2>/dev/null || true

        aws lambda update-function-configuration \
            --function-name "$FUNCTION_NAME" \
            --timeout "$TIMEOUT" \
            --memory-size "$MEMORY" \
            --region "$REGION" \
            --no-cli-pager > /dev/null 2>&1
    fi

    # Add permission for Gateway to invoke this Lambda
    aws lambda add-permission \
        --function-name "$FUNCTION_NAME" \
        --statement-id "AllowGatewayInvoke" \
        --action "lambda:InvokeFunction" \
        --principal "bedrock-agentcore.amazonaws.com" \
        --region "$REGION" \
        --no-cli-pager > /dev/null 2>&1 || true

    # Clean up
    rm -rf "$PACKAGE_DIR" "$ZIP_FILE"

    echo -e "  ${GREEN}✓ Deployed: $FUNCTION_NAME${NC}"
    echo ""
done

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}All MCP Tool Lambdas Deployed${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# List deployed functions
echo "Deployed Lambda functions:"
for TOOL_DEF in "${TOOLS[@]}"; do
    IFS=':' read -r TOOL_NAME TOOL_DIR TIMEOUT MEMORY <<< "$TOOL_DEF"
    FUNCTION_NAME="${ENVIRONMENT}-spark-tool-${TOOL_NAME}"
    ARN=$(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.FunctionArn' --output text --no-cli-pager 2>/dev/null || echo "NOT FOUND")
    echo "  $FUNCTION_NAME: $ARN"
done

echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Register Gateway targets (manual or via API)"
echo "  2. Update spark_supervisor_agent.py to use MCP tools"
echo "  3. Redeploy supervisor agent"
echo ""
