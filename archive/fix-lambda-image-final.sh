#!/bin/bash

# Fix Lambda image - push single platform image, not manifest list

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
echo -e "${BLUE}Fix Lambda Image - Single Platform${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Navigate to Docker directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT/Docker"

echo -e "${YELLOW}Building single-platform image for linux/amd64...${NC}"
echo ""

# Build with buildx for single platform (no manifest list)
docker buildx build \
  --platform linux/amd64 \
  --build-arg FRAMEWORK="" \
  --build-arg AWS_REGION=$REGION \
  --load \
  -t $IMAGE_NAME:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Build failed${NC}"
    echo ""
    echo "If buildx is not available, trying regular build..."
    docker build \
      --build-arg FRAMEWORK="" \
      --build-arg AWS_REGION=$REGION \
      -t $IMAGE_NAME:latest .
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Regular build also failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Image built${NC}"
echo ""

echo -e "${YELLOW}Tagging for ECR...${NC}"
docker tag $IMAGE_NAME:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest
echo ""

echo -e "${YELLOW}Logging into ECR...${NC}"
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com
echo ""

echo -e "${YELLOW}Pushing single-platform image...${NC}"
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Pushed${NC}"
echo ""

# Get the image digest
echo -e "${YELLOW}Getting image digest...${NC}"
IMAGE_DIGEST=$(aws ecr describe-images \
  --repository-name $IMAGE_NAME \
  --region $REGION \
  --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageDigest' \
  --output text)

echo "Image digest: $IMAGE_DIGEST"
echo ""

echo -e "${YELLOW}Updating Lambda with digest...${NC}"
aws lambda update-function-code \
  --function-name ${ENVIRONMENT}-spark-on-lambda \
  --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME@$IMAGE_DIGEST \
  --region $REGION

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lambda update failed${NC}"
    echo ""
    echo "Trying with :latest tag instead..."
    aws lambda update-function-code \
      --function-name ${ENVIRONMENT}-spark-on-lambda \
      --image-uri $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest \
      --region $REGION
    
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ Still failed${NC}"
        exit 1
    fi
fi

echo -e "${GREEN}✅ Lambda updated${NC}"
echo ""

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Success!${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
