#!/bin/bash

# Complete Spark Stack Deployment Script
# This script deploys the entire Spark Code Interpreter stack in us-east-1

set -e

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# Change to the parent directory (us-east-1-stable)
cd "$SCRIPT_DIR/.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
REGION="us-east-1"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Spark Code Interpreter - Complete Stack Deployment${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo "Stack Name: $STACK_NAME"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    echo -e "${RED}❌ AWS CLI not found. Please install it first.${NC}"
    exit 1
fi
echo "✅ AWS CLI installed"

# Check jq
if ! command -v jq &> /dev/null; then
    echo -e "${RED}❌ jq not found. Please install it first.${NC}"
    exit 1
fi
echo "✅ jq installed"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install it first.${NC}"
    exit 1
fi
echo "✅ Docker installed"

echo ""

# Get VPC and Subnet information
echo -e "${YELLOW}Getting VPC and Subnet information...${NC}"

# Get default VPC
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ No default VPC found. Please specify VPC_ID manually.${NC}"
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

# Build and push Spark Lambda Docker image BEFORE CloudFormation deployment
echo -e "${YELLOW}Building and pushing Spark Lambda Docker image...${NC}"
DOCKER_DIR="./Docker"
ECR_REPO_NAME="${ENVIRONMENT}-spark-lambda"

if [ -d "$DOCKER_DIR" ]; then
    # Create ECR repository if it doesn't exist
    aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
        aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION
    
    echo "✅ ECR repository ready: $ECR_REPO_NAME"
    
    # Get ECR login
    echo "Logging into ECR..."
    aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
    
    # Build Docker image for Lambda (AMD64 architecture)
    echo "Building Docker image for Lambda (AMD64 - this may take several minutes)..."
    cd $DOCKER_DIR
    
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest"
    
    # Use docker buildx for proper cross-platform build
    docker buildx create --use --name lambda-builder 2>/dev/null || docker buildx use lambda-builder
    
    docker buildx build \
        --platform linux/amd64 \
        --build-arg FRAMEWORK="" \
        --build-arg AWS_REGION=$REGION \
        -t $IMAGE_URI \
        --push \
        --provenance=false \
        --sbom=false \
        . 2>&1 | tail -n 30
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Docker build failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Docker image built and pushed to ECR${NC}"
    cd - > /dev/null
else
    echo -e "${RED}❌ Docker directory not found at $DOCKER_DIR${NC}"
    exit 1
fi

echo ""

# Check if stack exists and is in ROLLBACK_COMPLETE state
STACK_STATUS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].StackStatus' --output text 2>/dev/null || echo "DOES_NOT_EXIST")

if [ "$STACK_STATUS" == "ROLLBACK_COMPLETE" ]; then
    echo -e "${YELLOW}Stack is in ROLLBACK_COMPLETE state. Deleting it first...${NC}"
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    echo "Waiting for stack deletion to complete..."
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION
    echo -e "${GREEN}✅ Stack deleted successfully${NC}"
    echo ""
fi

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"

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

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ CloudFormation stack deployed successfully${NC}"
else
    echo -e "${RED}❌ CloudFormation stack deployment failed${NC}"
    exit 1
fi

echo ""

# Get stack outputs
echo -e "${YELLOW}Getting stack outputs...${NC}"

S3_BUCKET=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SparkDataBucketName`].OutputValue' --output text)
LAMBDA_FUNCTION=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`SparkLambdaFunctionName`].OutputValue' --output text)
EMR_APP_ID=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`EMRApplicationId`].OutputValue' --output text)
EMR_ROLE_ARN=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`EMRExecutionRoleArn`].OutputValue' --output text)
ALB_URL=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' --output text)

echo "S3 Bucket: $S3_BUCKET"
echo "Lambda Function: $LAMBDA_FUNCTION"
echo "EMR Application ID: $EMR_APP_ID"
echo "EMR Role ARN: $EMR_ROLE_ARN"
echo "ALB URL: $ALB_URL"
echo ""

# Create configuration file
echo -e "${YELLOW}Creating configuration file...${NC}"

cat > config/deployment-config.json <<EOF
{
  "account_id": "$ACCOUNT_ID",
  "region": "$REGION",
  "environment": "$ENVIRONMENT",
  "s3_bucket": "$S3_BUCKET",
  "lambda_function": "$LAMBDA_FUNCTION",
  "emr_application_id": "$EMR_APP_ID",
  "emr_execution_role_arn": "$EMR_ROLE_ARN",
  "alb_url": "$ALB_URL",
  "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}
EOF

echo -e "${GREEN}✅ Configuration file created: config/deployment-config.json${NC}"
echo ""

# Lambda function is already deployed with the Docker image from ECR
echo -e "${GREEN}✅ Spark Lambda function deployed with container image${NC}"
echo ""

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "✅ CloudFormation stack deployed"
echo "✅ S3 bucket created: $S3_BUCKET"
echo "✅ Lambda function created: $LAMBDA_FUNCTION"
echo "✅ EMR application created: $EMR_APP_ID"
echo "✅ ALB created: $ALB_URL"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Deploy AgentCore agents: ./deploy-agents.sh"
echo "2. Test the deployment: ./test-deployment.sh"
echo ""
echo -e "${GREEN}Infrastructure deployment complete!${NC}"
echo ""
echo -e "${YELLOW}Note: To deploy everything at once, use: ./deploy-all.sh${NC}"
