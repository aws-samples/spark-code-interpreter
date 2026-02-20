#!/bin/bash

echo "Creating Lambda deployment package with Docker..."

# Remove existing package and zip
rm -rf package AgenticCoreDeployment.zip

# Create package directory
mkdir -p package

# Use Docker to install dependencies for Linux
echo "Installing dependencies with Docker..."
docker run --rm -v "$PWD":/var/task -w /var/task public.ecr.aws/lambda/python:3.11 \
    pip install -r requirements.txt -t package/

# Copy Lambda function to package root
echo "Copying Lambda function..."
cp AgenticCoreDeployment.py package/lambda_function.py

# Create ZIP package
echo "Creating ZIP package..."
cd package
zip -r ../AgenticCoreDeployment.zip . -x "*.pyc" "*__pycache__*"
cd ..

# Clean up
rm -rf package

echo "Deployment package created: AgenticCoreDeployment.zip"
echo "Lambda handler should be set to: lambda_function.lambda_handler"