#!/bin/bash

# Complete Deployment Script
# Deploys everything: Agents + Docker + CloudFormation
# This is the ONE command to deploy the entire system

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
echo -e "${BLUE}Complete Spark System Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "This will deploy:"
echo "  1. Bedrock Agents (Spark Supervisor + Code Generation)"
echo "  2. Spark Lambda Docker Image"
echo "  3. CloudFormation Stack (Lambda, S3, Gateway, EMR)"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text --no-cli-pager)
echo "Account: $ACCOUNT_ID"
echo ""

# Check prerequisites
echo -e "${YELLOW}Checking prerequisites...${NC}"
command -v aws >/dev/null 2>&1 || { echo -e "${RED}❌ AWS CLI required${NC}"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo -e "${RED}❌ Docker required${NC}"; exit 1; }
command -v jq >/dev/null 2>&1 || { echo -e "${RED}❌ jq required${NC}"; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo -e "${RED}❌ Python 3 required${NC}"; exit 1; }
echo -e "${GREEN}✅ Prerequisites met${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# ============================================================================
# STEP 1: Deploy Bedrock Agents
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Deploying Bedrock Agents${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Check if bedrock-agentcore-starter-toolkit is installed
echo -e "${YELLOW}Checking bedrock-agentcore-starter-toolkit...${NC}"
if ! python3 -c "import bedrock_agentcore_starter_toolkit" 2>/dev/null; then
    echo "Installing bedrock-agentcore-starter-toolkit..."
    pip3 install bedrock-agentcore-starter-toolkit
fi
echo -e "${GREEN}✅ Toolkit ready${NC}"
echo ""

# Create config helper
CONFIG_DIR="$PROJECT_ROOT/agent-code"
cat > $CONFIG_DIR/deployment_config_helper.py <<'EOF'
import json
import os

CONFIG_FILE = os.path.join(os.path.dirname(__file__), '..', 'config', 'deployment-config.json')

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
EOF

# Deploy Spark Supervisor Agent
echo -e "${YELLOW}Deploying Spark Supervisor Agent...${NC}"
cd "$PROJECT_ROOT/agent-code/spark-supervisor-agent"

# Clean up stale config
if [ -f ".bedrock_agentcore.yaml" ]; then
    sed -i.bak '/agent_id:/d' .bedrock_agentcore.yaml 2>/dev/null || true
    sed -i.bak '/agent_arn:/d' .bedrock_agentcore.yaml 2>/dev/null || true
fi

# Copy custom Dockerfile with gcc support
if [ -f "Dockerfile.custom" ]; then
    cp Dockerfile.custom Dockerfile
    echo "Using custom Dockerfile with build tools"
fi

python3 agent_deployment.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Spark Supervisor Agent deployment failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Spark Supervisor Agent deployed (with IAM permissions)${NC}"
echo ""

# Wait for agent to be ready
echo -e "${YELLOW}Waiting for agent to be ready (10 seconds)...${NC}"
sleep 10

# Deploy Code Generation Agent
echo -e "${YELLOW}Deploying Code Generation Agent...${NC}"
cd "$PROJECT_ROOT/agent-code/code-generation-agent"

# Clean up stale config
if [ -f ".bedrock_agentcore.yaml" ]; then
    sed -i.bak '/agent_id:/d' .bedrock_agentcore.yaml 2>/dev/null || true
    sed -i.bak '/agent_arn:/d' .bedrock_agentcore.yaml 2>/dev/null || true
fi

# Copy custom Dockerfile with gcc support
if [ -f "Dockerfile.custom" ]; then
    cp Dockerfile.custom Dockerfile
    echo "Using custom Dockerfile with build tools"
fi

python3 agent_deployment.py
if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Code Generation Agent deployment failed${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Code Generation Agent deployed (with IAM permissions)${NC}"
echo ""

# Wait for agent to be ready
echo -e "${YELLOW}Waiting for agent to be ready (10 seconds)...${NC}"
sleep 10

# Load agent ARNs from config
CONFIG_FILE="$PROJECT_ROOT/config/deployment-config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Config file not created by agent deployment${NC}"
    exit 1
fi

SUPERVISOR_ARN=$(jq -r '.spark.supervisor_arn // .spark_supervisor_arn // empty' $CONFIG_FILE 2>/dev/null)
CODE_GEN_ARN=$(jq -r '.global.code_gen_agent_arn // .code_gen_agent_arn // empty' $CONFIG_FILE 2>/dev/null)

if [ -z "$SUPERVISOR_ARN" ] || [ -z "$CODE_GEN_ARN" ]; then
    echo -e "${RED}❌ Agent ARNs not found in config${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Agent ARNs loaded${NC}"
echo "  Supervisor: ${SUPERVISOR_ARN:0:60}..."
echo "  Code Gen: ${CODE_GEN_ARN:0:60}..."
echo ""

# ============================================================================
# STEP 2: Build and Push Spark Lambda Docker Image
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Building Spark Lambda${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"

ECR_REPO_NAME="${ENVIRONMENT}-spark-lambda"

# Check if ECR repository exists (CloudFormation should have created it)
echo -e "${YELLOW}Checking ECR repository...${NC}"
if aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION --no-cli-pager 2>/dev/null; then
    echo "Repository exists (created by CloudFormation or previous deployment)"
else
    echo -e "${YELLOW}⚠️  ECR repository not found. Creating manually...${NC}"
    echo "   (Note: CloudFormation should create this, but creating as fallback)"
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION --no-cli-pager 2>&1 | head -5 || true
fi
echo -e "${GREEN}✅ ECR repository ready${NC}"
echo ""

# Login to ECR
echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region $REGION --no-cli-pager 2>&1 | head -1 | \
    docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com > /dev/null 2>&1
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Logged in${NC}"
else
    echo -e "${YELLOW}⚠️  Login may have issues, continuing...${NC}"
fi
echo ""

# Build and push with buildx
IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest"

echo -e "${YELLOW}Building Docker image with --no-cache (this may take 5-10 minutes)...${NC}"
echo "Platform: linux/amd64 (Lambda requirement)"
echo "Includes: S3 write fix (hadoop-aws-3.3.4.jar + aws-java-sdk-bundle-1.12.261.jar)"
echo "Note: Using --no-cache to ensure fresh JAR downloads"
echo ""

# Ensure buildx builder exists
docker buildx create --use --name lambda-builder 2>/dev/null || docker buildx use lambda-builder 2>/dev/null || true

docker buildx build \
    --platform linux/amd64 \
    --no-cache \
    --build-arg FRAMEWORK="" \
    --build-arg AWS_REGION=$REGION \
    -t $IMAGE_URI \
    --push \
    --provenance=false \
    --sbom=false \
    Docker/ 2>&1 | grep -E "(#|=>|ERROR|error|Writing|Pushing|✓|✗|VERIFICATION)" | tail -50

if [ ${PIPESTATUS[0]} -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built and pushed${NC}"
echo ""

# ============================================================================
# STEP 2.5: Deploy MCP Tool Lambdas
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2.5: Deploying MCP Tool Lambdas${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"
bash scripts/deploy-mcp-tools.sh

echo ""

# ============================================================================
# STEP 3: Deploy CloudFormation Stack
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Deploying CloudFormation${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get VPC and Subnets
echo -e "${YELLOW}Getting VPC and subnet information...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text --no-cli-pager)

if [ "$VPC_ID" == "None" ] || [ -z "$VPC_ID" ]; then
    echo -e "${RED}❌ No default VPC found${NC}"
    exit 1
fi

PRIVATE_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text --no-cli-pager | tr '\t' ',')
PUBLIC_SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text --no-cli-pager | tr '\t' ',')

echo "VPC: $VPC_ID"
echo "Private Subnets: $PRIVATE_SUBNETS"
echo "Public Subnets: $PUBLIC_SUBNETS"
echo ""

# Check if stack exists
STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION --no-cli-pager 2>&1 | grep -c "does not exist" || true)

if [ "$STACK_EXISTS" -gt 0 ]; then
    echo -e "${YELLOW}Creating new CloudFormation stack...${NC}"
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
        --region $REGION \
        --no-cli-pager 2>&1 | head -10
    
    echo ""
    echo -e "${YELLOW}Waiting for stack creation (this may take 5-10 minutes)...${NC}"
    aws cloudformation wait stack-create-complete --stack-name $STACK_NAME --region $REGION --no-cli-pager 2>&1 | head -20
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Stack creation failed${NC}"
        echo "Check CloudFormation console for details"
        exit 1
    fi
else
    echo -e "${YELLOW}Updating existing CloudFormation stack...${NC}"
    UPDATE_OUTPUT=$(aws cloudformation update-stack \
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
        --region $REGION \
        --no-cli-pager 2>&1)
    
    if echo "$UPDATE_OUTPUT" | grep -q "No updates are to be performed"; then
        echo -e "${YELLOW}No updates needed${NC}"
    else
        echo "$UPDATE_OUTPUT" | head -10
        echo ""
        echo -e "${YELLOW}Waiting for stack update...${NC}"
        aws cloudformation wait stack-update-complete --stack-name $STACK_NAME --region $REGION --no-cli-pager 2>&1 | head -20
        
        if [ $? -ne 0 ]; then
            echo -e "${RED}❌ Stack update failed${NC}"
            echo "Check CloudFormation console for details"
            exit 1
        fi
    fi
fi

echo -e "${GREEN}✅ CloudFormation stack deployed${NC}"
echo ""

# ============================================================================
# STEP 3.5: Register MCP Gateway Targets
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3.5: Registering MCP Gateway Targets${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT"
python3 scripts/register-gateway-targets.py

echo ""

# ============================================================================
# STEP 4: Deploy Wrapper Lambda Code
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 4: Deploying Wrapper Lambda Code${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

cd "$PROJECT_ROOT/agent-wrapper"

echo -e "${YELLOW}Creating deployment package...${NC}"
zip -q agent_wrapper.zip agent_wrapper.py

echo -e "${YELLOW}Updating Lambda function code...${NC}"
aws lambda update-function-code \
    --function-name ${ENVIRONMENT}-spark-agent-wrapper \
    --zip-file fileb://agent_wrapper.zip \
    --region $REGION \
    --no-cli-pager 2>&1 | head -10

echo -e "${YELLOW}Waiting for Lambda to be ready...${NC}"
aws lambda wait function-updated \
    --function-name ${ENVIRONMENT}-spark-agent-wrapper \
    --region $REGION 2>&1 | head -10 || true

rm agent_wrapper.zip

echo -e "${GREEN}✅ Wrapper Lambda code deployed${NC}"
echo ""

cd "$PROJECT_ROOT"

# ============================================================================
# DEPLOYMENT COMPLETE
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete! 🎉${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Get stack outputs
echo -e "${YELLOW}Stack Outputs:${NC}"
aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
    --output table \
    --no-cli-pager

echo ""
echo -e "${GREEN}✅ All components deployed successfully!${NC}"
echo ""
echo -e "${YELLOW}What was deployed:${NC}"
echo "  ✅ Spark Supervisor Agent"
echo "  ✅ Code Generation Agent"
echo "  ✅ Spark Lambda (Docker)"
echo "  ✅ MCP Tool Lambdas (6)"
echo "  ✅ MCP Gateway Targets (6)"
echo "  ✅ Wrapper Lambda"
echo "  ✅ S3 Bucket"
echo "  ✅ AgentCore Gateway"
echo "  ✅ EMR Serverless"
echo "  ✅ Cognito User Pool"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Add Gateway Target (manual - CloudFormation doesn't support this yet)"
echo "   Go to: https://console.aws.amazon.com/bedrock/home?region=$REGION#/agentcore/gateways"
echo "   Select your gateway and add a Lambda target"
echo "   See DEPLOYMENT_GUIDE.md for detailed instructions"
echo ""
echo "2. Test the deployment:"
echo "   ./scripts/test-calculation.sh \"what is 7*10\""
echo ""
echo -e "${GREEN}Deployment completed successfully!${NC}"
echo ""
