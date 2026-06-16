# How to Send Payloads to the MCP Gateway

## Quick Start

### Test with "what is 5+5"

```bash
cd scripts
./simple-test.sh
```

This sends the question "what is 5+5" to your Gateway.

---

## Send Custom Prompts

### Option 1: Use the Script

```bash
cd scripts
./send-mcp-request.sh "what is 5+5"
./send-mcp-request.sh "create a dataframe with 10 rows"
./send-mcp-request.sh "analyze sales data"
```

### Option 2: Manual curl Command

```bash
# 1. Get your access token first
cd scripts
./quick-test.sh

# 2. Use the token (saved in /tmp/service_access_token.txt)
TOKEN=$(cat /tmp/service_access_token.txt)
GATEWAY_URL="<your-gateway-url>"

# 3. Send request
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "invoke_agent",
      "arguments": {
        "prompt": "what is 5+5"
      }
    }
  }'
```

---

## Payload Format

### MCP Protocol Format (JSON-RPC 2.0)

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "invoke_agent",
    "arguments": {
      "prompt": "what is 5+5"
    }
  }
}
```

### Direct Invocation Format (Alternative)

```json
{
  "prompt": "what is 5+5",
  "execution_platform": "lambda"
}
```

---

## Example Prompts

### Simple Math
```bash
./send-mcp-request.sh "what is 5+5"
./send-mcp-request.sh "calculate 100 * 25"
```

### Spark DataFrame Operations
```bash
./send-mcp-request.sh "create a dataframe with 10 rows and 3 columns"
./send-mcp-request.sh "generate sample sales data"
./send-mcp-request.sh "create a dataframe with names and ages"
```

### Data Analysis
```bash
./send-mcp-request.sh "analyze customer purchase patterns"
./send-mcp-request.sh "calculate average sales by region"
```

---

## Complete Example: Step by Step

### 1. Get Configuration

```bash
REGION=us-east-1
STACK_NAME=dev-spark-complete-stack

GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text)

echo "Gateway URL: $GATEWAY_URL"
```

### 2. Get Access Token

```bash
USER_POOL_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoUserPoolId`].OutputValue' \
  --output text)

CLIENT_ID=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoAppClientId`].OutputValue' \
  --output text)

TOKEN_ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`CognitoTokenEndpoint`].OutputValue' \
  --output text)

CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)

AUTH_HEADER=$(echo -n "${CLIENT_ID}:${CLIENT_SECRET}" | base64)

TOKEN_RESPONSE=$(curl -s -X POST "$TOKEN_ENDPOINT" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "Authorization: Basic $AUTH_HEADER" \
  -d "grant_type=client_credentials" \
  -d "scope=spark-api/spark.execute")

ACCESS_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.access_token')

echo "Access Token: ${ACCESS_TOKEN:0:30}..."
```

### 3. Send Your Request

```bash
# Example: "what is 5+5"
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
      "name": "invoke_agent",
      "arguments": {
        "prompt": "what is 5+5"
      }
    }
  }' | jq '.'
```

---

## Response Format

### Successful Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "The answer is 10"
      }
    ]
  }
}
```

### Error Response

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32600,
    "message": "Invalid Request"
  }
}
```

---

## Available Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `simple-test.sh` | Quick test with "5+5" | `./simple-test.sh` |
| `send-mcp-request.sh` | Send custom prompt | `./send-mcp-request.sh "your prompt"` |
| `quick-test.sh` | Get access token only | `./quick-test.sh` |
| `test-mcp-gateway.sh` | Full MCP protocol test | `./test-mcp-gateway.sh` |
| `test-complete-stack.sh` | Test all components | `./test-complete-stack.sh` |

---

## Troubleshooting

### "Unauthorized" Error

Your token may have expired. Get a new one:

```bash
cd scripts
./quick-test.sh
```

### "Gateway not found" Error

Check your Gateway URL:

```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue'
```

### No Response

Check Gateway status:

```bash
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --region us-east-1
```

---

## Next Steps

1. **Test basic functionality**: `./simple-test.sh`
2. **Send custom prompts**: `./send-mcp-request.sh "your question"`
3. **Configure MCP client**: Use Gateway URL with access token
4. **Add Gateway Targets**: Configure tools in AWS Console

---

## MCP Client Configuration

For Claude Desktop or other MCP clients:

```json
{
  "mcpServers": {
    "spark-gateway": {
      "url": "https://your-gateway-url",
      "headers": {
        "Authorization": "Bearer your-access-token"
      }
    }
  }
}
```

**Note**: Access tokens expire after 1 hour. You'll need to refresh them.

---

## Summary

**Simplest way to test:**
```bash
cd scripts
./simple-test.sh
```

**Send custom prompt:**
```bash
./send-mcp-request.sh "what is 5+5"
```

**Answer to "what is 5+5":** The Gateway will forward your request to the Spark Supervisor Agent, which will process it and return the result: **10** 🎉
