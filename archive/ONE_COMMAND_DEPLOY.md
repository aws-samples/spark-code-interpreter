# One-Command Deployment Guide

## Deploy Everything with a Single Command

This script automates the entire deployment process:
- ✅ Deploys both agents
- ✅ Updates CloudFormation template automatically
- ✅ Deploys infrastructure
- ✅ Creates test user (optional)
- ✅ Tests the gateway
- ✅ Saves all configuration

## Prerequisites

1. **Valid AWS credentials**:
   ```bash
   aws configure
   # Or
   aws sso login --profile your-profile
   ```

2. **Verify credentials**:
   ```bash
   aws sts get-caller-identity
   ```

3. **Required tools** (script will check):
   - Python 3.11+
   - Docker
   - jq
   - AWS CLI

## Run the Deployment

```bash
cd scripts
./deploy-all-automated.sh
```

That's it! The script will:

### Step 1: Deploy Spark Supervisor Agent (5 min)
- Deploys agent
- Extracts ARN automatically
- Waits 30 seconds for agent to be ready

### Step 2: Deploy Code Generation Agent (5 min)
- Deploys agent
- Extracts ARN automatically
- Waits 30 seconds for agent to be ready

### Step 3: Update CloudFormation Template (1 min)
- Automatically updates template with agent ARN
- Creates backup of original

### Step 4: Update Configuration (1 min)
- Updates config_snowflake.py with both ARNs
- Creates backup of original

### Step 5: Deploy Infrastructure (15-20 min)
- Builds and pushes Docker image for Spark Lambda
- Deploys CloudFormation stack
- Creates all resources (Cognito, Gateway, S3, EMR, etc.)
- Waits 60 seconds for resources to be ready

### Step 6: Get Stack Outputs (1 min)
- Retrieves all URLs and IDs
- Saves to config/deployment-config.json

### Step 7: Create Test User (Optional, 2 min)
- Prompts for email and password
- Creates Cognito user
- Gets JWT token
- Tests the gateway
- Saves token to /tmp/jwt_token.txt

**Total Time: ~30-35 minutes**

## What You'll See

```
========================================
Automated Deployment - Spark AgentCore Gateway
========================================
Region: us-east-1
Environment: dev

Step 0: Verifying AWS credentials...
✅ AWS Account: 123456789012

Checking prerequisites...
✅ python3 found
✅ jq found
✅ docker found
✅ bedrock-agentcore-starter-toolkit installed

========================================
Step 1: Deploying Spark Supervisor Agent
========================================

Deploying agent...
✅ Spark Supervisor Agent deployed
ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123

Waiting 30 seconds for agent to be fully ready...

========================================
Step 2: Deploying Code Generation Agent
========================================

Deploying agent...
✅ Code Generation Agent deployed
ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/code_generation_agent-XYZ789

Waiting 30 seconds for agent to be fully ready...

========================================
Step 3: Updating CloudFormation Template
========================================

Updating AgentRuntimeArn in CloudFormation template...
✅ CloudFormation template updated

========================================
Step 4: Updating Configuration File
========================================

Updating config_snowflake.py with agent ARNs...
✅ Configuration file updated

========================================
Step 5: Deploying Infrastructure
========================================

Getting VPC and subnet information...
VPC ID: vpc-abc123
Private Subnets: subnet-xxx,subnet-yyy
Public Subnets: subnet-aaa,subnet-bbb

Building and pushing Spark Lambda Docker image...
✅ Docker image built and pushed

Deploying CloudFormation stack (this takes 15-20 minutes)...
Creating new stack...
Waiting for stack creation to complete...
✅ CloudFormation stack deployed

Waiting 60 seconds for all resources to be fully ready...

========================================
Step 6: Retrieving Stack Outputs
========================================

Gateway ID: gw-abc123
Gateway HTTP URL: https://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
Gateway MCP URL: mcp://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
Cognito User Pool ID: us-east-1_ABC123
Cognito App Client ID: 1234567890abcdef
S3 Bucket: spark-data-123456789012-us-east-1
EMR Application ID: 00g1k848jaqqjf09

✅ Configuration saved to config/deployment-config.json

========================================
Step 7: Creating Test User (Optional)
========================================

Do you want to create a test user? (y/n): y
Email address: test@example.com
Password: ********

Creating user...
✅ Test user created: test@example.com

Getting JWT token...
✅ JWT token obtained

JWT Token:
eyJraWQiOiJ...very-long-token...

Token saved to: /tmp/jwt_token.txt

Testing gateway...
✅ Gateway test successful!

Response:
{
  "success": true,
  "session_id": "spark-abc123",
  "result": {
    "spark_code": "...",
    "execution_result": "success",
    ...
  }
}

========================================
🎉 Deployment Complete!
========================================

Summary:
✅ Spark Supervisor Agent: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123
✅ Code Generation Agent: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/code_generation_agent-XYZ789
✅ AgentCore Gateway: gw-abc123
✅ HTTP URL: https://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
✅ MCP URL: mcp://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
✅ Cognito User Pool: us-east-1_ABC123
✅ S3 Bucket: spark-data-123456789012-us-east-1
✅ EMR Application: 00g1k848jaqqjf09

Next Steps:
1. Create additional users: cd backend/backend && ./create-test-user.sh
2. Get JWT tokens: cd backend/backend && ./get-jwt-token.sh
3. Configure MCP client with: mcp://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
4. View logs: aws logs tail /aws/bedrock-agentcore/gateways/gw-abc123 --follow

Configuration saved to:
- config/deployment-config.json
- /tmp/jwt_token.txt (if test user created)

All done! 🚀
```

## After Deployment

### Use the Gateway

```bash
# Get the token
JWT_TOKEN=$(cat /tmp/jwt_token.txt)

# Get the gateway URL
GATEWAY_URL=$(jq -r '.gateway_http_url' config/deployment-config.json)

# Test it
curl -X POST $GATEWAY_URL/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "analyze sales data",
    "execution_platform": "lambda"
  }'
```

### Configure MCP Client

```bash
# Get MCP URL
MCP_URL=$(jq -r '.gateway_mcp_url' config/deployment-config.json)

# Create Claude Desktop config
mkdir -p ~/.config/claude
cat > ~/.config/claude/mcp.json <<EOF
{
  "mcpServers": {
    "spark-gateway": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-http", "$MCP_URL"],
      "env": {
        "AUTHORIZATION": "Bearer $JWT_TOKEN"
      }
    }
  }
}
EOF
```

### View Logs

```bash
# Gateway logs
GATEWAY_ID=$(jq -r '.gateway_id' config/deployment-config.json)
aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow

# Agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-* --follow

# Spark execution logs
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

### Create More Users

```bash
cd backend/backend
./create-test-user.sh
```

### Get New JWT Token

```bash
cd backend/backend
./get-jwt-token.sh
```

## Troubleshooting

### Script Fails at Step 1 or 2

**Issue**: Agent deployment fails

**Check**:
```bash
# View deployment logs
cat /tmp/spark_supervisor_deploy.log
cat /tmp/code_gen_deploy.log
```

**Common causes**:
- AWS credentials expired
- Insufficient permissions
- Docker not running

### Script Fails at Step 5

**Issue**: CloudFormation deployment fails

**Check**:
```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name dev-spark-complete-stack \
  --max-items 20
```

**Common causes**:
- VPC/subnet issues
- Resource limits
- Docker image build failed

### Gateway Test Fails

**Issue**: Test returns error

**Check**:
```bash
# View gateway logs
GATEWAY_ID=$(jq -r '.gateway_id' config/deployment-config.json)
aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID
```

**Common causes**:
- Agent not fully ready (wait a bit longer)
- JWT token invalid
- Gateway configuration issue

## Cleanup

To remove everything:

```bash
cd scripts
./cleanup.sh
```

This will:
- Delete CloudFormation stack
- Delete agents
- Remove S3 bucket
- Clean up logs

## Environment Variables

You can customize the deployment:

```bash
# Use different environment
export ENVIRONMENT=prod
export AWS_REGION=us-west-2

# Run deployment
./deploy-all-automated.sh
```

## What Gets Created

### AWS Resources
- ✅ Cognito User Pool
- ✅ Cognito App Client
- ✅ AgentCore Gateway (HTTP + MCP)
- ✅ S3 Bucket
- ✅ Lambda Function (Spark execution)
- ✅ EMR Serverless Application
- ✅ Application Load Balancer
- ✅ IAM Roles
- ✅ Security Groups
- ✅ CloudWatch Log Groups

### Local Files
- ✅ config/deployment-config.json
- ✅ /tmp/jwt_token.txt
- ✅ cloudformation/spark-complete-stack.yml.backup
- ✅ backend/backend/config_snowflake.py.backup

## Success Criteria

After running the script, you should have:
- ✅ Both agents deployed
- ✅ Gateway accessible via HTTP
- ✅ Gateway accessible via MCP
- ✅ Test user created (if opted in)
- ✅ JWT token obtained
- ✅ Gateway test passed
- ✅ All configuration saved

## Support

- **Script logs**: Check `/tmp/*.log` files
- **CloudFormation**: Check AWS Console → CloudFormation
- **Agents**: Check AWS Console → Bedrock → AgentCore
- **Gateway**: Check CloudWatch logs

---

**Ready to deploy?** Just run:

```bash
cd scripts
./deploy-all-automated.sh
```

**That's it!** ☕ Grab a coffee and let the script do all the work! (~30-35 minutes)
