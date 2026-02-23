# Add Agent as Gateway Target

## What You Need

You want: **Natural Language → Gateway → Agent → Lambda**

Currently: **Gateway → Lambda directly** (requires PySpark code)

## Solution: Add Agent Target Instead of Lambda Target

### Step 1: Remove Current Lambda Target

1. Go to AWS Console:
   ```
   https://console.aws.amazon.com/bedrock/home?region=us-east-1#/agentcore/gateways
   ```

2. Click on gateway: `dev-spark-gateway-0y5eyw5mag`

3. Click "Targets" tab

4. Select the `spark-executor` target

5. Click "Delete" or "Remove"

### Step 2: Add Agent Target

1. Click "Add target" button

2. Fill in:

**Basic Information:**
```
Name: spark-agent
Description: Spark Supervisor Agent for natural language data processing
```

**Target Type:**
```
Agent (or Bedrock Agent)
```

**Agent Configuration:**
```
Agent ARN: arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu
```

**Credentials:**
```
None
```

3. Click "Add target"

4. Wait for status: `Creating` → `Available`

---

## Alternative: Add via CLI

If the Console doesn't have an "Agent" target type option, use the CLI:

```bash
GATEWAY_ID="dev-spark-gateway-0y5eyw5mag"
AGENT_ARN="arn:aws:bedrock-agentcore:us-east-1:817323390093:runtime/spark_supervisor_agent-kSQUxI8Tqu"

# Remove old Lambda target first
OLD_TARGET_ID=$(aws bedrock-agentcore-control list-gateway-targets \
  --gateway-identifier $GATEWAY_ID \
  --region us-east-1 \
  --query 'items[0].targetId' \
  --output text)

aws bedrock-agentcore-control delete-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --target-id $OLD_TARGET_ID \
  --region us-east-1

# Add Agent target
aws bedrock-agentcore-control create-gateway-target \
  --gateway-identifier $GATEWAY_ID \
  --name spark-agent \
  --description "Spark Supervisor Agent for natural language queries" \
  --target-configuration "{\"agent\":{\"agentArn\":\"$AGENT_ARN\"}}" \
  --credential-provider-configurations '[{"credentialProviderType":"NONE"}]' \
  --region us-east-1
```

---

## Expected Tool Schema

After adding the Agent target, the Gateway should expose:

```json
{
  "tools": [
    {
      "name": "spark-agent___invoke_agent",
      "description": "Invoke Spark Supervisor Agent with natural language",
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
}
```

---

## Test After Adding Agent Target

```bash
cd scripts
./list-gateway-tools.sh
```

You should see: `spark-agent___invoke_agent`

Then test:
```bash
./ask-gateway.sh "what is 5+5"
```

This will now send natural language to the agent!

---

## Why This Matters

### Lambda Target (Current):
```
External App → Gateway → Lambda
                         ↓
                    Requires PySpark code
```

### Agent Target (What You Want):
```
External App → Gateway → Agent → Lambda
                         ↓         ↓
                   Natural Lang  PySpark
```

The Agent handles the translation from natural language to PySpark code.

---

## Troubleshooting

### If Console doesn't show "Agent" as target type:

The Gateway Target API supports these types:
- `lambda` - Direct Lambda invocation
- `agent` - Bedrock Agent invocation  
- `mcpServer` - External MCP server
- `apiGateway` - API Gateway endpoint

If the Console UI doesn't expose the Agent option, use the CLI command above.

### If CLI command fails:

Check the exact schema with:
```bash
aws bedrock-agentcore-control create-gateway-target help
```

Look for the `agent` configuration structure in the documentation.

---

## Summary

1. **Remove** the current Lambda target (`spark-executor`)
2. **Add** an Agent target pointing to: `spark_supervisor_agent-kSQUxI8Tqu`
3. **Test** with natural language queries

This gives you the flow you want: Natural Language → Gateway → Agent → Lambda
