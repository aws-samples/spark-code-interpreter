#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Automated Deployment - Spark AgentCore Gateway${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR/.."

# Verify AWS credentials
echo -e "${YELLOW}Step 0: Verifying AWS credentials...${NC}"
if ! aws sts get-caller-identity &>/dev/null; then
    echo -e "${RED}❌ AWS credentials are not valid or expired${NC}"
    echo "Please run: aws configure"
    echo "Or: aws sso login --profile your-profile"
    exit 1
fi

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✅ AWS Account: $ACCOUNT_ID${NC}"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ python3 not found${NC}"
    exit 1
fi
echo "✅ python3 found"

if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq not found. Please install: brew install jq${NC}"
    exit 1
fi
echo "✅ jq found"

if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ docker not found${NC}"
    exit 1
fi
echo "✅ docker found"

# Check if bedrock-agentcore-starter-toolkit is installed
if ! python3 -c "import bedrock_agentcore_starter_toolkit" &>/dev/null; then
    echo -e "${YELLOW}Installing bedrock-agentcore-starter-toolkit...${NC}"
    pip3 install --upgrade bedrock-agentcore-starter-toolkit
fi
echo "✅ bedrock-agentcore-starter-toolkit installed"
echo ""

# ============================================================================
# STEP 1: Deploy Spark Supervisor Agent
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Deploying Spark Supervisor Agent${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd agent-code/spark-supervisor-agent

echo "Deploying agent..."
python3 agent_deployment.py > /tmp/spark_supervisor_deploy.log 2>&1

# Extract ARN from deployment
SPARK_SUPERVISOR_ARN=$(grep -o 'arn:aws:bedrock-agentcore:[^"]*' /tmp/spark_supervisor_deploy.log | head -1)

if [ -z "$SPARK_SUPERVISOR_ARN" ]; then
    echo -e "${RED}❌ Failed to get Spark Supervisor Agent ARN${NC}"
    echo "Check logs: /tmp/spark_supervisor_deploy.log"
    cat /tmp/spark_supervisor_deploy.log
    exit 1
fi

echo -e "${GREEN}✅ Spark Supervisor Agent deployed${NC}"
echo "ARN: $SPARK_SUPERVISOR_ARN"
echo ""

# Wait for agent to be ready
echo "Waiting 30 seconds for agent to be fully ready..."
sleep 30

# ============================================================================
# STEP 2: Deploy Code Generation Agent
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Deploying Code Generation Agent${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd ../../agent-code/code-generation-agent

echo "Deploying agent..."
python3 agent_deployment.py > /tmp/code_gen_deploy.log 2>&1

# Extract ARN from deployment
CODE_GEN_ARN=$(grep -o 'arn:aws:bedrock-agentcore:[^"]*' /tmp/code_gen_deploy.log | head -1)

if [ -z "$CODE_GEN_ARN" ]; then
    echo -e "${RED}❌ Failed to get Code Generation Agent ARN${NC}"
    echo "Check logs: /tmp/code_gen_deploy.log"
    cat /tmp/code_gen_deploy.log
    exit 1
fi

echo -e "${GREEN}✅ Code Generation Agent deployed${NC}"
echo "ARN: $CODE_GEN_ARN"
echo ""

# Wait for agent to be ready
echo "Waiting 30 seconds for agent to be fully ready..."
sleep 30

# ============================================================================
# STEP 3: Update CloudFormation Template
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Updating CloudFormation Template${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd ../../

# Backup original template
cp cloudformation/spark-complete-stack.yml cloudformation/spark-complete-stack.yml.backup

# Update AgentRuntimeArn in CloudFormation template
echo "Updating AgentRuntimeArn in CloudFormation template..."
sed -i.bak "s|AgentRuntimeArn: !Sub 'arn:aws:bedrock-agentcore:\${AWS::Region}:\${AWS::AccountId}:runtime/spark_supervisor_agent-\*'|AgentRuntimeArn: '$SPARK_SUPERVISOR_ARN'|g" cloudformation/spark-complete-stack.yml

echo -e "${GREEN}✅ CloudFormation template updated${NC}"
echo ""

# ============================================================================
# STEP 4: Update Configuration File
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 4: Updating Configuration File${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Backup original config
cp backend/backend/config_snowflake.py backend/backend/config_snowflake.py.backup

# Update config with ARNs
echo "Updating config_snowflake.py with agent ARNs..."
sed -i.bak "s|\"supervisor_arn\": os.getenv(\"SPARK_SUPERVISOR_ARN\", \"[^\"]*\")|\"supervisor_arn\": os.getenv(\"SPARK_SUPERVISOR_ARN\", \"$SPARK_SUPERVISOR_ARN\")|g" backend/backend/config_snowflake.py
sed -i.bak "s|\"code_gen_agent_arn\": os.getenv(\"CODE_GEN_AGENT_ARN\", \"[^\"]*\")|\"code_gen_agent_arn\": os.getenv(\"CODE_GEN_AGENT_ARN\", \"$CODE_GEN_ARN\")|g" backend/backend/config_snowflake.py

echo -e "${GREEN}✅ Configuration file updated${NC}"
echo ""

# ============================================================================
# STEP 5: Deploy Infrastructure
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 5: Deploying Infrastructure${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get VPC and subnet information
echo "Getting VPC and subnet information..."
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ No default VPC found${NC}"
    exit 1
fi
echo "VPC ID: $VPC_ID"

# Get subnets
PRIVATE_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[?MapPublicIpOnLaunch==`false`].SubnetId' --output text | tr '\t' ',')
PUBLIC_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[?MapPublicIpOnLaunch==`true`].SubnetId' --output text | tr '\t' ',')

if [ -z "$PRIVATE_SUBNETS" ]; then
    echo -e "${YELLOW}⚠️  No private subnets found, using all subnets${NC}"
    PRIVATE_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')
fi

if [ -z "$PUBLIC_SUBNETS" ]; then
    echo -e "${YELLOW}⚠️  No public subnets found, using all subnets${NC}"
    PUBLIC_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')
fi

echo "Private Subnets: $PRIVATE_SUBNETS"
echo "Public Subnets: $PUBLIC_SUBNETS"
echo ""

# Build and push Spark Lambda Docker image
echo "Building and pushing Spark Lambda Docker image..."
DOCKER_DIR="./Docker"
ECR_REPO_NAME="${ENVIRONMENT}-spark-lambda"

if [ -d "$DOCKER_DIR" ]; then
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
        aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
    
    # Get ECR login
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Build Docker image
    cd $DOCKER_DIR
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest"
    
    docker buildx create --use --name lambda-builder 2>/dev/null || docker buildx use lambda-builder
    docker buildx build \
        --platform linux/amd64 \
        --build-arg FRAMEWORK="" \
        --build-arg AWS_REGION=$REGION \
        -t $IMAGE_URI \
        --push \
        --provenance=false \
        --sbom=false \
        . > /tmp/docker_build.log 2>&1
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Docker build failed${NC}"
        cat /tmp/docker_build.log
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker image built and pushed${NC}"
    cd - > /dev/null
fi

echo ""
echo "Deploying CloudFormation stack (this takes 15-20 minutes)..."

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>&1 | grep -c "does not exist" || true)

if [ "$STACK_EXISTS" -gt 0 ]; then
    # Create new stack
    echo "Creating new stack..."
    aws cloudformation create-stack \
      --stack-name $STACK_NAME \
      --template-body file://cloudformation/spark-complete-stack.yml \
      --parameters \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=VpcId,ParameterValue=$VPC_ID" \
        "ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\"" \
        "ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\"" \
      --capabilities CAPABILITY_NAMED_IAM \
      --region $REGION
    
    echo "Waiting for stack creation to complete..."
    aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION
else
    # Update existing stack
    echo "Updating existing stack..."
    aws cloudformation update-stack \
      --stack-name $STACK_NAME \
      --template-body file://cloudformation/spark-complete-stack.yml \
      --parameters \
        "ParameterKey=Environment,ParameterValue=$ENVIRONMENT" \
        "ParameterKey=VpcId,ParameterValue=$VPC_ID" \
        "ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\"" \
        "ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\"" \
      --capabilities CAPABILITY_NAMED_IAM \
      --region $REGION 2>&1 | tee /tmp/cf-update.log
    
    # Check if no updates needed
    if grep -q "No updates are to be performed" /tmp/cf-update.log; then
        echo -e "${YELLOW}No updates needed${NC}"
    else
        echo "Waiting for stack update to complete..."
        aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION
    fi
fi

echo -e "${GREEN}✅ CloudFormation stack deployed${NC}"
echo ""

# Wait for resources to be fully ready
echo "Waiting 60 seconds for all resources to be fully ready..."
sleep 60

# ============================================================================
# STEP 6: Get Stack Outputs
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 6: Retrieving Stack Outputs${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get outputs
GATEWAY_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' --output text 2>/dev/null || echo "")
GATEWAY_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' --output text 2>/dev/null || echo "")
GATEWAY_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayArn`].OutputValue' --output text 2>/dev/null || echo "")
USER_POOL_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' --output text)
APP_CLIENT_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' --output text)
S3_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SparkDataBucketName`].OutputValue' --output text)
EMR_APP_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`EMRApplicationId`].OutputValue' --output text)

echo "Gateway ID: $GATEWAY_ID"
echo "Gateway ARN: $GATEWAY_ARN"
echo "Gateway URL: $GATEWAY_URL"
echo "Cognito User Pool ID: $USER_POOL_ID"
echo "Cognito App Client ID: $APP_CLIENT_ID"
echo "S3 Bucket: $S3_BUCKET"
echo "EMR Application ID: $EMR_APP_ID"
echo ""

# Save configuration
mkdir -p config
cat > config/deployment-config.json <<EOF
{
  "account_id": "$ACCOUNT_ID",
  "region": "$REGION",
  "environment": "$ENVIRONMENT",
  "spark_supervisor_arn": "$SPARK_SUPERVISOR_ARN",
  "code_gen_agent_arn": "$CODE_GEN_ARN",
  "gateway_id": "$GATEWAY_ID",
  "gateway_arn": "$GATEWAY_ARN",
  "gateway_url": "$GATEWAY_URL",
  "cognito_user_pool_id": "$USER_POOL_ID",
  "cognito_app_client_id": "$APP_CLIENT_ID",
  "s3_bucket": "$S3_BUCKET",
  "emr_application_id": "$EMR_APP_ID"
}
EOF

echo -e "${GREEN}✅ Configuration saved to config/deployment-config.json${NC}"
echo ""

# ============================================================================
# STEP 7: Create Test User (Optional)
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 7: Creating Test User (Optional)${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

read -p "Do you want to create a test user? (y/n): " CREATE_USER

if [ "$CREATE_USER" == "y" ] || [ "$CREATE_USER" == "Y" ]; then
    read -p "Email address: " TEST_EMAIL
    read -sp "Password (min 8 chars, uppercase, lowercase, number, symbol): " TEST_PASSWORD
    echo ""
    
    echo "Creating user..."
    aws cognito-idp admin-create-user \
        --user-pool-id $USER_POOL_ID \
        --username $TEST_EMAIL \
        --user-attributes Name=email,Value=$TEST_EMAIL Name=email_verified,Value=true \
        --message-action SUPPRESS \
        --region $REGION
    
    aws cognito-idp admin-set-user-password \
        --user-pool-id $USER_POOL_ID \
        --username $TEST_EMAIL \
        --password "$TEST_PASSWORD" \
        --permanent \
        --region $REGION
    
    echo -e "${GREEN}✅ Test user created: $TEST_EMAIL${NC}"
    echo ""
    
    # Get JWT token
    echo "Getting JWT token..."
    AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
        --auth-flow USER_PASSWORD_AUTH \
        --client-id $APP_CLIENT_ID \
        --auth-parameters USERNAME=$TEST_EMAIL,PASSWORD=$TEST_PASSWORD \
        --region $REGION \
        --output json 2>&1)
    
    if [ $? -eq 0 ]; then
        JWT_TOKEN=$(echo $AUTH_RESPONSE | jq -r '.AuthenticationResult.IdToken')
        
        if [ "$JWT_TOKEN" != "null" ] && [ -n "$JWT_TOKEN" ]; then
            echo -e "${GREEN}✅ JWT token obtained${NC}"
            echo ""
            echo "JWT Token:"
            echo "$JWT_TOKEN"
            echo ""
            
            # Save token to file
            echo "$JWT_TOKEN" > /tmp/jwt_token.txt
            echo "Token saved to: /tmp/jwt_token.txt"
            echo ""
            
            # Test the gateway
            echo "Testing gateway..."
            if [ -n "$GATEWAY_URL" ]; then
                # For MCP gateway, we need to use the bedrock-agentcore API
                echo "Gateway is MCP-based. Use MCP client to test."
                echo "Example MCP config:"
                echo "{"
                echo "  \"mcpServers\": {"
                echo "    \"spark-gateway\": {"
                echo "      \"url\": \"$GATEWAY_URL\","
                echo "      \"headers\": {"
                echo "        \"Authorization\": \"Bearer $JWT_TOKEN\""
                echo "      }"
                echo "    }"
                echo "  }"
                echo "}"
            fi
        else
            echo -e "${YELLOW}⚠️  Failed to get JWT token${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  Authentication failed${NC}"
        echo "$AUTH_RESPONSE"
    fi
else
    echo "Skipping test user creation"
fi

echo ""

# ============================================================================
# DEPLOYMENT COMPLETE
# ============================================================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}🎉 Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "${YELLOW}Summary:${NC}"
echo "✅ Spark Supervisor Agent: $SPARK_SUPERVISOR_ARN"
echo "✅ Code Generation Agent: $CODE_GEN_ARN"
echo "✅ AgentCore Gateway: $GATEWAY_ID"
echo "✅ Gateway URL: $GATEWAY_URL"
echo "✅ Cognito User Pool: $USER_POOL_ID"
echo "✅ S3 Bucket: $S3_BUCKET"
echo "✅ EMR Application: $EMR_APP_ID"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Create additional users: cd backend/backend && ./create-test-user.sh"
echo "2. Get JWT tokens: cd backend/backend && ./get-jwt-token.sh"
echo "3. Configure MCP client with: $GATEWAY_URL"
echo "4. View logs: aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow"
echo ""
echo -e "${YELLOW}Configuration saved to:${NC}"
echo "- config/deployment-config.json"
echo "- /tmp/jwt_token.txt (if test user created)"
echo ""
echo -e "${GREEN}All done! 🚀${NC}"
