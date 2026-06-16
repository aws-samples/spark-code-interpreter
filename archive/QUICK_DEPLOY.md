# Quick Deployment Guide - AWS AgentCore Gateway with Cognito

## What You're Deploying

- ✅ **AWS AgentCore Gateway** (Managed service - no custom code!)
- ✅ **Cognito User Pool** (JWT authentication)
- ✅ **HTTP + MCP Protocols** (Native support)
- ✅ **Spark Supervisor Agent** (Your existing agent)

## Prerequisites

- AWS CLI configured
- Python 3.11+
- bedrock-agentcore CLI: `pip install bedrock-agentcore-starter-toolkit`
- jq installed

## Step-by-Step Deployment

### 1. Deploy Spark Supervisor Agent FIRST (5 minutes)

**Important**: Deploy the agent before the infrastructure so you have the ARN.

```bash
cd agent-code/spark-supervisor-agent
bedrock-agentcore deploy --region us-east-1
```

**Copy the Agent ARN** from the output. It looks like:
```
arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123
```

### 2. Deploy Code Generation Agent (5 minutes)

```bash
cd ../code-generation-agent
bedrock-agentcore deploy --region us-east-1
```

**Copy this ARN too.**

### 3. Update CloudFormation Template (1 minute)

Edit `cloudformation/spark-complete-stack.yml`:

Find this section:
```yaml
SparkAgentCoreGateway:
  Type: AWS::BedrockAgentCore::Gateway
  Properties:
    AgentRuntimeArn: !Sub 'arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:runtime/spark_supervisor_agent-*'
```

Replace the `AgentRuntimeArn` with your actual ARN:
```yaml
    AgentRuntimeArn: 'arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123'
```

Also update `config_snowflake.py` with both ARNs:
```python
"spark": {
    "supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:...:runtime/spark_supervisor_agent-ABC123"
},
"global": {
    "code_gen_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:...:runtime/code_generation_agent-XYZ789"
}
```

### 4. Deploy Infrastructure (15-20 minutes)

```bash
cd ../../scripts
./deploy-complete-stack.sh
```

This creates:
- ✅ Cognito User Pool
- ✅ **AgentCore Gateway** (HTTP + MCP endpoints)
- ✅ S3 Bucket
- ✅ EMR Serverless Application
- ✅ Application Load Balancer
- ✅ IAM Roles

**Wait for completion before proceeding.**

### 5. Verify Gateway Deployment (1 minute)

```bash
cd ../backend/backend
./deploy-gateway.sh
```

This will show you:
- Gateway ID
- HTTP URL
- MCP URL

### 6. Create Test User (1 minute)

```bash
./create-test-user.sh
```

Enter:
- Email: `test@example.com`
- Password: `Test123!@#` (min 8 chars, uppercase, lowercase, number, symbol)

### 7. Get JWT Token (1 minute)

```bash
./get-jwt-token.sh
```

Enter credentials from step 6.

**Copy the ID Token** - you'll need it for API calls.

### 8. Test HTTP Endpoint (1 minute)

```bash
export JWT_TOKEN="<paste-id-token-here>"

# Get Gateway URL
GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text)

echo "Gateway URL: $GATEWAY_URL"

# Test invoke endpoint
curl -X POST $GATEWAY_URL/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 10 rows of sample data with columns: id, name, age",
    "execution_platform": "lambda"
  }'
```

Expected response:
```json
{
  "success": true,
  "session_id": "spark-...",
  "result": {
    "spark_code": "from pyspark.sql import SparkSession...",
    "execution_result": "success",
    "actual_results": [
      {"id": 1, "name": "Alice", "age": 30},
      ...
    ]
  }
}
```

## MCP Integration (Optional)

### For Claude Desktop

1. Get MCP URL:

```bash
MCP_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayMcpUrl`].OutputValue' \
  --output text)

echo "MCP URL: $MCP_URL"
```

2. Create MCP config file:

```bash
mkdir -p ~/.config/claude
cat > ~/.config/claude/mcp.json <<EOF
{
  "mcpServers": {
    "spark-gateway": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-http",
        "$MCP_URL"
      ],
      "env": {
        "AUTHORIZATION": "Bearer $JWT_TOKEN"
      }
    }
  }
}
EOF
```

3. Restart Claude Desktop

4. Test in Claude:
```
User: Can you create a sample dataset with 10 rows?
Claude: [Uses invoke_spark_agent tool via MCP]
```

## Verification Checklist

- [ ] Spark Supervisor Agent deployed
- [ ] Code Generation Agent deployed
- [ ] CloudFormation template updated with agent ARNs
- [ ] Infrastructure deployed successfully
- [ ] Gateway URL obtained
- [ ] MCP URL obtained
- [ ] Test user created
- [ ] JWT token obtained
- [ ] HTTP endpoint works
- [ ] MCP integration configured (optional)

## Key Differences from Custom Gateway

### ❌ What You DON'T Need
- No FastAPI code
- No Docker images
- No Lambda function for gateway
- No custom JWT verification
- No custom MCP server

### ✅ What AWS Provides
- Managed AgentCore Gateway
- Built-in JWT verification
- Native MCP support
- Automatic scaling
- Built-in monitoring

## Common Issues

### Issue: "AgentRuntimeArn not found"
**Solution**: Deploy the agent first (Step 1), then update CloudFormation template with the ARN.

### Issue: "401 Unauthorized"
**Solution**: Token expired. Get new token:
```bash
./get-jwt-token.sh
```

### Issue: Gateway not found
**Solution**: Verify CloudFormation stack deployed successfully:
```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].StackStatus'
```

## Next Steps

1. **Add more users**: Run `./create-test-user.sh` again
2. **Configure PostgreSQL**: Add PostgreSQL connections in config
3. **Configure Glue**: Set up Glue databases and tables
4. **Monitor**: Check CloudWatch logs
5. **Scale**: Gateway scales automatically!

## Useful Commands

```bash
# Get Gateway URLs
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text

aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayMcpUrl`].OutputValue' \
  --output text

# List Cognito users
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text)

aws cognito-idp list-users --user-pool-id $USER_POOL_ID

# View gateway logs
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow
```

## Support

- Gateway README: `backend/backend/AGENTCORE_GATEWAY_README.md`
- Architecture: `docs/ARCHITECTURE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`

## Total Deployment Time

- Agents: ~10 minutes
- Infrastructure: ~15-20 minutes
- Testing: ~5 minutes
- **Total: ~30-35 minutes**

---

**Ready to deploy? Start with Step 1!**

## Prerequisites

- AWS CLI configured
- Docker installed
- Python 3.11+
- bedrock-agentcore CLI: `pip install bedrock-agentcore-starter-toolkit`
- jq installed

## Step-by-Step Deployment

### 1. Deploy Infrastructure (15-20 minutes)

```bash
cd scripts
./deploy-complete-stack.sh
```

This creates:
- ✅ Cognito User Pool
- ✅ S3 Bucket
- ✅ Lambda Functions
- ✅ EMR Serverless Application
- ✅ Application Load Balancer
- ✅ IAM Roles

**Wait for completion before proceeding.**

### 2. Deploy Spark Supervisor Agent (5 minutes)

```bash
cd agent-code/spark-supervisor-agent
bedrock-agentcore deploy --region us-east-1
```

**Save the Agent ARN from output.**

### 3. Deploy Code Generation Agent (5 minutes)

```bash
cd ../code-generation-agent
bedrock-agentcore deploy --region us-east-1
```

**Save the Agent ARN from output.**

### 4. Update Configuration

```bash
cd ../../backend/backend
```

Edit `config_snowflake.py` and update:
- `spark.supervisor_arn` with Spark Supervisor ARN
- `global.code_gen_agent_arn` with Code Generation ARN

Or set environment variables:
```bash
export SPARK_SUPERVISOR_ARN="arn:aws:bedrock-agentcore:..."
export CODE_GEN_AGENT_ARN="arn:aws:bedrock-agentcore:..."
```

### 5. Deploy Gateway (5 minutes)

```bash
./deploy-gateway.sh
```

This:
- Builds Docker image
- Pushes to ECR
- Updates Lambda function

### 6. Create Test User (1 minute)

```bash
./create-test-user.sh
```

Enter:
- Email: `test@example.com`
- Password: `Test123!@#` (min 8 chars, uppercase, lowercase, number, symbol)

### 7. Get JWT Token (1 minute)

```bash
./get-jwt-token.sh
```

Enter credentials from step 6.

**Copy the ID Token** - you'll need it for API calls.

### 8. Test the Gateway (1 minute)

```bash
# Get ALB URL
ALB_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`ALBUrl`].OutputValue' \
  --output text)

# Test health endpoint (no auth)
curl $ALB_URL/health

# Test authenticated endpoint
export JWT_TOKEN="<paste-id-token-here>"
curl -H "Authorization: Bearer $JWT_TOKEN" $ALB_URL/health
```

### 9. Test Spark Code Generation (2 minutes)

```bash
curl -X POST $ALB_URL/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 10 rows of sample data with columns: id, name, age",
    "session_id": "test-session-1",
    "execution_platform": "lambda"
  }'
```

Expected response:
```json
{
  "success": true,
  "session_id": "test-session-1",
  "result": {
    "spark_code": "from pyspark.sql import SparkSession...",
    "execution_result": "success",
    "execution_message": "Lambda execution completed successfully",
    "execution_output": [...],
    "actual_results": [
      {"id": 1, "name": "Alice", "age": 30},
      ...
    ],
    "s3_output_path": "s3://..."
  }
}
```

## MCP Integration (Optional)

### For Claude Desktop

1. Create MCP config file:

```bash
mkdir -p ~/.config/claude
cat > ~/.config/claude/mcp.json <<EOF
{
  "mcpServers": {
    "spark-gateway": {
      "command": "python",
      "args": ["$(pwd)/mcp_server.py"],
      "env": {
        "SPARK_GATEWAY_URL": "$ALB_URL",
        "SPARK_JWT_TOKEN": "$JWT_TOKEN"
      }
    }
  }
}
EOF
```

2. Restart Claude Desktop

3. Test in Claude:
```
User: Can you create a sample dataset with 10 rows?
Claude: [Uses invoke_spark_agent tool]
```

## Verification Checklist

- [ ] Infrastructure deployed successfully
- [ ] Agents deployed and ARNs saved
- [ ] Gateway Lambda updated
- [ ] Test user created
- [ ] JWT token obtained
- [ ] Health check passes
- [ ] Authenticated request works
- [ ] Spark code generation works
- [ ] MCP integration configured (optional)

## Common Issues

### Issue: "Cognito not configured"
**Solution**: Verify CloudFormation stack deployed successfully. Check outputs:
```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs'
```

### Issue: "401 Unauthorized"
**Solution**: Token expired. Get new token:
```bash
./get-jwt-token.sh
```

### Issue: "Agent not configured"
**Solution**: Update config with agent ARNs or set environment variables.

### Issue: Docker build fails
**Solution**: Ensure Docker is running:
```bash
docker ps
```

## Next Steps

1. **Add more users**: Run `./create-test-user.sh` again
2. **Configure PostgreSQL**: Add PostgreSQL connections in config
3. **Configure Glue**: Set up Glue databases and tables
4. **Monitor**: Check CloudWatch logs
5. **Scale**: Adjust Lambda memory/timeout as needed

## Useful Commands

```bash
# Get Cognito User Pool ID
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text

# List users
aws cognito-idp list-users \
  --user-pool-id <pool-id>

# View gateway logs
aws logs tail /aws/lambda/dev-spark-gateway --follow

# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-* --follow

# Update Lambda function
cd backend/backend
./deploy-gateway.sh
```

## Support

- Gateway README: `backend/backend/GATEWAY_README.md`
- Migration Summary: `GATEWAY_MIGRATION_SUMMARY.md`
- Architecture: `docs/ARCHITECTURE.md`
- Troubleshooting: `docs/TROUBLESHOOTING.md`

## Total Deployment Time

- Infrastructure: ~15-20 minutes
- Agents: ~10 minutes
- Gateway: ~5 minutes
- Testing: ~5 minutes
- **Total: ~35-40 minutes**

---

**Ready to deploy? Start with Step 1!**
