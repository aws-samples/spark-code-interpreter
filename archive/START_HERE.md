# 🚀 START HERE - Spark AgentCore Gateway Deployment

## Welcome!

You're about to deploy a **fully managed AWS AgentCore Gateway** with Cognito JWT authentication and MCP protocol support for your Spark Supervisor Agent.

## What You're Getting

- ✅ **AWS AgentCore Gateway** - Managed service (no custom code!)
- ✅ **Cognito Authentication** - JWT tokens with automatic verification
- ✅ **HTTP + MCP Protocols** - REST API and Model Context Protocol
- ✅ **Spark Supervisor Agent** - AI-powered Spark code generation and execution
- ✅ **Auto-scaling** - Handles any load automatically
- ✅ **Production-ready** - Secure, monitored, and cost-optimized

## Prerequisites

1. **Valid AWS credentials**:
   ```bash
   aws configure
   # Or
   aws sso login --profile your-profile
   ```

2. **Verify credentials work**:
   ```bash
   aws sts get-caller-identity
   ```

3. **Required tools** (will be checked automatically):
   - Python 3.11+
   - Docker
   - jq
   - AWS CLI

## Choose Your Deployment Method

### Option 1: One-Command Deployment (Recommended) ⚡

**Fastest and easiest!** Everything automated in one script.

```bash
cd scripts
./deploy-all-automated.sh
```

**Time: ~30-35 minutes**

See: [ONE_COMMAND_DEPLOY.md](ONE_COMMAND_DEPLOY.md)

### Option 2: Manual Step-by-Step 📋

**More control** over each step.

See: [DEPLOY_WITH_VALID_CREDENTIALS.md](DEPLOY_WITH_VALID_CREDENTIALS.md)

**Time: ~30-35 minutes**

### Option 3: Quick Deploy Guide 📖

**Simplified guide** with essential steps only.

See: [QUICK_DEPLOY.md](QUICK_DEPLOY.md)

**Time: ~30-35 minutes**

## Recommended: Use Option 1

The automated script is the easiest and most reliable:

```bash
# 1. Ensure AWS credentials are valid
aws sts get-caller-identity

# 2. Run the deployment
cd scripts
./deploy-all-automated.sh

# 3. Follow the prompts
# - It will ask if you want to create a test user
# - Enter email and password when prompted

# 4. Done! ☕
# The script handles everything automatically
```

## What Happens During Deployment

### Automated Steps (Option 1)

1. **Verify prerequisites** (1 min)
   - Checks AWS credentials
   - Checks required tools

2. **Deploy Spark Supervisor Agent** (5 min)
   - Deploys agent
   - Extracts ARN automatically
   - Waits for agent to be ready

3. **Deploy Code Generation Agent** (5 min)
   - Deploys agent
   - Extracts ARN automatically
   - Waits for agent to be ready

4. **Update configuration** (2 min)
   - Updates CloudFormation template
   - Updates config files
   - Creates backups

5. **Deploy infrastructure** (15-20 min)
   - Builds Docker image
   - Deploys CloudFormation stack
   - Creates all AWS resources

6. **Get outputs** (1 min)
   - Retrieves URLs and IDs
   - Saves configuration

7. **Create test user** (2 min, optional)
   - Creates Cognito user
   - Gets JWT token
   - Tests gateway

**Total: ~30-35 minutes**

## After Deployment

### What You'll Have

```json
{
  "spark_supervisor_arn": "arn:aws:bedrock-agentcore:...",
  "code_gen_agent_arn": "arn:aws:bedrock-agentcore:...",
  "gateway_http_url": "https://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com",
  "gateway_mcp_url": "mcp://abc123.gateway.bedrock-agentcore.us-east-1.amazonaws.com",
  "cognito_user_pool_id": "us-east-1_ABC123",
  "s3_bucket": "spark-data-123456789012-us-east-1",
  "jwt_token": "eyJraWQiOiJ..." (in /tmp/jwt_token.txt)
}
```

### Test the Gateway

```bash
# Get token and URL
JWT_TOKEN=$(cat /tmp/jwt_token.txt)
GATEWAY_URL=$(jq -r '.gateway_http_url' config/deployment-config.json)

# Test
curl -X POST $GATEWAY_URL/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 10 rows",
    "execution_platform": "lambda"
  }'
```

### Configure MCP (Optional)

For Claude Desktop or other MCP clients:

```bash
MCP_URL=$(jq -r '.gateway_mcp_url' config/deployment-config.json)

# Create config
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

## Documentation

### Quick References
- **One-Command Deploy**: [ONE_COMMAND_DEPLOY.md](ONE_COMMAND_DEPLOY.md) ⭐
- **Manual Deploy**: [DEPLOY_WITH_VALID_CREDENTIALS.md](DEPLOY_WITH_VALID_CREDENTIALS.md)
- **Quick Guide**: [QUICK_DEPLOY.md](QUICK_DEPLOY.md)

### Detailed Documentation
- **Gateway README**: [backend/backend/AGENTCORE_GATEWAY_README.md](backend/backend/AGENTCORE_GATEWAY_README.md)
- **Implementation**: [AGENTCORE_GATEWAY_IMPLEMENTATION.md](AGENTCORE_GATEWAY_IMPLEMENTATION.md)
- **Architecture**: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Troubleshooting**: [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

### Status & Summary
- **Deployment Ready**: [DEPLOYMENT_READY.md](DEPLOYMENT_READY.md)
- **Final Summary**: [FINAL_IMPLEMENTATION_SUMMARY.md](FINAL_IMPLEMENTATION_SUMMARY.md)

## Troubleshooting

### AWS Credentials Expired

```bash
# Refresh credentials
aws sso login --profile your-profile
# Or
aws configure
```

### Script Fails

```bash
# Check logs
cat /tmp/spark_supervisor_deploy.log
cat /tmp/code_gen_deploy.log

# Check CloudFormation
aws cloudformation describe-stack-events \
  --stack-name dev-spark-complete-stack \
  --max-items 20
```

### Gateway Not Working

```bash
# Check gateway logs
GATEWAY_ID=$(jq -r '.gateway_id' config/deployment-config.json)
aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow
```

## Support

### Common Issues

1. **"ExpiredToken" error** → Refresh AWS credentials
2. **"No module named bedrock_agentcore"** → Run: `pip3 install --upgrade bedrock-agentcore-starter-toolkit`
3. **Docker build fails** → Ensure Docker is running: `docker ps`
4. **CloudFormation fails** → Check VPC and subnets exist

### Get Help

1. Check the documentation files above
2. Review CloudWatch logs
3. Check AWS Console → CloudFormation for stack status
4. Check AWS Console → Bedrock → AgentCore for agent status

## Next Steps After Deployment

1. **Create more users**:
   ```bash
   cd backend/backend
   ./create-test-user.sh
   ```

2. **Get new JWT tokens**:
   ```bash
   cd backend/backend
   ./get-jwt-token.sh
   ```

3. **Configure data sources**:
   - Add PostgreSQL connections
   - Set up Glue databases
   - Configure S3 buckets

4. **Monitor**:
   ```bash
   # Gateway logs
   aws logs tail /aws/bedrock-agentcore/gateways/<gateway-id> --follow
   
   # Agent logs
   aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-* --follow
   ```

5. **Scale**: Gateway scales automatically - no configuration needed!

## Cleanup

To remove everything:

```bash
cd scripts
./cleanup.sh
```

## Quick Command Reference

```bash
# Deploy everything
cd scripts && ./deploy-all-automated.sh

# Create user
cd backend/backend && ./create-test-user.sh

# Get token
cd backend/backend && ./get-jwt-token.sh

# Test gateway
JWT_TOKEN=$(cat /tmp/jwt_token.txt)
GATEWAY_URL=$(jq -r '.gateway_http_url' config/deployment-config.json)
curl -H "Authorization: Bearer $JWT_TOKEN" $GATEWAY_URL/invoke -d '{"prompt":"test"}'

# View logs
GATEWAY_ID=$(jq -r '.gateway_id' config/deployment-config.json)
aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow

# Cleanup
cd scripts && ./cleanup.sh
```

---

## 🎯 Ready to Deploy?

### Recommended Path:

1. **Verify AWS credentials**:
   ```bash
   aws sts get-caller-identity
   ```

2. **Run one-command deployment**:
   ```bash
   cd scripts
   ./deploy-all-automated.sh
   ```

3. **Wait ~30-35 minutes** ☕

4. **Test and enjoy!** 🎉

---

**Questions?** Check [ONE_COMMAND_DEPLOY.md](ONE_COMMAND_DEPLOY.md) for detailed information.

**Issues?** See the Troubleshooting section above or check the documentation files.

**Ready?** Let's go! 🚀

```bash
cd scripts
./deploy-all-automated.sh
```
