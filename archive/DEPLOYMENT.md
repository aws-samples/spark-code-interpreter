# Deployment Guide - Spark Code Interpreter

Complete step-by-step deployment guide for the Spark Code Interpreter system.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Steps](#deployment-steps)
4. [Post-Deployment Configuration](#post-deployment-configuration)
5. [Verification](#verification)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Tools

Install these tools before starting:

```bash
# AWS CLI v2
curl "https://awscli.amazonaws.com/AWSCLIV2.pkg" -o "AWSCLIV2.pkg"
sudo installer -pkg AWSCLIV2.pkg -target /

# jq (JSON processor)
brew install jq  # macOS
# or
sudo apt-get install jq  # Linux

# Docker
# Download from https://www.docker.com/products/docker-desktop

# Python 3.11+
brew install python@3.11  # macOS
# or
sudo apt-get install python3.11  # Linux

# Bedrock AgentCore CLI
pip install bedrock-agentcore-starter-toolkit
```

### AWS Account Setup

1. **Create IAM User** (if not using existing):
```bash
aws iam create-user --user-name spark-deployer
```

2. **Attach Required Policies**:
```bash
aws iam attach-user-policy \
  --user-name spark-deployer \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess

aws iam attach-user-policy \
  --user-name spark-deployer \
  --policy-arn arn:aws:iam::aws:policy/IAMFullAccess
```

3. **Create Access Keys**:
```bash
aws iam create-access-key --user-name spark-deployer
```

4. **Configure AWS CLI**:
```bash
aws configure
# Enter Access Key ID
# Enter Secret Access Key
# Default region: us-east-1
# Default output format: json
```

### Service Quotas

Check and request increases if needed:

```bash
# Check Bedrock quotas
aws service-quotas get-service-quota \
  --service-code bedrock \
  --quota-code L-CCA5DF70 \
  --region us-east-1

# Check Lambda quotas
aws service-quotas get-service-quota \
  --service-code lambda \
  --quota-code L-B99A9384 \
  --region us-east-1

# Check EMR Serverless quotas
aws service-quotas list-service-quotas \
  --service-code emr-serverless \
  --region us-east-1
```

## Pre-Deployment Checklist

- [ ] AWS CLI installed and configured
- [ ] Docker installed and running
- [ ] Python 3.11+ installed
- [ ] jq installed
- [ ] bedrock-agentcore CLI installed
- [ ] AWS account has required permissions
- [ ] Service quotas checked
- [ ] VPC with public and private subnets exists
- [ ] Internet Gateway attached to VPC
- [ ] NAT Gateway configured for private subnets

## Deployment Steps

### Step 1: Prepare Environment

```bash
# Clone or navigate to deployment directory
cd us-east-1-stable

# Set environment variables
export AWS_REGION=us-east-1
export ENVIRONMENT=dev
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

echo "Deploying to account: $AWS_ACCOUNT_ID"
echo "Region: $AWS_REGION"
echo "Environment: $ENVIRONMENT"
```

### Step 2: Deploy Infrastructure

```bash
cd scripts
chmod +x *.sh

# Deploy CloudFormation stack
./deploy-complete-stack.sh
```

**What this does:**
- Creates S3 bucket: `spark-data-{ACCOUNT_ID}-us-east-1`
- Deploys Lambda function: `dev-spark-on-lambda`
- Creates EMR Serverless application: `dev-spark-emr`
- Sets up IAM roles with correct permissions
- Deploys Application Load Balancer
- Generates `config/deployment-config.json`

**Expected output:**
```
✅ CloudFormation stack deployed successfully
S3 Bucket: spark-data-025523569182-us-east-1
Lambda Function: dev-spark-on-lambda
EMR Application ID: 00g1k848jaqqjf09
EMR Role ARN: arn:aws:iam::025523569182:role/dev-spark-emr-execution-role
ALB URL: http://dev-spark-alb-123456789.us-east-1.elb.amazonaws.com
```

### Step 3: Deploy Code Generation Agent

```bash
cd ../agent-code/code-generation-agent

# Review configuration
cat .bedrock_agentcore.yaml

# Deploy agent
bedrock-agentcore deploy --region us-east-1
```

**Save the agent ARN** from output:
```
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/ray_code_interpreter-ABC123
```

### Step 4: Deploy Spark Supervisor Agent

```bash
cd ../spark-supervisor-agent

# Review configuration
cat .bedrock_agentcore.yaml

# Deploy agent
bedrock-agentcore deploy --region us-east-1
```

**Save the agent ARN** from output:
```
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-XYZ789
```

### Step 5: Update Configuration

```bash
cd ../../config

# Edit deployment-config.json with agent ARNs
cat > deployment-config.json <<EOF
{
  "account_id": "$AWS_ACCOUNT_ID",
  "region": "us-east-1",
  "environment": "dev",
  "s3_bucket": "spark-data-$AWS_ACCOUNT_ID-us-east-1",
  "lambda_function": "dev-spark-on-lambda",
  "emr_application_id": "YOUR_EMR_APP_ID",
  "emr_execution_role_arn": "arn:aws:iam::$AWS_ACCOUNT_ID:role/dev-spark-emr-execution-role",
  "code_gen_agent_arn": "YOUR_CODE_GEN_AGENT_ARN",
  "spark_supervisor_arn": "YOUR_SPARK_SUPERVISOR_ARN",
  "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}
EOF
```

### Step 6: Deploy Backend

```bash
cd ../backend

# Update config_snowflake.py with values from deployment-config.json
# The file already has the correct structure, just verify values

# Deploy backend Lambda
./deploy-backend.sh
```

### Step 7: Configure ALB Target

```bash
# Get backend Lambda ARN
BACKEND_LAMBDA_ARN=$(aws lambda get-function \
  --function-name dev-spark-supervisor-invocation \
  --region us-east-1 \
  --query 'Configuration.FunctionArn' \
  --output text)

# Register Lambda with ALB target group
TARGET_GROUP_ARN=$(aws elbv2 describe-target-groups \
  --names dev-spark-backend-tg \
  --region us-east-1 \
  --query 'TargetGroups[0].TargetGroupArn' \
  --output text)

aws elbv2 register-targets \
  --target-group-arn $TARGET_GROUP_ARN \
  --targets Id=$BACKEND_LAMBDA_ARN \
  --region us-east-1
```

## Post-Deployment Configuration

### 1. Upload JDBC Drivers (if using PostgreSQL/Snowflake)

```bash
# PostgreSQL driver
aws s3 cp postgresql-42.7.8.jar \
  s3://spark-data-$AWS_ACCOUNT_ID-us-east-1/jars/

# Snowflake driver (if needed)
aws s3 cp snowflake-jdbc-3.14.4.jar \
  s3://spark-data-$AWS_ACCOUNT_ID-us-east-1/jars/
```

### 2. Configure Bedrock Model Access

```bash
# Request model access in Bedrock console
# Or use CLI:
aws bedrock put-model-invocation-logging-configuration \
  --logging-config '{"cloudWatchConfig":{"logGroupName":"/aws/bedrock/modelinvocations","roleArn":"arn:aws:iam::'$AWS_ACCOUNT_ID':role/BedrockLoggingRole"}}' \
  --region us-east-1
```

### 3. Set Up CloudWatch Alarms

```bash
cd ../scripts
./setup-monitoring.sh
```

## Verification

### 1. Health Check

```bash
ALB_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
  --output text)

curl $ALB_URL/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-12-11T20:00:00Z"
}
```

### 2. Test Spark Code Generation

```bash
curl -X POST $ALB_URL/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 10 rows of sample data",
    "session_id": "test-'$(date +%s)'",
    "execution_platform": "lambda"
  }'
```

**Expected response:**
```json
{
  "success": true,
  "result": {
    "spark_code": "from pyspark.sql import SparkSession...",
    "execution_result": "success",
    "actual_results": [...]
  }
}
```

### 3. Check Logs

```bash
# Backend logs
aws logs tail /aws/lambda/dev-spark-supervisor-invocation \
  --follow \
  --region us-east-1

# Agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-*/DEFAULT \
  --follow \
  --region us-east-1

# Lambda execution logs
aws logs tail /aws/lambda/dev-spark-on-lambda \
  --follow \
  --region us-east-1
```

### 4. Verify S3 Bucket

```bash
aws s3 ls s3://spark-data-$AWS_ACCOUNT_ID-us-east-1/
```

**Expected structure:**
```
PRE output/
PRE scripts/
PRE logs/
PRE jars/
```

### 5. Verify EMR Application

```bash
aws emr-serverless get-application \
  --application-id YOUR_EMR_APP_ID \
  --region us-east-1
```

**Expected state:** `CREATED`

## Troubleshooting

### Deployment Fails

**Issue**: CloudFormation stack creation fails

**Solutions**:
1. Check CloudFormation events:
```bash
aws cloudformation describe-stack-events \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --max-items 20
```

2. Verify VPC and subnets exist
3. Check IAM permissions
4. Review CloudFormation template syntax

### Agent Deployment Fails

**Issue**: bedrock-agentcore deploy fails

**Solutions**:
1. Verify bedrock-agentcore CLI is installed:
```bash
bedrock-agentcore --version
```

2. Check Docker is running:
```bash
docker ps
```

3. Verify AWS credentials:
```bash
aws sts get-caller-identity
```

4. Check agent code syntax:
```bash
python -m py_compile spark_supervisor_agent.py
```

### Backend Not Responding

**Issue**: ALB health check fails

**Solutions**:
1. Check Lambda function exists:
```bash
aws lambda get-function \
  --function-name dev-spark-supervisor-invocation \
  --region us-east-1
```

2. Verify Lambda is registered with target group
3. Check security group rules
4. Review Lambda logs for errors

### Bedrock Throttling

**Issue**: `serviceUnavailableException` errors

**Solutions**:
1. Wait 10-15 minutes between requests
2. Request service quota increase
3. Use different Bedrock model
4. Implement exponential backoff in code

## Next Steps

After successful deployment:

1. **Configure Monitoring**: Set up CloudWatch dashboards
2. **Set Up Alerts**: Configure SNS topics for errors
3. **Enable Logging**: Configure detailed logging
4. **Test Thoroughly**: Run comprehensive test suite
5. **Document**: Update configuration documentation
6. **Train Users**: Provide user training materials

## Rollback Procedure

If deployment fails and you need to rollback:

```bash
cd scripts
./cleanup.sh

# This will:
# - Delete CloudFormation stack
# - Remove S3 bucket
# - Delete AgentCore agents
# - Clean up logs
```

## Support

For deployment issues:
1. Check logs in CloudWatch
2. Review `TROUBLESHOOTING.md`
3. Verify all prerequisites
4. Check AWS service health dashboard

---

**Deployment complete?** Proceed to [CONFIGURATION.md](CONFIGURATION.md) for advanced configuration options.
