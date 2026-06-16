# Fix for "Unknown tool: invoke_agent" Error

## The Error

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32602,
    "message": "Unknown tool: invoke_agent"
  }
}
```

## What This Means

✅ **Good news:** Authentication is working!  
❌ **Issue:** The Gateway has no tools configured

The Gateway is deployed and accepting authenticated requests, but it doesn't have any **Gateway Targets** configured yet. Gateway Targets are what expose tools through the MCP protocol.

---

## Solution Options

### Option 1: List Available Tools (Recommended First Step)

```bash
cd scripts
./list-gateway-tools.sh
```

This will show you what tools (if any) are currently available in the Gateway.

### Option 2: Invoke Agent Directly (Bypass Gateway)

Since the Gateway doesn't have tools yet, you can invoke the Spark Supervisor Agent directly:

```bash
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

This bypasses the Gateway and calls the agent directly via the Bedrock AgentCore Runtime API.

### Option 3: Add Gateway Targets

You need to configure Gateway Targets to expose tools through the Gateway.

---

## Understanding the Architecture

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ MCP Request
       │ (tools/call)
       ▼
┌─────────────┐
│   Gateway   │ ◄── You are here (Gateway exists but no targets)
└──────┬──────┘
       │
       │ No targets configured!
       │
       ▼
┌─────────────┐
│   Targets   │ ◄── Need to add these
│  (Tools)    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Agent     │
│  Runtime    │
└─────────────┘
```

---

## How to Add Gateway Targets

### Method 1: AWS Console (Easiest)

1. Go to AWS Console → Bedrock → AgentCore → Gateways
2. Select your gateway
3. Click "Add target"
4. Configure the target (Lambda, API, or MCP Server)

### Method 2: AWS CLI

```bash
# Get Gateway ID
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

# Create a Gateway Target (example for Lambda)
aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --name spark-executor \
  --description "Execute Spark code" \
  --target-configuration '{
    "mcp": {
      "lambda": {
        "lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:spark-lambda",
        "toolSchema": {
          "inlinePayload": "{\"tools\":[{\"name\":\"execute_spark\",\"description\":\"Execute Spark code\"}]}"
        }
      }
    }
  }' \
  --credential-provider-configurations '[{
    "type": "NONE"
  }]' \
  --region us-east-1
```

### Method 3: CloudFormation (Update Template)

We removed the Gateway Target from the CloudFormation template earlier because of schema issues. You can add it back once we figure out the correct schema, or add it manually via Console/CLI.

---

## Current Workaround: Invoke Agent Directly

While the Gateway doesn't have targets configured, you can still use the Spark Supervisor Agent directly:

### Quick Test:

```bash
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

### Custom Prompts:

```bash
./invoke-agent-directly.sh "create a dataframe with 10 rows"
./invoke-agent-directly.sh "generate sample sales data"
./invoke-agent-directly.sh "calculate 100 * 25"
```

---

## What Each Script Does

| Script | Purpose | Needs Gateway Targets? |
|--------|---------|----------------------|
| `list-gateway-tools.sh` | List available tools | No |
| `invoke-agent-directly.sh` | Call agent directly | No ✅ |
| `ask-gateway.sh` | Call via Gateway | Yes ❌ |
| `test-with-user-token.sh` | Test Gateway MCP | Yes ❌ |

---

## Checking Gateway Status

```bash
# List tools
./list-gateway-tools.sh

# Check Gateway info
GATEWAY_ID=$(aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --region us-east-1 \
  --query 'Stacks[0].Outputs[?OutputKey==`AgentCoreGatewayId`].OutputValue' \
  --output text)

aws bedrock-agentcore-control get-gateway \
  --gateway-identifier $GATEWAY_ID \
  --region us-east-1

# List targets
aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region us-east-1
```

---

## Why Gateway Targets Are Missing

We removed the Gateway Target from the CloudFormation template because the schema was complex and causing deployment failures. The Gateway itself deployed successfully, but without targets, it has no tools to expose.

### What Was Removed:

```yaml
# This was removed from CloudFormation:
SparkLambdaGatewayTarget:
  Type: AWS::BedrockAgentCore::GatewayTarget
  Properties:
    GatewayIdentifier: !Ref SparkAgentCoreGateway
    Name: spark-lambda-executor
    # ... complex configuration
```

---

## Next Steps

### Immediate: Use Direct Invocation

```bash
cd scripts
./invoke-agent-directly.sh "your question"
```

### Short-term: Add Gateway Target Manually

1. Use AWS Console to add a Gateway Target
2. Or use AWS CLI with correct schema
3. Then use `./ask-gateway.sh` to test

### Long-term: Update CloudFormation

Once we figure out the correct Gateway Target schema, we can add it back to the CloudFormation template for automated deployment.

---

## Testing Right Now

### What Works:

✅ Gateway is deployed  
✅ Authentication works (Cognito JWT)  
✅ MCP protocol works  
✅ Agent can be invoked directly  

### What Doesn't Work:

❌ Gateway has no tools (no targets configured)  
❌ Can't call tools via Gateway  

### Solution:

```bash
# Use direct invocation for now:
cd scripts
./invoke-agent-directly.sh "what is 5+5"
```

---

## Summary

**Error:** "Unknown tool: invoke_agent"  
**Cause:** Gateway has no Gateway Targets configured  
**Quick Fix:** Use `./invoke-agent-directly.sh` to bypass Gateway  
**Proper Fix:** Add Gateway Targets via Console or CLI  

---

**Test now:**

```bash
cd scripts

# Check what tools are available
./list-gateway-tools.sh

# Invoke agent directly (works without Gateway)
./invoke-agent-directly.sh "what is 5+5"
```

This will work! 🎉
