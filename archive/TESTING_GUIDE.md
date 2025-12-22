# Complete Testing Guide

## Quick Start - Test in 10 Seconds

### Option 1: Direct Agent Invocation (Recommended - Works Now!)

```bash
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

### Option 2: Via Gateway (Requires Gateway Targets)

```bash
cd scripts
./ask-gateway.sh "what is 5+5"
```

**Note:** If you get "Unknown tool" error, the Gateway doesn't have targets configured yet. Use Option 1 instead.

---

## Understanding the Current Setup

✅ **What's Working:**
- Gateway is deployed
- Authentication (Cognito JWT) works
- MCP protocol works
- Spark Supervisor Agent is deployed
- Direct agent invocation works

❌ **What's Not Working:**
- Gateway has no tools (no Gateway Targets configured)
- Can't call tools through Gateway yet

**Solution:** Use direct agent invocation for now, or add Gateway Targets manually.

---

## All Available Test Scripts

| Script | Purpose | Time | Usage |
|--------|---------|------|-------|
| `ask-gateway.sh` | **Quickest** - Ask any question | 5s | `./ask-gateway.sh "your question"` |
| `get-user-token.sh` | Get ID token with details | 10s | `./get-user-token.sh` |
| `test-with-user-token.sh` | Full MCP test with user auth | 30s | `./test-with-user-token.sh` |
| `simple-test.sh` | Simple "5+5" test | 5s | `./simple-test.sh` |
| `test-mcp-gateway.sh` | Complete MCP protocol test | 60s | `./test-mcp-gateway.sh` |
| `test-complete-stack.sh` | Test all stack components | 2m | `./test-complete-stack.sh` |
| `get-client-credentials.sh` | Get OAuth2 credentials | 10s | `./get-client-credentials.sh` |

---

## Common Test Scenarios

### 1. Ask a Simple Question

```bash
./ask-gateway.sh "what is 5+5"
./ask-gateway.sh "calculate 100 * 25"
./ask-gateway.sh "what is the capital of France"
```

### 2. Spark/Data Questions

```bash
./ask-gateway.sh "create a dataframe with 10 rows"
./ask-gateway.sh "generate sample sales data"
./ask-gateway.sh "create a dataframe with names and ages"
```

### 3. Get a Token for Manual Testing

```bash
# Get token
./get-user-token.sh

# Token is saved to /tmp/id_token.txt
TOKEN=$(cat /tmp/id_token.txt)

# Use it
curl -X POST $GATEWAY_URL \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"invoke_agent","arguments":{"prompt":"your question"}}}'
```

### 4. Test Everything

```bash
# Full stack test
./test-complete-stack.sh

# MCP protocol test
./test-mcp-gateway.sh
```

---

## Understanding the Authentication Flow

### What Happens When You Run a Test:

```
1. Get Configuration
   ├─ Gateway URL
   ├─ User Pool ID
   └─ Client ID

2. Get Client Secret
   └─ Required for SECRET_HASH

3. Create/Update Test User
   ├─ Username: gateway-test@example.com
   └─ Password: TestPass123!

4. Calculate SECRET_HASH
   └─ HMAC-SHA256(username+clientId, clientSecret)

5. Authenticate User
   ├─ Send: username, password, SECRET_HASH
   └─ Receive: ID Token

6. Call Gateway
   ├─ Send: Bearer <ID Token>
   └─ Receive: Response
```

---

## Troubleshooting

### Error: "Invalid Bearer token"

**Cause:** Using wrong token type (access token instead of ID token)

**Fix:** Use the updated scripts that get ID tokens

```bash
./ask-gateway.sh "test"
```

### Error: "SECRET_HASH was not received"

**Cause:** Client has secret but SECRET_HASH not provided

**Fix:** Scripts now calculate SECRET_HASH automatically

```bash
./get-user-token.sh
```

### Error: "User does not exist"

**Cause:** Test user not created

**Fix:** Scripts create user automatically, or create manually:

```bash
aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --user-attributes Name=email,Value=test@example.com Name=email_verified,Value=true \
  --message-action SUPPRESS

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username test@example.com \
  --password "TestPass123!" \
  --permanent
```

### Error: "Gateway not found"

**Cause:** Stack not deployed or wrong region

**Fix:** Check stack status:

```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].StackStatus'
```

---

## Manual Testing

If you want to test manually without scripts:

### Step 1: Get Configuration

```bash
REGION=us-east-1
STACK_NAME=dev-spark-complete-stack

GATEWAY_URL=$(aws cloudformation describe-stacks \
  --stack-name $STACK_NAME \
  --region $REGION \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayUrl`].OutputValue' \
  --output text)

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
```

### Step 2: Get Client Secret

```bash
CLIENT_SECRET=$(aws cognito-idp describe-user-pool-client \
  --user-pool-id $USER_POOL_ID \
  --client-id $CLIENT_ID \
  --query 'UserPoolClient.ClientSecret' \
  --output text \
  --region $REGION)
```

### Step 3: Create User

```bash
USERNAME="test@example.com"
PASSWORD="TestPass123!"

aws cognito-idp admin-create-user \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --user-attributes Name=email,Value=$USERNAME Name=email_verified,Value=true \
  --message-action SUPPRESS \
  --region $REGION

aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password "$PASSWORD" \
  --permanent \
  --region $REGION
```

### Step 4: Calculate SECRET_HASH

```bash
SECRET_HASH=$(echo -n "${USERNAME}${CLIENT_ID}" | \
  openssl dgst -sha256 -hmac "$CLIENT_SECRET" -binary | \
  base64)
```

### Step 5: Get ID Token

```bash
AUTH_RESPONSE=$(aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id $CLIENT_ID \
  --auth-parameters USERNAME=$USERNAME,PASSWORD=$PASSWORD,SECRET_HASH=$SECRET_HASH \
  --region $REGION \
  --output json)

ID_TOKEN=$(echo "$AUTH_RESPONSE" | jq -r '.AuthenticationResult.IdToken')
```

### Step 6: Call Gateway

```bash
curl -X POST "$GATEWAY_URL" \
  -H "Authorization: Bearer $ID_TOKEN" \
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

## Expected Responses

### Success Response

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
  "id": 0,
  "error": {
    "code": -32001,
    "message": "Invalid Bearer token"
  }
}
```

---

## Token Information

### ID Token (What Gateway Expects)

- **Type:** JWT
- **Audience:** Client ID
- **Issuer:** Cognito User Pool
- **Contains:** User information (email, sub, etc.)
- **Use for:** Gateway authentication ✅

### Access Token (OAuth2)

- **Type:** JWT
- **Audience:** Resource server (spark-api)
- **Issuer:** Cognito User Pool
- **Contains:** Scopes and permissions
- **Use for:** Service-to-service API calls

### Refresh Token

- **Type:** Opaque string
- **Use for:** Getting new ID/Access tokens when they expire

---

## Quick Reference

### Get Token
```bash
./get-user-token.sh
```

### Ask Question
```bash
./ask-gateway.sh "your question"
```

### Full Test
```bash
./test-complete-stack.sh
```

### View Logs
```bash
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

aws logs tail /aws/bedrock-agentcore/gateways/$GATEWAY_ID --follow
```

---

## Summary

**Simplest test:**
```bash
cd scripts
./ask-gateway.sh "what is 5+5"
```

**Get detailed token info:**
```bash
./get-user-token.sh
```

**Test everything:**
```bash
./test-complete-stack.sh
```

---

## Next Steps

1. ✅ Test basic functionality
2. ✅ Configure MCP client (Claude Desktop, etc.)
3. ✅ Add Gateway Targets for more tools
4. ✅ Integrate with your applications

---

**Ready to test?** Run:

```bash
cd scripts
./ask-gateway.sh "what is 5+5"
```

🎉 Happy testing!
