#!/bin/bash

# Backend API Deployment Script (ECS Fargate)
# Deploys the FastAPI backend as an ECS Fargate service behind the ALB

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

REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backend API Deployment (ECS Fargate)${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "AWS Account: $ACCOUNT_ID"
echo ""

# Load deployment config to get agent ARNs
CONFIG_FILE="config/deployment-config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${RED}❌ Deployment config not found: $CONFIG_FILE${NC}"
    echo "Please run deploy-agents.sh first to deploy agents"
    exit 1
fi

echo -e "${YELLOW}Loading configuration...${NC}"
SPARK_SUPERVISOR_ARN=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('spark', {}).get('supervisor_arn', ''))" 2>/dev/null || echo "")
CODE_GEN_AGENT_ARN=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('global', {}).get('code_gen_agent_arn', ''))" 2>/dev/null || echo "")
S3_BUCKET=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('s3_bucket', ''))" 2>/dev/null || echo "")
LAMBDA_FUNCTION=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('lambda_function', ''))" 2>/dev/null || echo "")
EMR_APP_ID=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('emr_application_id', ''))" 2>/dev/null || echo "")

if [ -z "$SPARK_SUPERVISOR_ARN" ] || [ -z "$CODE_GEN_AGENT_ARN" ]; then
    echo -e "${RED}❌ Agent ARNs not found in config${NC}"
    echo "Please run deploy-agents.sh first"
    exit 1
fi

echo "✅ Spark Supervisor ARN: $SPARK_SUPERVISOR_ARN"
echo "✅ Code Gen Agent ARN: $CODE_GEN_AGENT_ARN"
echo "✅ S3 Bucket: $S3_BUCKET"
echo "✅ Lambda Function: $LAMBDA_FUNCTION"
echo "✅ EMR Application: $EMR_APP_ID"
echo ""

# Build and push backend Docker image
echo -e "${YELLOW}Building backend Docker image...${NC}"
BACKEND_DIR="backend/backend"
ECR_REPO_NAME="${ENVIRONMENT}-spark-backend"

if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}❌ Backend directory not found: $BACKEND_DIR${NC}"
    exit 1
fi

# Create ECR repository if it doesn't exist
aws ecr describe-repositories --repository-names $ECR_REPO_NAME --region $REGION 2>/dev/null || \
    aws ecr create-repository --repository-name $ECR_REPO_NAME --region $REGION

echo "✅ ECR repository ready: $ECR_REPO_NAME"

# Get ECR login
echo "Logging into ECR..."
aws ecr get-login-password --region $REGION | docker login --username AWS --password-stdin $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

# Build Docker image
echo "Building Docker image (this may take a few minutes)..."
cd $BACKEND_DIR

IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$ECR_REPO_NAME:latest"

# Use docker buildx for proper cross-platform build
docker buildx create --use --name backend-builder 2>/dev/null || docker buildx use backend-builder

docker buildx build \
    --platform linux/amd64 \
    --build-arg AWS_REGION=$REGION \
    -t $IMAGE_URI \
    --push \
    --provenance=false \
    --sbom=false \
    -f Dockerfile \
    . 2>&1 | tail -n 30

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built and pushed to ECR${NC}"
cd - > /dev/null

# Get VPC and subnet information from CloudFormation
echo -e "${YELLOW}Getting VPC and subnet information...${NC}"
VPC_ID=$(aws ec2 describe-vpcs --region $REGION --filters "Name=is-default,Values=true" --query 'Vpcs[0].VpcId' --output text)
SUBNETS=$(aws ec2 describe-subnets --region $REGION --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0:2].SubnetId' --output text | tr '\t' ',')

echo "VPC ID: $VPC_ID"
echo "Subnets: $SUBNETS"
echo ""

# Create ECS cluster if it doesn't exist
CLUSTER_NAME="${ENVIRONMENT}-spark-cluster"
echo -e "${YELLOW}Creating ECS cluster...${NC}"
aws ecs create-cluster --cluster-name $CLUSTER_NAME --region $REGION 2>/dev/null || echo "Cluster already exists"

# Create CloudWatch log group
LOG_GROUP="/ecs/${ENVIRONMENT}-spark-backend"
aws logs create-log-group --log-group-name $LOG_GROUP --region $REGION 2>/dev/null || echo "Log group already exists"

# Create ECS task execution role if it doesn't exist
TASK_ROLE_NAME="${ENVIRONMENT}-spark-backend-task-role"
TASK_ROLE_ARN=$(aws iam get-role --role-name $TASK_ROLE_NAME --query 'Role.Arn' --output text 2>/dev/null || echo "")

if [ -z "$TASK_ROLE_ARN" ]; then
    echo "Creating ECS task execution role..."
    aws iam create-role \
        --role-name $TASK_ROLE_NAME \
        --assume-role-policy-document '{
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "ecs-tasks.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }]
        }' --region $REGION
    
    aws iam attach-role-policy \
        --role-name $TASK_ROLE_NAME \
        --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy
    
    # Add permissions for Bedrock, Lambda, S3, EMR
    aws iam put-role-policy \
        --role-name $TASK_ROLE_NAME \
        --policy-name BackendPermissions \
        --policy-document "{
            \"Version\": \"2012-10-17\",
            \"Statement\": [
                {
                    \"Effect\": \"Allow\",
                    \"Action\": [
                        \"bedrock:*\",
                        \"bedrock-agentcore:*\",
                        \"lambda:InvokeFunction\",
                        \"s3:*\",
                        \"emr-serverless:*\",
                        \"glue:*\"
                    ],
                    \"Resource\": \"*\"
                }
            ]
        }"
    
    sleep 10  # Wait for role to propagate
    TASK_ROLE_ARN=$(aws iam get-role --role-name $TASK_ROLE_NAME --query 'Role.Arn' --output text)
fi

echo "✅ Task role: $TASK_ROLE_ARN"
echo ""

# Register ECS task definition
echo -e "${YELLOW}Registering ECS task definition...${NC}"
TASK_DEF_FILE="/tmp/task-definition.json"

cat > $TASK_DEF_FILE <<EOF
{
  "family": "${ENVIRONMENT}-spark-backend",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "executionRoleArn": "$TASK_ROLE_ARN",
  "taskRoleArn": "$TASK_ROLE_ARN",
  "containerDefinitions": [
    {
      "name": "backend",
      "image": "$IMAGE_URI",
      "essential": true,
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "SPARK_SUPERVISOR_ARN", "value": "$SPARK_SUPERVISOR_ARN"},
        {"name": "RAY_CODE_GEN_AGENT_ARN", "value": "$CODE_GEN_AGENT_ARN"},
        {"name": "S3_BUCKET", "value": "$S3_BUCKET"},
        {"name": "DATA_BUCKET", "value": "$S3_BUCKET"},
        {"name": "SPARK_LAMBDA_FUNCTION", "value": "$LAMBDA_FUNCTION"},
        {"name": "EMR_APPLICATION_ID", "value": "$EMR_APP_ID"},
        {"name": "AWS_DEFAULT_REGION", "value": "$REGION"},
        {"name": "BEDROCK_MODEL", "value": "us.anthropic.claude-haiku-4-5-20251001-v1:0"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "$LOG_GROUP",
          "awslogs-region": "$REGION",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
EOF

aws ecs register-task-definition \
    --cli-input-json file://$TASK_DEF_FILE \
    --region $REGION > /dev/null

echo -e "${GREEN}✅ Task definition registered${NC}"
echo ""

# Get target group ARN
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
    --names ${ENVIRONMENT}-spark-backend-tg \
    --region $REGION \
    --query 'TargetGroups[0].TargetGroupArn' \
    --output text)

# Create security group for ECS tasks
SG_NAME="${ENVIRONMENT}-spark-backend-sg"
SG_ID=$(aws ec2 describe-security-groups \
    --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" \
    --region $REGION \
    --query 'SecurityGroups[0].GroupId' \
    --output text 2>/dev/null)

if [ -z "$SG_ID" ] || [ "$SG_ID" == "None" ]; then
    echo "Creating security group for ECS tasks..."
    SG_ID=$(aws ec2 create-security-group \
        --group-name $SG_NAME \
        --description "Security group for Spark backend ECS tasks" \
        --vpc-id $VPC_ID \
        --region $REGION \
        --query 'GroupId' \
        --output text)
    
    # Allow inbound from ALB
    ALB_SG_ID=$(aws ec2 describe-security-groups \
        --filters "Name=group-name,Values=${ENVIRONMENT}-spark-alb-sg" \
        --region $REGION \
        --query 'SecurityGroups[0].GroupId' \
        --output text)
    
    aws ec2 authorize-security-group-ingress \
        --group-id $SG_ID \
        --protocol tcp \
        --port 8000 \
        --source-group $ALB_SG_ID \
        --region $REGION
    
    # Allow outbound to anywhere
    aws ec2 authorize-security-group-egress \
        --group-id $SG_ID \
        --protocol -1 \
        --cidr 0.0.0.0/0 \
        --region $REGION 2>/dev/null || echo "Egress rule already exists"
fi

echo "✅ Security group: $SG_ID"
echo ""

# Create or update ECS service
SERVICE_NAME="${ENVIRONMENT}-spark-backend"
echo -e "${YELLOW}Creating/updating ECS service...${NC}"

# Check if service exists
SERVICE_EXISTS=$(aws ecs describe-services \
    --cluster $CLUSTER_NAME \
    --services $SERVICE_NAME \
    --region $REGION \
    --query 'services[0].serviceName' \
    --output text 2>/dev/null)

if [ "$SERVICE_EXISTS" == "$SERVICE_NAME" ]; then
    echo "Updating existing service..."
    aws ecs update-service \
        --cluster $CLUSTER_NAME \
        --service $SERVICE_NAME \
        --task-definition ${ENVIRONMENT}-spark-backend \
        --force-new-deployment \
        --region $REGION > /dev/null
else
    echo "Creating new service..."
    aws ecs create-service \
        --cluster $CLUSTER_NAME \
        --service-name $SERVICE_NAME \
        --task-definition ${ENVIRONMENT}-spark-backend \
        --desired-count 1 \
        --launch-type FARGATE \
        --network-configuration "awsvpcConfiguration={subnets=[$SUBNETS],securityGroups=[$SG_ID],assignPublicIp=ENABLED}" \
        --load-balancers "targetGroupArn=$TARGET_GROUP_ARN,containerName=backend,containerPort=8000" \
        --region $REGION > /dev/null
fi

echo -e "${GREEN}✅ ECS service deployed${NC}"
echo ""

# Update ALB listener to forward to target group
echo -e "${YELLOW}Updating ALB listener...${NC}"
LISTENER_ARN=$(aws elbv2 describe-listeners \
    --load-balancer-arn $(aws elbv2 describe-load-balancers \
        --names ${ENVIRONMENT}-spark-alb \
        --region $REGION \
        --query 'LoadBalancers[0].LoadBalancerArn' \
        --output text) \
    --region $REGION \
    --query 'Listeners[0].ListenerArn' \
    --output text)

aws elbv2 modify-listener \
    --listener-arn $LISTENER_ARN \
    --default-actions Type=forward,TargetGroupArn=$TARGET_GROUP_ARN \
    --region $REGION > /dev/null

echo -e "${GREEN}✅ ALB listener updated${NC}"
echo ""

# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
    --stack-name $STACK_NAME \
    --region $REGION \
    --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
    --output text)

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Backend Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "ECS Cluster: $CLUSTER_NAME"
echo "ECS Service: $SERVICE_NAME"
echo "ALB URL: $ALB_URL"
echo ""
echo -e "${YELLOW}Waiting for service to become healthy (this may take 2-3 minutes)...${NC}"
echo "You can check status with:"
echo "  aws ecs describe-services --cluster $CLUSTER_NAME --services $SERVICE_NAME --region $REGION"
echo ""
echo -e "${GREEN}Backend is deploying! 🚀${NC}"
echo ""
