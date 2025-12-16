#!/bin/bash

# Configuration Update Script
# Updates configuration values in the deployed system

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
REGION="us-east-1"
ENVIRONMENT="dev"
CONFIG_FILE="../config/deployment-config.json"

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --lambda-function NAME      Update Lambda function name"
    echo "  --emr-app-id ID            Update EMR application ID"
    echo "  --s3-bucket NAME           Update S3 bucket name"
    echo "  --bedrock-model ID         Update Bedrock model ID"
    echo "  --code-gen-agent ARN       Update code generation agent ARN"
    echo "  --supervisor-agent ARN     Update supervisor agent ARN"
    echo "  --region REGION            AWS region (default: us-east-1)"
    echo "  --environment ENV          Environment (default: dev)"
    echo "  --help                     Display this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --lambda-function new-spark-lambda"
    echo "  $0 --emr-app-id 00g1k848jaqqjf09 --region us-east-1"
    echo "  $0 --bedrock-model us.anthropic.claude-haiku-4-5-20251001-v1:0"
    exit 1
}

# Parse command line arguments
LAMBDA_FUNCTION=""
EMR_APP_ID=""
S3_BUCKET=""
BEDROCK_MODEL=""
CODE_GEN_AGENT=""
SUPERVISOR_AGENT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --lambda-function)
            LAMBDA_FUNCTION="$2"
            shift 2
            ;;
        --emr-app-id)
            EMR_APP_ID="$2"
            shift 2
            ;;
        --s3-bucket)
            S3_BUCKET="$2"
            shift 2
            ;;
        --bedrock-model)
            BEDROCK_MODEL="$2"
            shift 2
            ;;
        --code-gen-agent)
            CODE_GEN_AGENT="$2"
            shift 2
            ;;
        --supervisor-agent)
            SUPERVISOR_AGENT="$2"
            shift 2
            ;;
        --region)
            REGION="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            usage
            ;;
    esac
done

# Check if at least one option is provided
if [ -z "$LAMBDA_FUNCTION" ] && [ -z "$EMR_APP_ID" ] && [ -z "$S3_BUCKET" ] && \
   [ -z "$BEDROCK_MODEL" ] && [ -z "$CODE_GEN_AGENT" ] && [ -z "$SUPERVISOR_AGENT" ]; then
    echo -e "${RED}Error: At least one configuration option must be provided${NC}"
    usage
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Configuration Update${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# Load current configuration
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}Error: Configuration file not found: $CONFIG_FILE${NC}"
    exit 1
fi

echo "Loading current configuration from $CONFIG_FILE"
echo ""

# Update Lambda function
if [ -n "$LAMBDA_FUNCTION" ]; then
    echo -e "${YELLOW}Updating Lambda function name...${NC}"
    
    # Verify function exists
    if aws lambda get-function --function-name "$LAMBDA_FUNCTION" --region "$REGION" &>/dev/null; then
        echo "✅ Lambda function verified: $LAMBDA_FUNCTION"
        
        # Update config file
        jq --arg fn "$LAMBDA_FUNCTION" '.lambda_function = $fn' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
        mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
        
        # Update backend config
        if [ -f "../backend/config_snowflake.py" ]; then
            sed -i.bak "s/\"lambda_function\": \"[^\"]*\"/\"lambda_function\": \"$LAMBDA_FUNCTION\"/" ../backend/config_snowflake.py
            echo "✅ Updated backend configuration"
        fi
    else
        echo -e "${RED}❌ Lambda function not found: $LAMBDA_FUNCTION${NC}"
        exit 1
    fi
    echo ""
fi

# Update EMR application ID
if [ -n "$EMR_APP_ID" ]; then
    echo -e "${YELLOW}Updating EMR application ID...${NC}"
    
    # Verify application exists
    if aws emr-serverless get-application --application-id "$EMR_APP_ID" --region "$REGION" &>/dev/null; then
        echo "✅ EMR application verified: $EMR_APP_ID"
        
        # Update config file
        jq --arg id "$EMR_APP_ID" '.emr_application_id = $id' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
        mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
        
        # Update backend config
        if [ -f "../backend/config_snowflake.py" ]; then
            sed -i.bak "s/\"emr_application_id\": \"[^\"]*\"/\"emr_application_id\": \"$EMR_APP_ID\"/" ../backend/config_snowflake.py
            echo "✅ Updated backend configuration"
        fi
    else
        echo -e "${RED}❌ EMR application not found: $EMR_APP_ID${NC}"
        exit 1
    fi
    echo ""
fi

# Update S3 bucket
if [ -n "$S3_BUCKET" ]; then
    echo -e "${YELLOW}Updating S3 bucket name...${NC}"
    
    # Verify bucket exists
    if aws s3 ls "s3://$S3_BUCKET" --region "$REGION" &>/dev/null; then
        echo "✅ S3 bucket verified: $S3_BUCKET"
        
        # Update config file
        jq --arg bucket "$S3_BUCKET" '.s3_bucket = $bucket' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
        mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
        
        # Update backend config
        if [ -f "../backend/config_snowflake.py" ]; then
            sed -i.bak "s/\"s3_bucket\": \"[^\"]*\"/\"s3_bucket\": \"$S3_BUCKET\"/" ../backend/config_snowflake.py
            echo "✅ Updated backend configuration"
        fi
    else
        echo -e "${RED}❌ S3 bucket not found: $S3_BUCKET${NC}"
        exit 1
    fi
    echo ""
fi

# Update Bedrock model
if [ -n "$BEDROCK_MODEL" ]; then
    echo -e "${YELLOW}Updating Bedrock model ID...${NC}"
    echo "Model: $BEDROCK_MODEL"
    
    # Update config file
    jq --arg model "$BEDROCK_MODEL" '.bedrock_model = $model' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    
    # Update backend config
    if [ -f "../backend/config_snowflake.py" ]; then
        sed -i.bak "s/\"bedrock_model\": \"[^\"]*\"/\"bedrock_model\": \"$BEDROCK_MODEL\"/" ../backend/config_snowflake.py
        echo "✅ Updated backend configuration"
    fi
    echo ""
fi

# Update code generation agent ARN
if [ -n "$CODE_GEN_AGENT" ]; then
    echo -e "${YELLOW}Updating code generation agent ARN...${NC}"
    echo "ARN: $CODE_GEN_AGENT"
    
    # Update config file
    jq --arg arn "$CODE_GEN_AGENT" '.code_gen_agent_arn = $arn' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    
    # Update backend config
    if [ -f "../backend/config_snowflake.py" ]; then
        sed -i.bak "s|\"code_gen_agent_arn\": \"[^\"]*\"|\"code_gen_agent_arn\": \"$CODE_GEN_AGENT\"|" ../backend/config_snowflake.py
        echo "✅ Updated backend configuration"
    fi
    echo ""
fi

# Update supervisor agent ARN
if [ -n "$SUPERVISOR_AGENT" ]; then
    echo -e "${YELLOW}Updating supervisor agent ARN...${NC}"
    echo "ARN: $SUPERVISOR_AGENT"
    
    # Update config file
    jq --arg arn "$SUPERVISOR_AGENT" '.spark_supervisor_arn = $arn' "$CONFIG_FILE" > "${CONFIG_FILE}.tmp"
    mv "${CONFIG_FILE}.tmp" "$CONFIG_FILE"
    
    # Update backend config
    if [ -f "../backend/config_snowflake.py" ]; then
        sed -i.bak "s|\"supervisor_arn\": \"[^\"]*\"|\"supervisor_arn\": \"$SUPERVISOR_AGENT\"|" ../backend/config_snowflake.py
        echo "✅ Updated backend configuration"
    fi
    echo ""
fi

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Configuration Updated Successfully${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Updated configuration saved to: $CONFIG_FILE"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Review the updated configuration"
echo "2. Redeploy backend if needed"
echo "3. Test the changes"
echo ""

# Display updated configuration
echo "Current configuration:"
cat "$CONFIG_FILE" | jq '.'

echo ""
echo -e "${GREEN}Update complete!${NC}"
