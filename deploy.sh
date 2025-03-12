#!/bin/bash

# Check if required parameters are provided
if [ $# -ne 3 ]; then
    echo "Usage: $0 <aws-account-id> <aws-region> <ec2-key-pair>"
    echo "Example: $0 123456789012 us-east-1 myec2key"
    exit 1
fi

# Configuration variables
AWS_ACCOUNT_ID=$1
AWS_REGION=$2
EC2_KEY=$3
ECR_REPOSITORY_NAME="sparkonlambda"
IMAGE_TAG="latest"

# ECR repository URL
ECR_REPOSITORY_URI="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY_NAME}"

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

echo "Inititaing deployment of the bedrock application"
cd /home/ec2-user/environment/spark-code-interpreter/CloudFormation/
sam deploy --template-file cloudFormation.yml --region ${AWS_REGION} --stack-name spark-code-interpreter --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM --resolve-s3 --image-repository ${ECR_REPOSITORY_URI} --parameter-overrides  "ParameterKey=ImageUri,ParameterValue=${ECR_REPOSITORY_URI}:${IMAGE_TAG} ParameterKey=KeyPair,ParameterValue=${EC2_KEY}"
