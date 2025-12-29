#!/bin/bash

# Complete Spark Stack Deployment Script
# This script deploys the entire Spark Code Interpreter stack in us-east-1

set -e

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

# Deploy CloudFormation stack
echo -e "${YELLOW}Deploying CloudFormation stack...${NC}"

aws cloudformation deploy \
  --template-file ../cloudformation/spark-complete-stack.yml \
  --stack-name $STACK_NAME \
  --parameter-overrides \
    Environment=$ENVIRONMENT \
    VpcId=$VPC_ID \
    PrivateSubnetIds=$PRIVATE_SUBNETS \
    PublicSubnetIds=$PUBLIC_SUBNETS \
  --capabilities CAPABILITY_NAMED_IAM \
  --region $REGION \
  --no-fail-on-empty-changeset

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

cat > ../config/deployment-config.json <<EOF
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

echo -e "${GREEN}✅ Configuration file created: ../config/deployment-config.json${NC}"
echo ""

# Deploy Spark Lambda code
echo -e "${YELLOW}Deploying Spark Lambda code...${NC}"
cd ../agent-code/spark-on-lambda
./deploy.sh $LAMBDA_FUNCTION $REGION
cd ../../scripts

echo ""

# Deploy AgentCore agents
echo -e "${YELLOW}Deploying AgentCore agents...${NC}"
echo "This requires bedrock-agentcore CLI to be installed"
echo "Run: pip install bedrock-agentcore-starter-toolkit"
echo ""
echo "Then deploy agents:"
echo "  1. Code Generation Agent"
echo "  2. Spark Supervisor Agent"
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
echo "1. Deploy AgentCore agents (see ../docs/AGENT_DEPLOYMENT.md)"
echo "2. Update backend configuration with agent ARNs"
echo "3. Deploy backend Lambda function"
echo "4. Test the deployment"
echo ""
echo -e "${GREEN}Deployment complete!${NC}"
