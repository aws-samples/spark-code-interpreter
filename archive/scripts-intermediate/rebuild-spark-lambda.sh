#!/bin/bash

# Rebuild and redeploy Spark Lambda with S3 configuration fix
# This script rebuilds the Docker image with:
# - S3 write configuration (automatic S3A filesystem setup)
# - JAR classpath fix (hadoop-aws and aws-sdk-bundle JARs)
# - Correct platform (linux/amd64 for Lambda)

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
echo -e "${BLUE}Rebuild Spark Lambda${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Includes:"
echo "  ✓ S3 write configuration"
echo "  ✓ JAR classpath fix"
echo "  ✓ Platform: linux/amd64"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running${NC}"
    exit 1
fi

# Navigate to Docker directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT/Docker"

echo -e "${YELLOW}Step 1: Building Docker image for linux/amd64...${NC}"
echo "Note: Lambda requires linux/amd64 platform"
echo "Using docker buildx for single-platform image"
echo ""

docker buildx build \
  --platform linux/amd64 \
  --load \
  --build-arg FRAMEWORK="" \
  --build-arg AWS_REGION=$REGION \
  -t $IMAGE_NAME:latest .

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Docker image built successfully${NC}"
echo ""
echo ""

echo -e "${YELLOW}Step 2: Tagging image for ECR...${NC}"
docker tag $IMAGE_NAME:latest \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest

echo -e "${GREEN}✅ Image tagged${NC}"
echo ""

echo -e "${YELLOW}Step 3: Logging into ECR...${NC}"
aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ ECR login failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Logged into ECR${NC}"
echo ""

echo -e "${YELLOW}Step 4: Pushing image to ECR...${NC}"
docker push $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Docker push failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Image pushed to ECR${NC}"
echo ""

echo -e "${YELLOW}Step 5: Updating Lambda function...${NC}"

# Get image digest for reliable deployment
IMAGE_DIGEST=$(aws ecr describe-images \
  --repository-name $IMAGE_NAME \
  --region $REGION \
  --query 'sort_by(imageDetails,& imagePushedAt)[-1].imageDigest' \
  --output text 2>/dev/null)

if [ ! -z "$IMAGE_DIGEST" ] && [ "$IMAGE_DIGEST" != "None" ]; then
    echo "Using image digest: $IMAGE_DIGEST"
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME@$IMAGE_DIGEST"
else
    echo "Using latest tag"
    IMAGE_URI="$ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest"
fi

aws lambda update-function-code \
  --function-name ${ENVIRONMENT}-spark-on-lambda \
  --image-uri $IMAGE_URI \
  --region $REGION \
  --query 'FunctionArn' \
  --output text

if [ $? -ne 0 ]; then
    echo -e "${RED}❌ Lambda update failed${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Lambda function updated${NC}"
echo ""

echo -e "${YELLOW}Waiting for Lambda to be ready...${NC}"
sleep 10

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Testing Lambda${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Create test payload with Spark config
TEST_PAYLOAD=$(cat <<EOF
{
  "code": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.appName('Test').getOrCreate()\ndf = spark.range(1, 11)\nresult = df.selectExpr('sum(id) as total').collect()[0]['total']\nprint(f'Result: {result}')\nspark.stop()\nimport json\nwith open('/tmp/output.json', 'w') as f: json.dump({'result': result}, f)",
  "config": {
    "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    "spark.hadoop.fs.s3.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
    "spark.hadoop.fs.s3a.aws.credentials.provider": "com.amazonaws.auth.DefaultAWSCredentialsProviderChain"
  }
}
EOF
)

echo "Test payload:"
echo "$TEST_PAYLOAD" | jq '.'
echo ""

aws lambda invoke \
  --function-name ${ENVIRONMENT}-spark-on-lambda \
  --payload "$TEST_PAYLOAD" \
  --region $REGION \
  /tmp/spark_test_response.json > /dev/null 2>&1

echo -e "${YELLOW}Waiting for execution...${NC}"
sleep 5

if [ -f /tmp/spark_test_response.json ]; then
    echo "Response:"
    cat /tmp/spark_test_response.json | jq '.'
    
    # Check if successful
    if cat /tmp/spark_test_response.json | jq -e '.statusCode == 200' > /dev/null 2>&1; then
        echo ""
        echo -e "${GREEN}✅ Test successful!${NC}"
    else
        echo ""
        echo -e "${YELLOW}⚠️  Test completed with errors (check response above)${NC}"
    fi
    
    rm /tmp/spark_test_response.json
else
    echo -e "${RED}❌ No response file${NC}"
fi

echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Deployment Complete${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""
echo "Image: $ACCOUNT_ID.dkr.ecr.$REGION.amazonaws.com/$IMAGE_NAME:latest"
echo "Function: ${ENVIRONMENT}-spark-on-lambda"
echo ""
echo "The Spark Lambda now includes default S3 configuration."
echo "It will automatically use S3A filesystem for S3 writes."
echo ""
