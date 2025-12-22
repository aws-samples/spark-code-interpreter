# Deployment Guide - When You Have Valid AWS Credentials

## Prerequisites

1. **Refresh your AWS credentials**:
   ```bash
   aws configure
   # Or refresh your SSO session
   aws sso login --profile your-profile
   ```

2. **Verify credentials work**:
   ```bash
   aws sts get-caller-identity
   ```

## Step-by-Step Deployment

### Step 1: Deploy Spark Supervisor Agent (5 minutes)

```bash
cd agent-code/spark-supervisor-agent

# Method 1: Using Python directly
python3 agent_deployment.py

# Method 2: Using the CLI (if it works)
bedrock-agentcore deploy --region us-east-1
```

**Expected Output**:
```
✅ Spark Supervisor Agent deployed successfully!
ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123
```

**IMPORTANT**: Copy this ARN! You'll need it in Step 3.

### Step 2: Deploy Code Generation Agent (5 minutes)

```bash
cd ../code-generation-agent

# Deploy
python3 agent_deployment.py
```

**Expected Output**:
```
✅ Code Generation Agent deployed successfully!
ARN: arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/code_generation_agent-XYZ789
```

**IMPORTANT**: Copy this ARN too!

### Step 3: Update CloudFormation Template (2 minutes)

Edit `cloudformation/spark-complete-stack.yml`:

Find this line (around line 60):
```yaml
SparkAgentCoreGateway:
  Type: AWS::BedrockAgentCore::Gateway
  Properties:
    Name: !Sub '${Environment}-spark-gateway'
    Description: 'Spark Supervisor Agent Gateway with Cognito JWT and MCP support'
    AgentRuntimeArn: !Sub 'arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:runtime/spark_supervisor_agent-*'
```

Replace the `AgentRuntimeArn` line with your actual ARN from Step 1:
```yaml
    AgentRuntimeArn: 'arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123'
```

Also update `backend/backend/config_snowflake.py`:

Find these lines (around line 30-40):
```python
"spark": {
    ...
    "supervisor_arn": os.getenv("SPARK_SUPERVISOR_ARN", "arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-EZPQeDGCjR")
},
"global": {
    ...
    "code_gen_agent_arn": os.getenv("CODE_GEN_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/ray_code_interpreter-oTKmLH9IB9"),
}
```

Replace with your ARNs:
```python
"spark": {
    ...
    "supervisor_arn": os.getenv("SPARK_SUPERVISOR_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/spark_supervisor_agent-ABC123")
},
"global": {
    ...
    "code_gen_agent_arn": os.getenv("CODE_GEN_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:123456789012:runtime/code_generation_agent-XYZ789"),
}
```

### Step 4: Deploy Infrastructure (15-20 minutes)

```bash
cd ../../scripts
./deploy-complete-stack.sh
```

This will:
- ✅ Create Cognito User Pool
- ✅ Create AgentCore Gateway (HTTP + MCP)
- ✅ Create S3 Bucket
- ✅ Create EMR Serverless Application
- ✅ Create Application Load Balancer
- ✅ Create IAM Roles

**Wait for completion** - this takes 15-20 minutes.

**Expected Output**:
```
✅ CloudFormation stack deployed successfully
S3 Bucket: spark-data-123456789012-us-east-1
EMR Application ID: 00g1k848jaqqjf09
ALB URL: http://dev-spark-alb-123456789.us-east-1.elb.amazonaws.com
```

### Step 5: Verify Gateway (1 minute)

```bash
cd ../backend/backend
./deploy-gateway.sh
```

**Expected Output**:
```
✅ Gateway ID: gw-abc123
✅ HTTP URL: https://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
✅ MCP URL: mcp://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com
```

### Step 6: Create Test User (1 minute)

```bash
./create-test-user.sh
```

**Prompts**:
```
Email address: test@example.com
Password: Test123!@#
```

**Requirements**:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one symbol

**Expected Output**:
```
✅ User created successfully!
Username: test@example.com
```

### Step 7: Get JWT Token (1 minute)

```bash
./get-jwt-token.sh
```

**Prompts**:
```
Username (email): test@example.com
Password: [hidden]
```

**Expected Output**:
```
✅ Authentication successful!

ID Token (use this for API calls):
eyJraWQiOiJ...very-long-token...

Access Token:
eyJraWQiOiJ...another-long-token...

Refresh Token (valid for 30 days):
eyJjdHkiOiJ...refresh-token...

Export as environment variable:
export SPARK_JWT_TOKEN="eyJraWQiOiJ..."

Test the gateway:
curl -H 'Authorization: Bearer eyJraWQiOiJ...' https://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com/invoke
```

**IMPORTANT**: Copy the ID Token!

### Step 8: Test HTTP Endpoint (2 minutes)

```bash
# Set the token
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

**Expected Response**:
```json
{
  "success": true,
  "session_id": "spark-abc123...",
  "result": {
    "spark_code": "from pyspark.sql import SparkSession\n...",
    "execution_result": "success",
    "execution_message": "Lambda execution completed successfully",
    "execution_output": [
      "Processing data...",
      "10 rows written"
    ],
    "actual_results": [
      {"id": 1, "name": "Alice", "age": 30},
      {"id": 2, "name": "Bob", "age": 25},
      ...
    ],
    "s3_output_path": "s3://spark-data-123456789012-us-east-1/output/spark-abc123"
  },
  "user_id": "cognito-user-sub-id"
}
```

### Step 9: Configure MCP (Optional, 5 minutes)

#### Get MCP URL

```bash
MCP_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayMcpUrl`].OutputValue' \
  --output text)

echo "MCP URL: $MCP_URL"
```

#### Configure Claude Desktop

Create or edit `~/.config/claude/mcp.json`:

```json
{
  "mcpServers": {
    "spark-gateway": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-http",
        "<paste-mcp-url-here>"
      ],
      "env": {
        "AUTHORIZATION": "Bearer <paste-jwt-token-here>"
      }
    }
  }
}
```

**Note**: You'll need to refresh the JWT token every hour (or use refresh token).

#### Test in Claude Desktop

1. Restart Claude Desktop
2. Start a new conversation
3. Try: "Can you create a sample dataset with 10 rows using Spark?"
4. Claude should use the `invoke_spark_agent` tool

## Verification Checklist

- [ ] AWS credentials are valid
- [ ] Spark Supervisor Agent deployed (ARN saved)
- [ ] Code Generation Agent deployed (ARN saved)
- [ ] CloudFormation template updated with agent ARN
- [ ] config_snowflake.py updated with both ARNs
- [ ] Infrastructure deployed successfully
- [ ] Gateway URL obtained
- [ ] MCP URL obtained
- [ ] Test user created
- [ ] JWT token obtained
- [ ] HTTP endpoint test passed
- [ ] MCP configured in Claude Desktop (optional)

## Troubleshooting

### Issue: "ExpiredToken" error

**Solution**: Refresh AWS credentials
```bash
aws sso login --profile your-profile
# Or
aws configure
```

### Issue: Agent deployment fails

**Check**:
1. AWS credentials are valid
2. You have permissions for Bedrock AgentCore
3. Docker is running (if using containers)

**Solution**:
```bash
# Check credentials
aws sts get-caller-identity

# Check Docker
docker ps

# Try deployment again
cd agent-code/spark-supervisor-agent
python3 agent_deployment.py
```

### Issue: CloudFormation fails with "AgentRuntimeArn not found"

**Solution**: Make sure you updated the CloudFormation template with the actual agent ARN from Step 1.

### Issue: "401 Unauthorized" when testing

**Solution**: Token expired or invalid
```bash
# Get new token
cd backend/backend
./get-jwt-token.sh
```

### Issue: Gateway not found

**Solution**: Check CloudFormation stack status
```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].StackStatus'
```

## Next Steps After Deployment

1. **Add more users**:
   ```bash
   cd backend/backend
   ./create-test-user.sh
   ```

2. **Configure PostgreSQL connections** (if needed):
   - Edit `config_snowflake.py`
   - Add PostgreSQL connection details

3. **Configure Glue tables** (if needed):
   - Create Glue databases and tables
   - Test with Glue data sources

4. **Monitor**:
   ```bash
   # Gateway logs
   GATEWAY_ID=$(aws cloudformation describe-stacks \
     --stack-name dev-spark-complete-stack \
     --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
     --output text)
   
   aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow
   ```

5. **Scale**: Gateway scales automatically - no configuration needed!

## Useful Commands

```bash
# Get all CloudFormation outputs
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs'

# List Cognito users
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text)

aws cognito-idp list-users --user-pool-id $USER_POOL_ID

# Delete a user
aws cognito-idp admin-delete-user \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com

# View Spark execution logs
aws logs tail /aws/lambda/dev-spark-on-lambda --follow

# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-* --follow
```

## Total Time Estimate

- Agent deployments: ~10 minutes
- Infrastructure: ~15-20 minutes
- Testing: ~5 minutes
- **Total: ~30-35 minutes**

---

**Ready to deploy?** Make sure your AWS credentials are valid and start with Step 1!
