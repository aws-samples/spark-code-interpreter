#!/bin/bash

# Complete Stack Deployment Script
# Deploys CloudFormation stack with Spark Lambda Docker image
# Prerequisites: Agents must be deployed first (run deploy-agents.sh)

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Complete Stack Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}❌ AWS CLI required${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker required${NC}"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo -e "${RED}❌ jq required${NC}"; exit 1; }
echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Get agent ARNs from config
CONFIG_FILE="config/deployment-config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Config file not found: $CONFIG_FILE${NC}"
    echo "Run ./scripts/deploy-agents.sh first to deploy agents"
    exit 1
fi

SUPERVISOR_ARN=$(jq -r '.spark.supervisor_arn // .spark_supervisor_arn // empty' $CONFIG_FILE 2>/dev/null)
CODE_GEN_ARN=$(jq -r '.global.code_gen_agent_arn // .code_gen_agent_arn // empty' $CONFIG_FILE 2>/dev/null)

if [ -z "$SUPERVISOR_ARN" ] || [ -z "$CODE_GEN_ARN" ]; then
    echo -e "${RED}❌ Agent ARNs not found in config${NC}"
    echo "Run ./scripts/deploy-agents.sh first"
    exit 1
fi

echo -e "${GREEN}✅ Agent ARNs loaded${NC}"
echo "  Supervisor: ${SUPERVISOR_ARN:0:50}..."
echo "  Code Gen: ${CODE_GEN_ARN:0:50}..."
echo ""

# Get VPC and Subnets
echo -e "${YELLOW}Getting VPC and subnet information...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ No default VPC found${NC}"
    exit 1
fi

PRIVATE_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')
PUBLIC_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')

echo "VPC: $VPC_ID"
echo "Private Subnets: $PRIVATE_SUBNETS"
echo "Public Subnets: $PUBLIC_SUBNETS"
echo ""

# Build and push Spark Lambda Docker image
echo -e "${YELLOW}Step 1: Building Spark Lambda Docker image...${NC}"
ECR_REPO_NAME="${ENVIRONMENT}-spark-lambda"

# Create ECR repository if needed
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION

echo -e "${GREEN}✅ ECR repository ready${NC}"

# Login to ECR
aws ecr get-login-password --region $REGION | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build and push with buildx (single command)
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest"

echo "Building for linux/amd64 (Lambda platform)..."
docker buildx create --use --name lambda-builder 2>/dev/null || docker buildx use lambda-builder

docker buildx build \
    --platform linux/amd64 \
    --build-arg FRAMEWORK="" \
    --build-arg AWS_REGION=$REGION \
    -t $IMAGE_URI \
    --push \
    --provenance=false \
    --sbom=false \
    Docker/

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built and pushed${NC}"
echo ""

# Deploy CloudFormation stack
echo -e "${YELLOW}Step 2: Deploying CloudFormation stack...${NC}"

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>&1 | grep -c "does not exist" || true)

if [ "$STACK_EXISTS" -gt 0 ]; then
    echo "Creating new stack..."
    
    # Try to create stack, handle conflicts
    CREATE_OUTPUT=$(aws cloudformation create-stack \
        --stack-name $STACK_NAME \
        --template-body file://cloudformation/spark-complete-stack.yml \
        --parameters \
            ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
            ParameterKey=BedrockModel,ParameterValue=us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
            ParameterKey=SparkSupervisorAgentArn,ParameterValue=$SUPERVISOR_ARN \
            ParameterKey=CodeGenerationAgentArn,ParameterValue=$CODE_GEN_ARN \
            ParameterKey=VpcId,ParameterValue=$VPC_ID \
            ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\" \
            ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $REGION 2>&1) || {
        
        # Check if error is due to existing resources
        if echo "$CREATE_OUTPUT" | grep -q "already exists\|AlreadyExists"; then
            echo -e "${YELLOW}⚠️  Resources already exist from previous deployment${NC}"
            echo "Cleaning up orphaned resources..."
            
            # Clean up Lambda functions
            echo "  Deleting Lambda functions..."
            LAMBDA_FUNCTIONS=(
                "${ENVIRONMENT}-spark-on-lambda"
                "${ENVIRONMENT}-spark-agent-wrapper"
            )
            for func in "${LAMBDA_FUNCTIONS[@]}"; do
                aws lambda delete-function --function-name $func --region $REGION 2>/dev/null || true
            done
            
            # Clean up IAM roles
            echo "  Deleting IAM roles..."
            IAM_ROLES=(
                "${ENVIRONMENT}-spark-lambda-role"
                "${ENVIRONMENT}-spark-wrapper-lambda-role"
                "${ENVIRONMENT}-spark-emr-execution-role"
                "${ENVIRONMENT}-spark-gateway-role"
                "AmazonBedrockAgentCoreSDKRuntime-${REGION}-${ENVIRONMENT}"
            )
            
            for role in "${IAM_ROLES[@]}"; do
                # Delete inline policies
                INLINE_POLICIES=$(aws iam list-role-policies --role-name $role --query 'PolicyNames' --output text 2>/dev/null || echo "")
                for policy in $INLINE_POLICIES; do
                    aws iam delete-role-policy --role-name $role --policy-name $policy 2>/dev/null || true
                done
                
                # Detach managed policies
                MANAGED_POLICIES=$(aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null || echo "")
                for policy_arn in $MANAGED_POLICIES; do
                    aws iam detach-role-policy --role-name $role --policy-arn $policy_arn 2>/dev/null || true
                done
                
                # Delete role
                aws iam delete-role --role-name $role 2>/dev/null || true
            done
            
            echo "  Waiting 10 seconds for resources to be fully deleted..."
            sleep 10
            
            echo "Retrying stack creation..."
            aws cloudformation create-stack \
                --stack-name $STACK_NAME \
                --template-body file://cloudformation/spark-complete-stack.yml \
                --parameters \
                    ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
                    ParameterKey=BedrockModel,ParameterValue=us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
                    ParameterKey=SparkSupervisorAgentArn,ParameterValue=$SUPERVISOR_ARN \
                    ParameterKey=CodeGenerationAgentArn,ParameterValue=$CODE_GEN_ARN \
                    ParameterKey=VpcId,ParameterValue=$VPC_ID \
                    ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\" \
                    ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\" \
                --capabilities CAPABILITY_NAMED_IAM \
                --region $REGION
        else
            echo -e "${RED}❌ Stack creation failed${NC}"
            echo "$CREATE_OUTPUT"
            exit 1
        fi
    }
    
    echo "Waiting for stack creation..."
    aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION
else
    echo "Updating existing stack..."
    aws cloudformation update-stack \
        --stack-name $STACK_NAME \
        --template-body file://cloudformation/spark-complete-stack.yml \
        --parameters \
            ParameterKey=Environment,ParameterValue=$ENVIRONMENT \
            ParameterKey=BedrockModel,ParameterValue=us.anthropic.claude-sonnet-4-5-20250929-v1:0 \
            ParameterKey=SparkSupervisorAgentArn,ParameterValue=$SUPERVISOR_ARN \
            ParameterKey=CodeGenerationAgentArn,ParameterValue=$CODE_GEN_ARN \
            ParameterKey=VpcId,ParameterValue=$VPC_ID \
            ParameterKey=PrivateSubnetIds,ParameterValue=\"$PRIVATE_SUBNETS\" \
            ParameterKey=PublicSubnetIds,ParameterValue=\"$PUBLIC_SUBNETS\" \
        --capabilities CAPABILITY_NAMED_IAM \
        --region $REGION 2>&1 | tee /tmp/cf-update.log
    
    if grep -q "No updates are to be performed" /tmp/cf-update.log; then
        echo -e "${YELLOW}No updates needed${NC}"
    else
        echo "Waiting for stack update..."
        aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION
    fi
fi

echo -e "${GREEN}✅ CloudFormation stack deployed${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Add Gateway Target (manual via Console)"
echo "   See DEPLOYMENT_GUIDE.md for instructions"
echo ""
echo "2. Test deployment:"
echo "   ./scripts/test-calculation.sh \"what is 7*10\""
echo ""
