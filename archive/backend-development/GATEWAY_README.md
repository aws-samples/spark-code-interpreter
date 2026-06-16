# Spark AgentCore Gateway with Cognito JWT Authentication

This gateway replaces the previous FastAPI backend with a secure, JWT-authenticated API that exposes the Spark Supervisor Agent as an MCP server.

## Architecture

```
External Application
    │
    ├─→ MCP Client (with JWT token)
    │       │
    │       ▼
    │   MCP Server (mcp_server.py)
    │       │
    │       ▼
    └─→ Gateway API (gateway.py)
            │
            ├─→ Cognito JWT Verification
            │
            ▼
        Spark Supervisor Agent
            │
            ├─→ Code Generation Agent
            ├─→ Lambda/EMR Execution
            └─→ Result Retrieval
```

## Components

### 1. Gateway API (`gateway.py`)
- FastAPI application with Cognito JWT authentication
- Exposes REST endpoints for agent invocation
- Validates JWT tokens from Cognito
- Wraps Spark Supervisor Agent invocation

### 2. MCP Server (`mcp_server.py`)
- Model Context Protocol server
- Exposes gateway as MCP tools
- Handles authentication with JWT tokens
- Can be used by external applications (Claude Desktop, etc.)

### 3. Cognito User Pool
- Manages user authentication
- Issues JWT tokens
- Configured via CloudFormation

## Deployment

### Step 1: Deploy Infrastructure

```bash
cd scripts
./deploy-complete-stack.sh
```

This creates:
- Cognito User Pool
- Cognito App Client
- Gateway Lambda Function
- All other infrastructure (S3, EMR, etc.)

### Step 2: Deploy Gateway

```bash
cd backend/backend
./deploy-gateway.sh
```

This:
- Builds Docker image
- Pushes to ECR
- Updates Lambda function

### Step 3: Create Test User

```bash
./create-test-user.sh
```

Enter email and password when prompted.

### Step 4: Get JWT Token

```bash
./get-jwt-token.sh
```

This will:
- Authenticate with Cognito
- Return ID token, access token, and refresh token
- Show example curl command

## API Endpoints

### Public Endpoints (No Auth)

#### GET /health
Health check endpoint

```bash
curl https://<alb-url>/health
```

#### GET /
API information

```bash
curl https://<alb-url>/
```

### Authenticated Endpoints (Require JWT)

All authenticated endpoints require the `Authorization` header:

```
Authorization: Bearer <jwt-token>
```

#### POST /invoke
Main endpoint to invoke Spark Supervisor Agent

```bash
curl -X POST https://<alb-url>/invoke \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "analyze sales data and show top 10 products",
    "session_id": "my-session-123",
    "execution_platform": "lambda"
  }'
```

**Request Body:**
```json
{
  "prompt": "Natural language description of Spark job",
  "session_id": "optional-session-id",
  "s3_input_path": "s3://bucket/input.csv",
  "s3_output_path": "s3://bucket/output/",
  "selected_tables": ["database.table1", "database.table2"],
  "selected_postgres_tables": [...],
  "execution_platform": "lambda|emr|auto",
  "skip_generation": false,
  "spark_code": "pre-validated code if skip_generation=true"
}
```

**Response:**
```json
{
  "success": true,
  "session_id": "my-session-123",
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

#### GET /glue/databases
List Glue databases

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://<alb-url>/glue/databases
```

#### GET /glue/tables/{database}
List tables in a Glue database

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://<alb-url>/glue/tables/my_database
```

#### GET /postgres/connections
List PostgreSQL connections

```bash
curl -H "Authorization: Bearer $JWT_TOKEN" \
  https://<alb-url>/postgres/connections
```

## MCP Server Usage

### Configuration

Create an MCP configuration file:

```json
{
  "mcpServers": {
    "spark-gateway": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "SPARK_GATEWAY_URL": "https://<alb-url>",
        "SPARK_JWT_TOKEN": "<your-jwt-token>"
      }
    }
  }
}
```

### Using with Claude Desktop

1. Add the MCP server to Claude Desktop configuration
2. Restart Claude Desktop
3. Use the `invoke_spark_agent` tool in conversations

Example:
```
User: Can you analyze the sales data in my Glue table and show me the top 10 products?

Claude: I'll use the Spark agent to analyze your sales data.
[Uses invoke_spark_agent tool]
```

### Available MCP Tools

1. **invoke_spark_agent** - Main tool to generate and execute Spark code
2. **list_glue_databases** - List available Glue databases
3. **list_glue_tables** - List tables in a database
4. **list_postgres_connections** - List PostgreSQL connections
5. **list_postgres_databases** - List databases in a connection
6. **list_postgres_schemas** - List schemas in a database
7. **list_postgres_tables** - List tables in a schema

## Authentication Flow

### 1. User Authentication

```bash
# Authenticate with Cognito
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id <app-client-id> \
  --auth-parameters USERNAME=user@example.com,PASSWORD=password \
  --region us-east-1
```

Returns:
```json
{
  "AuthenticationResult": {
    "IdToken": "eyJraWQ...",
    "AccessToken": "eyJraWQ...",
    "RefreshToken": "eyJjdHk...",
    "ExpiresIn": 3600
  }
}
```

### 2. Token Verification

The gateway automatically:
1. Extracts JWT from `Authorization: Bearer <token>` header
2. Fetches Cognito public keys
3. Verifies token signature
4. Validates token claims (audience, issuer, expiration)
5. Extracts user information

### 3. Token Refresh

When ID token expires (1 hour), use refresh token:

```bash
aws cognito-idp initiate-auth \
  --auth-flow REFRESH_TOKEN_AUTH \
  --client-id <app-client-id> \
  --auth-parameters REFRESH_TOKEN=<refresh-token> \
  --region us-east-1
```

## Security

### JWT Token Security
- Tokens are signed by Cognito using RS256
- Gateway verifies signature using Cognito public keys
- Public keys are cached for 1 hour
- Tokens expire after 1 hour (configurable)

### IAM Permissions
Gateway Lambda has permissions for:
- Bedrock AgentCore invocation
- S3 read/write
- Glue metadata access
- Secrets Manager (for PostgreSQL)
- EMR Serverless job management

### Network Security
- Gateway runs in Lambda (no exposed ports)
- Accessed via ALB with HTTPS (recommended)
- Cognito handles user authentication
- No hardcoded credentials

## Configuration

### Environment Variables

Set in CloudFormation or Lambda configuration:

```bash
COGNITO_REGION=us-east-1
COGNITO_USER_POOL_ID=us-east-1_xxxxx
COGNITO_APP_CLIENT_ID=xxxxxxxxxxxxxxxxxx
```

### Application Configuration

Uses `config_snowflake.py` for:
- Spark settings (S3 bucket, EMR app ID, etc.)
- PostgreSQL connections
- Bedrock model configuration

## Monitoring

### CloudWatch Logs

Gateway logs are in:
```
/aws/lambda/dev-spark-gateway
```

View logs:
```bash
aws logs tail /aws/lambda/dev-spark-gateway --follow
```

### Metrics

Monitor:
- Lambda invocations
- Lambda errors
- Lambda duration
- Cognito authentication attempts

## Troubleshooting

### 401 Unauthorized

**Cause**: Invalid or expired JWT token

**Solution**:
1. Get a new token with `./get-jwt-token.sh`
2. Verify token is not expired
3. Check token is in correct format: `Bearer <token>`

### 500 Internal Server Error

**Cause**: Gateway or agent error

**Solution**:
1. Check CloudWatch logs
2. Verify Spark Supervisor Agent is deployed
3. Check IAM permissions

### Cognito Not Configured

**Cause**: Environment variables not set

**Solution**:
1. Verify CloudFormation stack deployed successfully
2. Check Lambda environment variables
3. Redeploy gateway with `./deploy-gateway.sh`

## Development

### Local Testing

Run gateway locally:

```bash
# Set environment variables
export COGNITO_REGION=us-east-1
export COGNITO_USER_POOL_ID=us-east-1_xxxxx
export COGNITO_APP_CLIENT_ID=xxxxxxxxxx

# Run gateway
python gateway.py
```

Access at: http://localhost:8000

### Testing MCP Server

```bash
# Set environment variables
export SPARK_GATEWAY_URL=http://localhost:8000
export SPARK_JWT_TOKEN=<your-token>

# Run MCP server
python mcp_server.py
```

## Migration from Old Backend

The new gateway replaces the old FastAPI backend (`main.py`). Key differences:

### Old Backend
- No authentication
- Direct FastAPI endpoints
- Session management in memory
- No MCP support

### New Gateway
- Cognito JWT authentication
- Same REST API with auth
- Stateless (session in agent)
- MCP server included

### Migration Steps

1. Deploy new infrastructure with Cognito
2. Deploy gateway Lambda
3. Update client applications to:
   - Authenticate with Cognito
   - Include JWT token in requests
   - Use new endpoint structure (if changed)

## Support

For issues:
1. Check CloudWatch logs
2. Verify Cognito configuration
3. Test with `./get-jwt-token.sh`
4. Review IAM permissions
