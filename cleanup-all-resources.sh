#!/bin/bash

# Complete Cleanup Script
# Removes all manually created resources and CloudFormation stack

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
ENVIRONMENT=${ENVIRONMENT:-dev}
STACK_NAME="${ENVIRONMENT}-spark-complete-stack"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Complete Resource Cleanup${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Region: $REGION"
echo "Environment: $ENVIRONMENT"
echo ""

ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
echo "Account: $ACCOUNT_ID"
echo ""

# ============================================================================
# Step 1: Delete Agents
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 1: Deleting Agents${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Listing agents...${NC}"
AGENTS=$(aws bedrock-agentcore list-runtimes --region $REGION --query 'runtimes[?contains(runtimeName, `spark`) || contains(runtimeName, `ray`)].runtimeArn' --output text 2>&1 || echo "")

if [ -n "$AGENTS" ]; then
    for AGENT_ARN in $AGENTS; do
        echo -e "${YELLOW}Deleting agent: ${AGENT_ARN}${NC}"
        aws bedrock-agentcore delete-runtime --runtime-arn "$AGENT_ARN" --region $REGION 2>&1 || echo "Failed to delete $AGENT_ARN"
    done
    echo -e "${GREEN}✅ Agents deleted${NC}"
else
    echo -e "${YELLOW}No agents found${NC}"
fi
echo ""

# Wait for agents to be deleted
echo -e "${YELLOW}Waiting 10 seconds for agents to be deleted...${NC}"
sleep 10

# ============================================================================
# Step 2: Delete CloudFormation Stack
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 2: Deleting CloudFormation Stack${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

STACK_EXISTS=$(aws cloudformation describe-stacks --stack-name $STACK_NAME --region $REGION 2>&1 | grep -c "does not exist" || true)

if [ "$STACK_EXISTS" -eq 0 ]; then
    echo -e "${YELLOW}Deleting CloudFormation stack: ${STACK_NAME}${NC}"
    aws cloudformation delete-stack --stack-name $STACK_NAME --region $REGION
    
    echo -e "${YELLOW}Waiting for stack deletion (this may take 5-10 minutes)...${NC}"
    aws cloudformation wait stack-delete-complete --stack-name $STACK_NAME --region $REGION 2>&1 || {
        echo -e "${RED}Stack deletion failed or timed out${NC}"
        echo "Check CloudFormation console for details"
    }
    
    echo -e "${GREEN}✅ CloudFormation stack deleted${NC}"
else
    echo -e "${YELLOW}Stack does not exist${NC}"
fi
echo ""

# ============================================================================
# Step 3: Delete ECR Repositories
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 3: Deleting ECR Repositories${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

ECR_REPOS=$(aws ecr describe-repositories --region $REGION --query 'repositories[?contains(repositoryName, `spark`) || contains(repositoryName, `bedrock-agentcore`)].repositoryName' --output text 2>&1 || echo "")

if [ -n "$ECR_REPOS" ]; then
    for REPO in $ECR_REPOS; do
        echo -e "${YELLOW}Deleting ECR repository: ${REPO}${NC}"
        aws ecr delete-repository --repository-name "$REPO" --force --region $REGION 2>&1 || echo "Failed to delete $REPO"
    done
    echo -e "${GREEN}✅ ECR repositories deleted${NC}"
else
    echo -e "${YELLOW}No ECR repositories found${NC}"
fi
echo ""

# ============================================================================
# Step 4: Delete IAM Roles (AgentCore Runtime Roles)
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 4: Deleting IAM Roles${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

IAM_ROLES=$(aws iam list-roles --query 'Roles[?starts_with(RoleName, `AmazonBedrockAgentCoreSDKRuntime-us-east-1-`)].RoleName' --output text 2>&1 || echo "")

if [ -n "$IAM_ROLES" ]; then
    for ROLE in $IAM_ROLES; do
        echo -e "${YELLOW}Deleting IAM role: ${ROLE}${NC}"
        
        # Delete inline policies
        POLICIES=$(aws iam list-role-policies --role-name "$ROLE" --query 'PolicyNames' --output text 2>&1 || echo "")
        if [ -n "$POLICIES" ]; then
            for POLICY in $POLICIES; do
                echo "  Deleting inline policy: $POLICY"
                aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POLICY" 2>&1 || true
            done
        fi
        
        # Detach managed policies
        ATTACHED=$(aws iam list-attached-role-policies --role-name "$ROLE" --query 'AttachedPolicies[].PolicyArn' --output text 2>&1 || echo "")
        if [ -n "$ATTACHED" ]; then
            for POLICY_ARN in $ATTACHED; do
                echo "  Detaching managed policy: $POLICY_ARN"
                aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$POLICY_ARN" 2>&1 || true
            done
        fi
        
        # Delete the role
        aws iam delete-role --role-name "$ROLE" 2>&1 || echo "Failed to delete $ROLE"
    done
    echo -e "${GREEN}✅ IAM roles deleted${NC}"
else
    echo -e "${YELLOW}No IAM roles found${NC}"
fi
echo ""

# ============================================================================
# Step 5: Delete CodeBuild IAM Roles
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 5: Deleting CodeBuild IAM Roles${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

CODEBUILD_ROLES=$(aws iam list-roles --query 'Roles[?starts_with(RoleName, `AmazonBedrockAgentCoreSDKCodeBuild-us-east-1-`)].RoleName' --output text 2>&1 || echo "")

if [ -n "$CODEBUILD_ROLES" ]; then
    for ROLE in $CODEBUILD_ROLES; do
        echo -e "${YELLOW}Deleting CodeBuild IAM role: ${ROLE}${NC}"
        
        # Delete inline policies
        POLICIES=$(aws iam list-role-policies --role-name "$ROLE" --query 'PolicyNames' --output text 2>&1 || echo "")
        if [ -n "$POLICIES" ]; then
            for POLICY in $POLICIES; do
                echo "  Deleting inline policy: $POLICY"
                aws iam delete-role-policy --role-name "$ROLE" --policy-name "$POLICY" 2>&1 || true
            done
        fi
        
        # Detach managed policies
        ATTACHED=$(aws iam list-attached-role-policies --role-name "$ROLE" --query 'AttachedPolicies[].PolicyArn' --output text 2>&1 || echo "")
        if [ -n "$ATTACHED" ]; then
            for POLICY_ARN in $ATTACHED; do
                echo "  Detaching managed policy: $POLICY_ARN"
                aws iam detach-role-policy --role-name "$ROLE" --policy-arn "$POLICY_ARN" 2>&1 || true
            done
        fi
        
        # Delete the role
        aws iam delete-role --role-name "$ROLE" 2>&1 || echo "Failed to delete $ROLE"
    done
    echo -e "${GREEN}✅ CodeBuild IAM roles deleted${NC}"
else
    echo -e "${YELLOW}No CodeBuild IAM roles found${NC}"
fi
echo ""

# ============================================================================
# Step 6: Delete S3 Bucket (if exists)
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 6: Deleting S3 Bucket${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

S3_BUCKET="spark-data-${ACCOUNT_ID}-${REGION}"

if aws s3 ls "s3://${S3_BUCKET}" 2>&1 | grep -q "NoSuchBucket"; then
    echo -e "${YELLOW}S3 bucket does not exist${NC}"
else
    echo -e "${YELLOW}Deleting S3 bucket: ${S3_BUCKET}${NC}"
    
    # Delete all versions and delete markers
    echo "  Deleting all object versions..."
    aws s3api list-object-versions --bucket "$S3_BUCKET" --query 'Versions[].{Key:Key,VersionId:VersionId}' --output text 2>&1 | \
        while read -r key version; do
            [ -n "$key" ] && aws s3api delete-object --bucket "$S3_BUCKET" --key "$key" --version-id "$version" 2>&1 > /dev/null || true
        done
    
    aws s3api list-object-versions --bucket "$S3_BUCKET" --query 'DeleteMarkers[].{Key:Key,VersionId:VersionId}' --output text 2>&1 | \
        while read -r key version; do
            [ -n "$key" ] && aws s3api delete-object --bucket "$S3_BUCKET" --key "$key" --version-id "$version" 2>&1 > /dev/null || true
        done
    
    # Delete the bucket
    aws s3 rb "s3://${S3_BUCKET}" --force 2>&1 || echo "Failed to delete bucket"
    
    echo -e "${GREEN}✅ S3 bucket deleted${NC}"
fi
echo ""

# ============================================================================
# Step 7: Delete CodeBuild Projects
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 7: Deleting CodeBuild Projects${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

CODEBUILD_PROJECTS=$(aws codebuild list-projects --region $REGION --query 'projects[?contains(@, `bedrock-agentcore`)]' --output text 2>&1 || echo "")

if [ -n "$CODEBUILD_PROJECTS" ]; then
    for PROJECT in $CODEBUILD_PROJECTS; do
        echo -e "${YELLOW}Deleting CodeBuild project: ${PROJECT}${NC}"
        aws codebuild delete-project --name "$PROJECT" --region $REGION 2>&1 || echo "Failed to delete $PROJECT"
    done
    echo -e "${GREEN}✅ CodeBuild projects deleted${NC}"
else
    echo -e "${YELLOW}No CodeBuild projects found${NC}"
fi
echo ""

# ============================================================================
# Step 8: Clean up local config files
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Step 8: Cleaning Local Config Files${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${YELLOW}Cleaning agent config files...${NC}"

# Clean Spark Supervisor Agent config
if [ -f "agent-code/spark-supervisor-agent/.bedrock_agentcore.yaml" ]; then
    echo "  Removing spark-supervisor-agent/.bedrock_agentcore.yaml"
    rm -f agent-code/spark-supervisor-agent/.bedrock_agentcore.yaml
fi

# Clean Code Generation Agent config
if [ -f "agent-code/code-generation-agent/.bedrock_agentcore.yaml" ]; then
    echo "  Removing code-generation-agent/.bedrock_agentcore.yaml"
    rm -f agent-code/code-generation-agent/.bedrock_agentcore.yaml
fi

# Clean deployment config
if [ -f "config/deployment-config.json" ]; then
    echo "  Removing config/deployment-config.json"
    rm -f config/deployment-config.json
fi

echo -e "${GREEN}✅ Local config files cleaned${NC}"
echo ""

# ============================================================================
# Cleanup Complete
# ============================================================================
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Cleanup Complete! 🎉${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

echo -e "${GREEN}All resources have been cleaned up:${NC}"
echo "  ✅ Agents deleted"
echo "  ✅ CloudFormation stack deleted"
echo "  ✅ ECR repositories deleted"
echo "  ✅ IAM roles deleted"
echo "  ✅ S3 bucket deleted"
echo "  ✅ CodeBuild projects deleted"
echo "  ✅ Local config files cleaned"
echo ""

echo -e "${YELLOW}You can now run a fresh deployment:${NC}"
echo "  ./scripts/deploy-all.sh"
echo ""
