# Complete Deployment Guide

## Overview

This guide covers deploying the complete Spark Code Interpreter stack in a new AWS account. All components use Claude Sonnet 4.5 by default and include automatic S3 configuration.

## Architecture

```
User/Application
    ↓ (JWT Token)
AgentCore Gateway (MCP)
    ↓
Wrapper Lambda
    ↓
Spark Supervisor Agent
    ↓
Code Generation Agent
    ↓
Spark Lambda (PySpark)
    ↓
S3 (Session-based Results)
```

## Prerequisites

1. **AWS Account** with appropriate permissions
2. **AWS CLI** configured with credentials
3. **Docker** with buildx support
4. **Python 3.11+** installed
5. **bedrock-agentcore-starter-toolkit** installed
6. **jq** installed (for JSON parsing)

## Configuration Summary

| Component | Value |
|-----------|-------|
| Model | Claude Sonnet 4.5 (`us.anthropic.claude-sonnet-4-5-20250929-v1:0`) |
| Wrapper Lambda Timeout | 900s (15 min) |
| Spark Lambda Timeout | 300s (5 min) |
| S3 Structure | `s3://spark-data-{account}-{region}/{session-id}/` |
| Region | us-east-1 (configurable) |

## Quick Deployment (Recommended)

### One Command Deployment

For the simplest deployment, use the all-in-one script:

```bash
./scripts/deploy-all.sh
```

This single command:
1. ✅ Deploys both Bedrock agents
2. ✅ Builds and pushes Spark Lambda Docker image
3. ✅ Deploys complete CloudFormation stack
4. ✅ Waits for everything to be ready
5. ✅ Shows all outputs

**Time**: ~15-20 minutes total

Then skip to [Step 3: Configure Gateway Target](#step-3-configure-gateway-target-manual)

---

## Manual Deployment (Advanced)

If you prefer step-by-step control, follow these steps:

## Step 1: Deploy Bedrock Agents

Agents must be deployed **before** CloudFormation because the stack needs their ARNs.

### 1.1 Deploy Code Generation Agent

```bash
cd agent-code/code-generation-agent
python3 agent_deployment.py

# Note the Agent ARN from output
# Example: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/ray_code_interpreter-XXXXX
```

### 1.2 Deploy Spark Supervisor Agent

```bash
cd ../spark-supervisor-agent
python3 agent_deployment.py

# Note the Agent ARN from output
# Example: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-XXXXX
```

**Note**: Both agents use Claude Sonnet 4.5 as default model. The Spark Supervisor Agent has a fallback if model_id is not provided.

### 1.3 Save Agent ARNs

```bash
# Save for CloudFormation deployment
export CODE_GEN_ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/ray_code_interpreter-XXXXX"
export SUPERVISOR_ARN="arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/spark_supervisor_agent-XXXXX"
```

## Step 2: Deploy Complete Stack

This single script builds the Docker image and deploys CloudFormation.

### 2.1 Run Deployment Script

```bash
./scripts/deploy-stack.sh
```

This script:
1. ✅ Loads agent ARNs from config (saved by deploy-agents.sh)
2. ✅ Creates ECR repository if needed
3. ✅ Builds Docker image with correct platform (linux/amd64)
4. ✅ Includes S3 write fix (JAR classpath)
5. ✅ Pushes to ECR
6. ✅ Deploys CloudFormation stack with all parameters
7. ✅ Includes wrapper Lambda (inline code)
8. ✅ Shows stack outputs

**Note**: The script automatically gets VPC and subnet information from your default VPC.

### 2.2 Verify Deployment

```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs' \
  --output table
```

## Step 3: Configure Gateway Target (Manual)

**IMPORTANT**: Gateway Targets cannot be added via CloudFormation.

### Via AWS Console

1. Go to: https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/gateways
2. Select Gateway: `dev-spark-gateway`
3. Click **"Add target"**
4. Configure:
   - **Name**: `spark-agent`
   - **Type**: `Lambda`
   - **Lambda ARN**: Get from CloudFormation outputs (`WrapperLambdaFunctionArn`)
   - **Tool Schema**:

```json
[
  {
    "name": "ask_agent",
    "description": "Ask Spark Supervisor Agent a natural language question",
    "inputSchema": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "Natural language query"
        }
      },
      "required": ["prompt"]
    }
  }
]
```

5. Click **"Create target"**

## Step 4: Test Deployment

### Test via Lambda Console

1. Go to Lambda Console
2. Select `dev-spark-agent-wrapper`
3. Test with payload:

```json
{"prompt":"what is 7*10"}
```

### Test via CLI

```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"what is 7*10"}' \
  /tmp/response.json

cat /tmp/response.json | jq '.'
```

### Verify S3 Results

```bash
# Get session ID from response
SESSION_ID="..." # From response

# List files
aws s3 ls s3://spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1/$SESSION_ID/ --recursive

# Download generated code
aws s3 cp s3://spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1/$SESSION_ID/${SESSION_ID}_code.py -

# Download results
aws s3 cp s3://spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1/$SESSION_ID/output/ ./results/ --recursive
```

## Troubleshooting

### S3 Write Fails

**Issue**: `ClassNotFoundException: Class org.apache.hadoop.fs.s3a.S3AFileSystem not found`

**Solution**: Already fixed in Docker image. Verify with:
```bash
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

Look for `--jars` parameter in spark-submit command.

### Model Not Found

**Issue**: Agent throws "No model_id found"

**Solution**: Already fixed. Spark Supervisor Agent uses Claude Sonnet 4.5 as default fallback.

### Gateway Timeout

**Issue**: Gateway returns timeout after ~30 seconds

**Solution**: Expected behavior. Lambda continues processing. Check S3 for results.

### Lambda Image Error

**Issue**: `InvalidParameterValueException: image manifest not supported`

**Solution**: Rebuild with correct platform:
```bash
docker buildx build --platform linux/amd64 --load -t dev-spark-lambda:latest .
```

## Summary of Changes

All components have been updated with:

1. **S3 Write Fix**: JAR classpath explicitly added to spark-submit
2. **Model Configuration**: Claude Sonnet 4.5 as default in all components
3. **Lambda Timeouts**: Wrapper 900s, Spark 300s
4. **S3 Structure**: Session-based folders (`{session-id}/`)
5. **CloudFormation**: Complete infrastructure with all fixes

## Next Steps

1. ✅ Deploy in new account (follow this guide)
2. ⏳ Test end-to-end with sample queries
3. ⏳ Set up monitoring and alerts
4. ⏳ Configure cost controls
5. ⏳ Add custom data sources (Glue, PostgreSQL)

---

**Version**: 2.0.0 | **Model**: Claude Sonnet 4.5 | **Updated**: Dec 2025

USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text \
  --region us-east-1)

# Create user
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com \
  --user-attributes Name=email,Value=user@example.com Name=email_verified,Value=true \
  --temporary-password TempPassword123! \
  --region us-east-1

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username user@example.com \
  --password YourPassword123! \
  --permanent \
  --region us-east-1
```

## Step 7: Test the Deployment

### 7.1 Get Authentication Token

```bash
# Use the provided script
cd scripts
./get-user-token.sh user@example.com YourPassword123!

# Or manually
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' \
  --output text)

CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text)

# Calculate SECRET_HASH
SECRET_HASH=$(echo -n "user@example.com$CLIENT_ID" | \
  openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | \
  base64)

# Get ID token
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters \
    USERNAME=user@example.com,PASSWORD=YourPassword123!,SECRET_HASH=$SECRET_HASH \
  --query 'AuthenticationResult.IdToken' \
  --output text
```

### 7.2 Test Gateway

```bash
# Get Gateway URL
GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text)

# Test with token
curl -X POST "$GATEWAY_URL/invoke" \
  -H "Authorization: Bearer $ID_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "spark-agent___ask_agent",
    "input": {
      "prompt": "calculate 10 + 20"
    }
  }'
```

### 7.3 Test Wrapper Lambda Directly

```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"calculate 5 + 5"}' \
  --region us-east-1 \
  /tmp/test_response.json

# Wait for processing
sleep 60

# Check response
cat /tmp/test_response.json | jq '.body' -r | jq '.'

# Check S3 for results
SESSION_ID=$(cat /tmp/test_response.json | jq -r '.body' | jq -r '.sessionId')
aws s3 ls s3://spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1/$SESSION_ID/ --recursive
```

## Step 8: Verify S3 Structure

```bash
# List recent sessions
aws s3 ls s3://spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1/ --recursive | tail -20

# Expected structure:
# {session-id}/{session-id}_code.py      # Generated PySpark code
# {session-id}/output/part-*.csv         # Execution results
```

## Configuration Summary

### Key Resources Created

1. **Cognito User Pool** - JWT authentication
2. **AgentCore Gateway** - MCP endpoint with JWT auth
3. **Wrapper Lambda** - Natural language → Agent invocation
4. **Spark Lambda** - PySpark code execution
5. **S3 Bucket** - Session-based data storage
6. **EMR Serverless** - Alternative execution platform
7. **IAM Roles** - Proper permissions for all components

### Important ARNs and IDs

Save these for reference:

```bash
# Get all important values
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[*].[OutputKey,OutputValue]' \
  --output table > deployment-outputs.txt
```

## Troubleshooting

### Issue: Gateway Timeout

**Symptom**: Gateway returns timeout after ~30 seconds

**Solution**: This is expected. Gateway has built-in timeout, but Lambda continues processing. Check S3 for results or invoke Lambda directly.

### Issue: S3 Write Fails

**Symptom**: `No FileSystem for scheme "s3"`

**Solution**: Ensure Spark configuration is passed correctly. The wrapper Lambda includes:
```python
'spark_config': {
    'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem'
}
```

### Issue: Bedrock Throttling

**Symptom**: `modelStreamErrorException`

**Solution**: 
- Wait a few minutes and retry
- Request quota increase via AWS Service Quotas
- Consider using Claude 3.5 Haiku for higher quota

### Issue: Agent Not Found

**Symptom**: `ResourceNotFoundException` when invoking agent

**Solution**: Verify agent ARNs are correct in CloudFormation parameters

## Cleanup

To delete all resources:

```bash
# Delete CloudFormation stack
aws cloudformation delete-stack \
  --stack-name dev-spark-complete-stack \
  --region us-east-1

# Wait for deletion
aws cloudformation wait stack-delete-complete \
  --stack-name dev-spark-complete-stack \
  --region us-east-1

# Delete ECR repository
aws ecr delete-repository \
  --repository-name dev-spark-lambda \
  --force \
  --region us-east-1

# Delete S3 bucket (if not empty)
S3_BUCKET=spark-data-$(aws sts get-caller-identity --query Account --output text)-us-east-1
aws s3 rm s3://$S3_BUCKET --recursive
aws s3 rb s3://$S3_BUCKET

# Delete agents (manual via Console or API)
```

## Next Steps

1. Configure MCP client to use Gateway endpoint
2. Set up monitoring and logging
3. Configure CloudWatch alarms
4. Implement cost controls
5. Set up CI/CD pipeline for updates

## Support

For issues or questions:
- Check `COMPLETE_CHANGES_CHECKLIST.md` for detailed changes
- Review `S3_WRITE_FIX.md` for S3 configuration details
- See `GATEWAY_TARGET_CONFIG.md` for Gateway Target schema
