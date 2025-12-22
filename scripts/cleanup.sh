#!/bin/bash

# Cleanup Script - Remove all Spark Code Interpreter resources

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

REGION="us-east-1"
ENVIRONMENT="${ENVIRONMENT:-dev}"
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}Spark Code Interpreter - Cleanup${NC}"
echo -e "${YELLOW}========================================${NC}"
echo ""
echo -e "${RED}WARNING: This will delete all resources!${NC}"
echo ""
read -p "Are you sure you want to continue? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "Cleanup cancelled"
    exit 0
fi

echo ""

# Get AWS Account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Delete ECS service and cluster
CLUSTER_NAME="${ENVIRONMENT}-spark-cluster"
SERVICE_NAME="${ENVIRONMENT}-spark-backend"

echo -e "${YELLOW}Deleting ECS service: $SERVICE_NAME${NC}"
aws ecs update-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --desired-count 0 --region $REGION 2>/dev/null || echo "Service not found"
aws ecs delete-service --cluster $CLUSTER_NAME --service $SERVICE_NAME --region $REGION 2>/dev/null || echo "Service not found or already deleted"

echo -e "${YELLOW}Deleting ECS cluster: $CLUSTER_NAME${NC}"
aws ecs delete-cluster --cluster $CLUSTER_NAME --region $REGION 2>/dev/null || echo "Cluster not found or already deleted"

# Delete backend Lambda (if it exists from old deployment)
BACKEND_LAMBDA_NAME="${ENVIRONMENT}-spark-backend"
aws lambda delete-function --function-name $BACKEND_LAMBDA_NAME --region $REGION 2>/dev/null || echo "Backend Lambda not found"

# Get S3 bucket name
S3_BUCKET=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`SparkDataBucketName`].OutputValue' \
  --output text 2>/dev/null || echo "")

if [ -n "$S3_BUCKET" ]; then
    echo -e "${YELLOW}Emptying S3 bucket: $S3_BUCKET${NC}"
    aws s3 rm s3://$S3_BUCKET --recursive --region $REGION || true
    echo -e "${GREEN}✅ S3 bucket emptied${NC}"
fi

# Delete Lambda functions explicitly before stack deletion
echo ""
echo -e "${YELLOW}Deleting Lambda functions...${NC}"
LAMBDA_FUNCTIONS=(
    "${ENVIRONMENT}-spark-on-lambda"
    "${ENVIRONMENT}-spark-agent-wrapper"
)

for func in "${LAMBDA_FUNCTIONS[@]}"; do
    echo "Deleting Lambda function: $func"
    aws lambda delete-function --function-name $func --region $REGION 2>/dev/null || echo "Function not found or already deleted"
done
echo -e "${GREEN}✅ Lambda functions deleted${NC}"

# Delete CloudFormation stack
echo -e "${YELLOW}Deleting CloudFormation stack: $STACK_NAME${NC}"
aws cloudformation delete-stack \
  --stack-name $STACK_NAME \
  --region $REGION || true

echo "Waiting for stack deletion..."
aws cloudformation wait stack-delete-complete \
  --stack-name $STACK_NAME \
  --region $REGION 2>/dev/null || true

echo -e "${GREEN}✅ CloudFormation stack deleted${NC}"

# Clean up IAM roles that might not have been deleted by CloudFormation
echo ""
echo -e "${YELLOW}Cleaning up IAM roles...${NC}"
IAM_ROLES=(
    "${ENVIRONMENT}-spark-lambda-role"
    "${ENVIRONMENT}-spark-wrapper-lambda-role"
    "${ENVIRONMENT}-spark-emr-execution-role"
    "${ENVIRONMENT}-spark-gateway-role"
    "AmazonBedrockAgentCoreSDKRuntime-${REGION}-${ENVIRONMENT}"
)

for role in "${IAM_ROLES[@]}"; do
    echo "Checking role: $role"
    
    # List and delete inline policies
    INLINE_POLICIES=$(aws iam list-role-policies --role-name $role --query 'PolicyNames' --output text 2>/dev/null || echo "")
    if [ -n "$INLINE_POLICIES" ]; then
        for policy in $INLINE_POLICIES; do
            echo "  Deleting inline policy: $policy"
            aws iam delete-role-policy --role-name $role --policy-name $policy 2>/dev/null || true
        done
    fi
    
    # List and detach managed policies
    MANAGED_POLICIES=$(aws iam list-attached-role-policies --role-name $role --query 'AttachedPolicies[*].PolicyArn' --output text 2>/dev/null || echo "")
    if [ -n "$MANAGED_POLICIES" ]; then
        for policy_arn in $MANAGED_POLICIES; do
            echo "  Detaching managed policy: $policy_arn"
            aws iam detach-role-policy --role-name $role --policy-arn $policy_arn 2>/dev/null || true
        done
    fi
    
    # Delete the role
    echo "  Deleting role: $role"
    aws iam delete-role --role-name $role 2>/dev/null || echo "  Role not found or already deleted"
done

echo -e "${GREEN}✅ IAM roles cleaned up${NC}"

# Delete ECS task definitions
echo ""
echo -e "${YELLOW}Deregistering ECS task definitions...${NC}"
TASK_FAMILY="${ENVIRONMENT}-spark-backend"
TASK_ARNS=$(aws ecs list-task-definitions --family-prefix $TASK_FAMILY --region $REGION --query 'taskDefinitionArns' --output text 2>/dev/null)
for arn in $TASK_ARNS; do
    aws ecs deregister-task-definition --task-definition $arn --region $REGION 2>/dev/null || echo "Task definition already deregistered"
done

# Delete IAM role
echo -e "${YELLOW}Deleting ECS task role...${NC}"
TASK_ROLE_NAME="${ENVIRONMENT}-spark-backend-task-role"
aws iam detach-role-policy --role-name $TASK_ROLE_NAME --policy-arn arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy --region $REGION 2>/dev/null || echo "Policy not attached"
aws iam delete-role-policy --role-name $TASK_ROLE_NAME --policy-name BackendPermissions --region $REGION 2>/dev/null || echo "Policy not found"
aws iam delete-role --role-name $TASK_ROLE_NAME --region $REGION 2>/dev/null || echo "Role not found"

# Delete CloudWatch log group
echo -e "${YELLOW}Deleting CloudWatch log group...${NC}"
aws logs delete-log-group --log-group-name "/ecs/${ENVIRONMENT}-spark-backend" --region $REGION 2>/dev/null || echo "Log group not found"

# Delete ECR repositories
echo ""
echo -e "${YELLOW}Deleting ECR repositories...${NC}"
for repo in "${ENVIRONMENT}-spark-lambda" "${ENVIRONMENT}-spark-backend"; do
    echo "Deleting ECR repository: $repo"
    aws ecr delete-repository --repository-name $repo --region $REGION --force 2>/dev/null || echo "Repository $repo not found or already deleted"
done
echo -e "${GREEN}✅ ECR repositories deleted${NC}"

# Get Gateway ID before deleting stack
echo ""
echo -e "${YELLOW}Getting Gateway ID from CloudFormation...${NC}"
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text 2>/dev/null || echo "")

# Get Cognito User Pool ID before deleting stack
echo -e "${YELLOW}Getting Cognito User Pool ID from CloudFormation...${NC}"
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text 2>/dev/null || echo "")

# Delete AgentCore Gateway
if [ -n "$GATEWAY_ID" ]; then
    echo ""
    echo -e "${YELLOW}Deleting AgentCore Gateway: $GATEWAY_ID${NC}"
    aws bedrock-agentcore delete-gateway --gateway-id $GATEWAY_ID --region $REGION 2>/dev/null || echo "Gateway not found or already deleted"
    echo -e "${GREEN}✅ AgentCore Gateway deleted${NC}"
fi

# Delete Cognito User Pool (this also deletes the domain and app client)
if [ -n "$USER_POOL_ID" ]; then
    echo ""
    echo -e "${YELLOW}Deleting Cognito User Pool: $USER_POOL_ID${NC}"
    # Delete domain first
    DOMAIN="${ENVIRONMENT}-spark-gateway-${ACCOUNT_ID}"
    aws cognito-idp delete-user-pool-domain --domain $DOMAIN --user-pool-id $USER_POOL_ID --region $REGION 2>/dev/null || echo "Domain not found or already deleted"
    # Delete user pool
    aws cognito-idp delete-user-pool --user-pool-id $USER_POOL_ID --region $REGION 2>/dev/null || echo "User pool not found or already deleted"
    echo -e "${GREEN}✅ Cognito User Pool deleted${NC}"
fi

# Delete AgentCore agents
echo ""
echo -e "${YELLOW}Deleting AgentCore agents...${NC}"
CONFIG_FILE="../config/deployment-config.json"
if [ -f "$CONFIG_FILE" ]; then
    SPARK_SUPERVISOR_ARN=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('spark', {}).get('supervisor_arn', ''))" 2>/dev/null || echo "")
    CODE_GEN_AGENT_ARN=$(cat $CONFIG_FILE | python3 -c "import sys, json; config=json.load(sys.stdin); print(config.get('global', {}).get('code_gen_agent_arn', ''))" 2>/dev/null || echo "")
    
    if [ -n "$SPARK_SUPERVISOR_ARN" ]; then
        AGENT_ID=$(echo $SPARK_SUPERVISOR_ARN | awk -F'/' '{print $NF}')
        echo "Deleting Spark Supervisor Agent: $AGENT_ID"
        aws bedrock-agentcore delete-agent-runtime --agent-id $AGENT_ID --region $REGION 2>/dev/null || echo "Agent not found or already deleted"
    fi
    
    if [ -n "$CODE_GEN_AGENT_ARN" ]; then
        AGENT_ID=$(echo $CODE_GEN_AGENT_ARN | awk -F'/' '{print $NF}')
        echo "Deleting Code Generation Agent: $AGENT_ID"
        aws bedrock-agentcore delete-agent-runtime --agent-id $AGENT_ID --region $REGION 2>/dev/null || echo "Agent not found or already deleted"
    fi
    
    echo -e "${GREEN}✅ AgentCore agents deleted${NC}"
else
    echo -e "${YELLOW}⚠️  Config file not found. Agents may need manual deletion.${NC}"
    echo "List agents: aws bedrock-agentcore list-agent-runtimes --region $REGION"
fi

# Delete S3 bucket
if [ -n "$S3_BUCKET" ]; then
    echo ""
    echo -e "${YELLOW}Deleting S3 bucket: $S3_BUCKET${NC}"
    aws s3 rb s3://$S3_BUCKET --force --region $REGION 2>/dev/null || echo "S3 bucket already deleted"
    echo -e "${GREEN}✅ S3 bucket deleted${NC}"
fi

# Clean up local config files
echo ""
echo -e "${YELLOW}Cleaning up local configuration files...${NC}"
rm -f ../config/deployment-config.json
rm -f ../agent-code/deployment_config_helper.py
rm -f ../agent-code/spark-supervisor-agent/.bedrock_agentcore.yaml.bak
rm -f ../agent-code/code-generation-agent/.bedrock_agentcore.yaml.bak
echo -e "${GREEN}✅ Local config files cleaned${NC}"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Cleanup Complete${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "All resources have been removed:"
echo "  ✅ CloudFormation Stack"
echo "  ✅ S3 Bucket"
echo "  ✅ Lambda Functions (Spark & Wrapper)"
echo "  ✅ AgentCore Gateway"
echo "  ✅ Cognito User Pool"
echo "  ✅ AgentCore Agents"
echo "  ✅ ECS Cluster & Service (if existed)"
echo "  ✅ ECR Repositories"
echo "  ✅ Local config files"
echo ""
echo -e "${GREEN}You can now run ./deploy-all.sh for a fresh deployment!${NC}"
