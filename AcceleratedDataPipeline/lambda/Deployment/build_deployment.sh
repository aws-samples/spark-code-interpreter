#!/bin/bash

# Create deployment package for AgenticCoreDeployment Lambda
echo "Creating Lambda deployment package..."

# Remove existing package and zip
rm -rf package AgenticCoreDeployment.zip

# Create package directory
mkdir -p package

# Install dependencies to package directory
echo "Installing dependencies..."
pip install \
--platform manylinux2014_x86_64 \
--target=package \
--implementation cp \
--python-version 3.12 \
--only-binary=:all: --upgrade \
-r requirements_simple.txt



# Create ZIP package
echo "Creating ZIP package..."
cd package
zip -r ../AgenticCoreDeployment.zip . 
cd ..
# Copy Lambda function to package root
echo "Copying Lambda function..."
zip AgenticCoreDeployment.zip lambda_function.py 
# Clean up
rm -rf package

echo "Deployment package created: AgenticCoreDeployment.zip"
echo "Lambda handler should be set to: lambda_function.lambda_handler"