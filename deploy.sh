#!/bin/bash

# Check if required parameters are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <aws-account-id> <aws-region>"
    echo "Example: $0 123456789012 us-east-1"
    exit 1
fi

# Configuration variables
AWS_ACCOUNT_ID=$1
AWS_REGION=$2
#EC2_KEY=$3
ECR_REPOSITORY_NAME="sparkonlambda"
IMAGE_TAG="latest"
# ECR repository URL
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

# Read values from config.json post templated

# Using ["key-name"] syntax for keys with hyphens
DYNAMODB_TABLE=$(jq -r '.DynamodbTable' config.json)
DYNAMODB_TABLE=`echo $DYNAMODB_TABLE | sed "s/{{ACCOUNT_ID}}/${AWS_ACCOUNT_ID}/g"`
USER_ID=$(jq -r '.UserId' config.json)
BUCKET_NAME=$(jq -r '.Bucket_Name' config.json)
BUCKET_NAME=`echo $BUCKET_NAME | sed "s/{{ACCOUNT_ID}}/${AWS_ACCOUNT_ID}/g"`
INPUT_BUCKET=$(jq -r '.input_bucket' config.json)
INPUT_BUCKET=`echo $INPUT_BUCKET | sed "s/{{ACCOUNT_ID}}/${AWS_ACCOUNT_ID}/g"`
INPUT_S3_PATH=$(jq -r '.input_s3_path' config.json)
LAMBDA_FUNCTION=$(jq -r '.["lambda-function"]' config.json)

# Verify if jq successfully extracted the values
if [ -z "$DYNAMODB_TABLE" ] || [ -z "$USER_ID" ] || [ -z "$BUCKET_NAME" ] || [ -z "$INPUT_BUCKET" ] || [ -z "$INPUT_S3_PATH" ] || [ -z "$LAMBDA_FUNCTION" ]; then
    echo "Error: Failed to read one or more values from config.json"
    echo "DynamoDB Table: $DYNAMODB_TABLE"
    echo "User ID: $USER_ID"
    echo "Bucket Name: $BUCKET_NAME"
    echo "Input Bucket: $INPUT_BUCKET"
    echo "Input S3 Path: $INPUT_S3_PATH"
    echo "Lambda Function: $LAMBDA_FUNCTION"
    exit 1
fi

# Authenticate Docker to ECR
echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

# Create ECR repository if it doesn't exist
echo "Creating ECR repository if it doesn't exist..."
aws ecr describe-repositories --repository-names ${ECR_REPOSITORY_NAME} --region ${AWS_REGION} || \
aws ecr create-repository --repository-name ${ECR_REPOSITORY_NAME} --region ${AWS_REGION} --image-tag-mutability MUTABLE --image-scanning-configuration scanOnPush=true

# Build Docker image
echo "Building Docker image..."
cd Docker
docker build -t ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} .

# Tag Docker image
echo "Tagging Docker image..."
docker tag ${ECR_REPOSITORY_NAME}:${IMAGE_TAG} ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Logging in to Amazon ECR..."
aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com


# Push Docker image to ECR
echo "Pushing Docker image to ECR..."
echo "Pushu Docker image ${ECR_REPOSITORY_URI}:${IMAGE_TAG} ..."
docker push ${ECR_REPOSITORY_URI}:${IMAGE_TAG}

echo "Done! SparkonLambda Image has been built and pushed to ECR successfully."

# Add this near the top of your deploy.sh script
MY_IP=$(curl -s https://checkip.amazonaws.com)/32
GIT_BRANCH=`git rev-parse --abbrev-ref HEAD`
echo "Inititaing deployment of the bedrock application"
cd ../CloudFormation/
sam deploy \
    --template-file cloudFormation.yml \
    --region ${AWS_REGION} \
    --stack-name spark-code-interpreter \
    --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
    --resolve-s3 \
    --image-repository ${ECR_REPOSITORY_URI} \
    --parameter-overrides \
        ImageUri=${ECR_REPOSITORY_URI}:${IMAGE_TAG} \
        DynamoDBTable=${DYNAMODB_TABLE} \
        UserId=${USER_ID} \
        BucketName=${BUCKET_NAME} \
        InputBucket=${INPUT_BUCKET} \
        InputS3Path=${INPUT_S3_PATH} \
        LambdaFunction=${LAMBDA_FUNCTION} \
        MyIp=${MY_IP} \
        GitBranch=${GIT_BRANCH}

