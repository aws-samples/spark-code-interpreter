# AWS AgentCore Gateway with Cognito JWT and MCP Support

This implementation uses the native **AWS AgentCore Gateway** service to expose the Spark Supervisor Agent with Cognito JWT authentication and MCP protocol support.

## Architecture

```
External Application
    │
    ├─→ HTTP Client (with JWT token)
    │       │
    │       ▼
    │   AWS AgentCore Gateway (HTTP)
    │       │
    │       ├─→ Cognito JWT Verification (Managed by AWS)
    │       │
    │       ▼
    │   Spark Supervisor Agent
    │
    └─→ MCP Client (with JWT token)
            │
            ▼
        AWS AgentCore Gateway (MCP)
            │
            ├─→ Cognito JWT Verification (Managed by AWS)
            │
            ▼
        Spark Supervisor Agent
            │
            ├─→ Code Generation Agent
            ├─→ Lambda/EMR Execution
            └─→ Result Retrieval
```

## What is AWS AgentCore Gateway?

AWS AgentCore Gateway is a **managed service** that:
- Exposes AgentCore agents as HTTP and MCP endpoints
- Handles authentication automatically (JWT, API Key, etc.)
- Supports multiple protocols (HTTP, MCP)
- No custom code or Lambda functions needed
- Fully managed by AWS (scaling, monitoring, etc.)

## Key Differences from Custom Implementation

### ❌ What We DON'T Need Anymore
- No FastAPI application
- No custom JWT verification code
- No Lambda function for gateway
- No Docker image building
- No manual CORS configuration
- No custom MCP server implementation

### ✅ What AWS Provides
- Native AgentCore Gateway resource
- Built-in Cognito JWT verification
- Automatic MCP protocol support
- Managed scaling and availability
- Built-in monitoring and logging
- CORS configuration via CloudFormation

## Components

### 1. AgentCore Gateway (CloudFormation)
```yaml
SparkAgentCoreGateway:
  Type: AWS::BedrockAgentCore::Gateway
  Properties:
    Name: dev-spark-gateway
    AgentRuntimeArn: <spark-supervisor-agent-arn>
    AuthenticationConfiguration:
      Type: JWT
      JwtConfiguration:
        Issuer: https://cognito-idp.us-east-1.amazonaws.com/<pool-id>
        Audience: [<app-client-id>]
        JwksUri: https://cognito-idp.us-east-1.amazonaws.com/<pool-id>/.well-known/jwks.json
    ProtocolConfiguration:
      Protocols:
        - HTTP
        - MCP
```

### 2. Cognito User Pool
- Manages user authentication
- Issues JWT tokens
- Configured via CloudFormation

### 3. Spark Supervisor Agent
- Unchanged from previous implementation
- Orchestrates code generation and execution

## Deployment

### Step 1: Deploy Infrastructure

```bash
cd scripts
./deploy-complete-stack.sh
```

This creates:
- ✅ Cognito User Pool
- ✅ AgentCore Gateway (HTTP + MCP)
- ✅ S3, EMR, Lambda, IAM roles
- ✅ Application Load Balancer

### Step 2: Deploy Spark Supervisor Agent

```bash
cd agent-code/spark-supervisor-agent
bedrock-agentcore deploy --region us-east-1
```

**Save the Agent ARN** - you'll need to update the CloudFormation template with it.

### Step 3: Update Gateway with Agent ARN

Edit `cloudformation/spark-complete-stack.yml`:

```yaml
SparkAgentCoreGateway:
  Properties:
    AgentRuntimeArn: <paste-your-agent-arn-here>
```

Then redeploy:

```bash
cd scripts
./deploy-complete-stack.sh
```

### Step 4: Create Test User

```bash
cd backend/backend
./create-test-user.sh
```

### Step 5: Get JWT Token

```bash
./get-jwt-token.sh
```

### Step 6: Test the Gateway

```bash
export JWT_TOKEN="<id-token-from-step-5>"

# Get Gateway URL
GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text)

# Test HTTP endpoint
curl -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -X POST $GATEWAY_URL/invoke \
  -d '{
    "prompt": "create sample data with 10 rows",
    "execution_platform": "lambda"
  }'
```

## HTTP API Usage

### Authentication

All requests require JWT token in Authorization header:

```
Authorization: Bearer <jwt-token>
```

### Invoke Agent

**Endpoint**: `POST /invoke`

**Request**:
```json
{
  "prompt": "analyze sales data and show top 10 products",
  "session_id": "optional-session-id",
  "s3_input_path": "s3://bucket/input.csv",
  "s3_output_path": "s3://bucket/output/",
  "selected_tables": ["database.table1"],
  "selected_postgres_tables": [...],
  "execution_platform": "lambda|emr|auto",
  "skip_generation": false,
  "spark_code": "pre-validated code if skip_generation=true"
}
```

**Response**:
```json
{
  "success": true,
  "session_id": "spark-...",
  "result": {
    "spark_code": "generated PySpark code",
    "execution_result": "success",
    "execution_message": "Job completed successfully",
    "execution_output": ["log line 1", "log line 2"],
    "actual_results": [{"col1": "val1", "col2": "val2"}],
    "s3_output_path": "s3://bucket/output/session-123"
  },
  "user_id": "cognito-user-id"
}
```

### Example with curl

```bash
curl -X POST $GATEWAY_URL/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a dataset with 10 rows",
    "execution_platform": "lambda"
  }'
```

## MCP Protocol Usage

### Get MCP URL

```bash
MCP_URL=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayMcpUrl`].OutputValue' \
  --output text)

echo $MCP_URL
```

### Configure MCP Client

Create `~/.config/claude/mcp.json`:

```json
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
        "AUTHORIZATION": "Bearer <your-jwt-token>"
      }
    }
  }
}
```

### Available MCP Tools

The AgentCore Gateway automatically exposes the agent's tools as MCP tools:

1. **invoke_spark_agent** - Main tool to generate and execute Spark code
2. **select_execution_platform** - Choose Lambda or EMR
3. **validate_spark_code** - Validate generated code
4. **execute_spark_code_lambda** - Execute on Lambda
5. **execute_spark_code_emr** - Execute on EMR
6. **fetch_spark_results** - Get results from S3
7. **fetch_glue_table_schema** - Get Glue table metadata
8. **fetch_postgres_table_schema** - Get PostgreSQL table metadata

### Using with Claude Desktop

1. Configure MCP as shown above
2. Restart Claude Desktop
3. Use natural language:

```
User: Can you analyze my sales data in Glue table sales.transactions?

Claude: I'll use the Spark agent to analyze your data.
[Calls invoke_spark_agent via MCP]
```

## Authentication Flow

### 1. User Authentication

```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <app-client-id> \
  --auth-parameters USERNAME=user@example.com,PASSWORD=password \
  --region us-east-1
```

Returns JWT tokens (ID token, access token, refresh token).

### 2. Token Verification (Automatic)

AgentCore Gateway automatically:
1. Extracts JWT from `Authorization: Bearer <token>` header
2. Fetches Cognito public keys from JWKS URI
3. Verifies token signature
4. Validates token claims (issuer, audience, expiration)
5. Extracts user information
6. Passes request to agent if valid

**No custom code needed!**

### 3. Token Refresh

When ID token expires (1 hour):

```bash
aws cognito-idp initiate-auth \
  --auth-flow REFRESH_TOKEN_AUTH \
  --client-id <app-client-id> \
  --auth-parameters REFRESH_TOKEN=<refresh-token> \
  --region us-east-1
```

## Configuration

### CloudFormation Parameters

```yaml
Parameters:
  Environment: dev
  VpcId: vpc-xxxxx
  PrivateSubnetIds: subnet-xxx,subnet-yyy
  PublicSubnetIds: subnet-aaa,subnet-bbb
```

### Gateway Configuration

Set in CloudFormation template:

```yaml
SparkAgentCoreGateway:
  Properties:
    Name: dev-spark-gateway
    AgentRuntimeArn: <your-agent-arn>
    AuthenticationConfiguration:
      Type: JWT
      JwtConfiguration:
        Issuer: <cognito-issuer>
        Audience: [<app-client-id>]
        JwksUri: <cognito-jwks-uri>
    ProtocolConfiguration:
      Protocols: [HTTP, MCP]
      HttpConfiguration:
        CorsConfiguration:
          AllowOrigins: ['*']
          AllowMethods: [GET, POST, OPTIONS]
          AllowHeaders: ['*']
          AllowCredentials: true
      McpConfiguration:
        Enabled: true
        ServerName: spark-supervisor-agent
        ServerVersion: '1.0.0'
```

## Monitoring

### CloudWatch Logs

AgentCore Gateway logs are in:
```
/aws/bedrock-agentcore/gateways/<gateway-id>
```

View logs:
```bash
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow
```

### Metrics

Monitor in CloudWatch:
- Gateway invocations
- Authentication failures
- Agent execution time
- Error rates

## Troubleshooting

### 401 Unauthorized

**Cause**: Invalid or expired JWT token

**Solution**:
```bash
# Get new token
./get-jwt-token.sh

# Verify token format
echo $JWT_TOKEN | cut -d. -f2 | base64 -d | jq
```

### 403 Forbidden

**Cause**: Token valid but user not authorized

**Solution**:
- Check Cognito user exists
- Verify user is confirmed
- Check token audience matches app client ID

### Gateway Not Found

**Cause**: CloudFormation stack not deployed or failed

**Solution**:
```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].StackStatus'

# Check for errors
aws cloudformation describe-stack-events \
  --stack-name dev-spark-complete-stack \
  --max-items 20
```

### Agent ARN Not Set

**Cause**: Gateway created before agent deployed

**Solution**:
1. Deploy agent first
2. Update CloudFormation template with agent ARN
3. Redeploy stack

## Security

### JWT Token Security
- Tokens signed by Cognito using RS256
- Gateway verifies signature automatically
- Public keys fetched from Cognito JWKS endpoint
- Tokens expire after 1 hour (configurable)

### Network Security
- Gateway is managed by AWS (no exposed infrastructure)
- HTTPS enforced
- CORS configured for web clients
- VPC configuration for EMR

### IAM Permissions
- Gateway has managed IAM role
- Agent has separate execution role
- Least privilege access

## Cost Optimization

### AgentCore Gateway Pricing
- Pay per request
- No idle costs
- No infrastructure to manage
- Automatic scaling

### Comparison with Custom Lambda
| Aspect | Custom Lambda | AgentCore Gateway |
|--------|--------------|-------------------|
| Infrastructure | Manage Lambda, ALB | Fully managed |
| Scaling | Configure concurrency | Automatic |
| Authentication | Custom code | Built-in |
| MCP Support | Custom implementation | Native |
| Cost | Lambda + ALB | Gateway requests only |
| Maintenance | High | Low |

## Migration from Custom Gateway

If you previously had a custom FastAPI gateway:

### What to Remove
- ❌ `gateway.py` (FastAPI app)
- ❌ `mcp_server.py` (custom MCP server)
- ❌ `requirements.txt` (Python dependencies)
- ❌ `Dockerfile` (container image)
- ❌ Gateway Lambda function
- ❌ ECR repository
- ❌ Lambda deployment scripts

### What to Keep
- ✅ `config_snowflake.py` (configuration)
- ✅ `postgres_metadata.py` (metadata fetcher)
- ✅ Spark Supervisor Agent
- ✅ Code Generation Agent
- ✅ Cognito User Pool
- ✅ All infrastructure (S3, EMR, etc.)

### Migration Steps
1. Remove custom gateway code
2. Update CloudFormation with AgentCore Gateway
3. Deploy stack
4. Test with same JWT tokens
5. Update MCP clients with new URL

## Support

### Documentation
- AWS AgentCore Gateway: https://docs.aws.amazon.com/bedrock/latest/userguide/agentcore-gateway.html
- Cognito JWT: https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-with-identity-providers.html
- MCP Protocol: https://modelcontextprotocol.io/

### Troubleshooting
1. Check CloudWatch logs
2. Verify Cognito configuration
3. Test JWT token validity
4. Review IAM permissions

---

**Ready to deploy?** Follow the deployment steps above!
