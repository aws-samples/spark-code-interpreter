#!/bin/bash

# Fix Lambda image platform issue
# Lambda requires linux/amd64 platform

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

REGION=${AWS_REGION:-us-east-1}
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
ENVIRONMENT=${ENVIRONMENT:-dev}
IMAGE_NAME="${ENVIRONMENT}-spark-lambda"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Fix Lambda Image Platform${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo -e "${YELLOW}Issue: Lambda requires linux/amd64 platform${NC}"
echo -e "${YELLOW}Solution: Rebuild with --platform linux/amd64${NC}"
echo ""

# Navigate to Docker directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT/Docker"

echo -e "${YELLOW}Step 1: Removing old image...${NC}"
docker rmi $IMAGE_NAME:latest 2>/dev/null || true
docker rmi $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest 2>/dev/null || true
echo -e "${GREEN}✅ Old images removed${NC}"
echo ""

echo -e "${YELLOW}Step 2: Building for linux/amd64 platform...${NC}"
docker build \
  --platform linux/amd64 \
  --build-arg FRAMEWORK="" \
  --build-arg AWS_REGION=$REGION \
  -t $IMAGE_NAME:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image built for linux/amd64${NC}"
echo ""

echo -e "${YELLOW}Step 3: Verifying platform...${NC}"
PLATFORM=$(docker inspect $IMAGE_NAME:latest --format='{{.Os}}/{{.Architecture}}')
echo "Platform: $PLATFORM"

if [ "$PLATFORM" != "linux/amd64" ]; then
    echo -e "${RED}❌ Platform is still $PLATFORM${NC}"
    echo "Your Docker may not support multi-platform builds."
    echo "Try: docker buildx create --use"
    exit 1
fi

echo -e "${GREEN}✅ Platform verified: $PLATFORM${NC}"
echo ""

echo -e "${YELLOW}Step 4: Tagging for ECR...${NC}"
docker tag $IMAGE_NAME:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest
echo -e "${GREEN}✅ Tagged${NC}"
echo ""

echo -e "${YELLOW}Step 5: Logging into ECR...${NC}"
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECR login failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Logged in${NC}"
echo ""

echo -e "${YELLOW}Step 6: Pushing to ECR...${NC}"
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pushed to ECR${NC}"
echo ""

echo -e "${YELLOW}Step 7: Updating Lambda function...${NC}"
aws lambda update-function-code \
  --function-name ${ENVIRONMENT}-spark-on-lambda \
  --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest \
  --region $REGION

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lambda update failed${NC}"
    echo ""
    echo "Possible issues:"
    echo "1. Image manifest still incompatible (check platform)"
    echo "2. Lambda function doesn't exist"
    echo "3. Permissions issue"
    exit 1
fi

echo -e "${GREEN}✅ Lambda updated${NC}"
echo ""

echo -e "${YELLOW}Waiting for Lambda to be ready...${NC}"
sleep 10

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Success!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Image: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest"
echo "Platform: linux/amd64"
echo "Function: ${ENVIRONMENT}-spark-on-lambda"
echo ""
echo "The Lambda function now uses the correct platform image."
echo ""
