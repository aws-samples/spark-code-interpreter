# Deploy Spark Supervisor Agent - Quick Instructions

## Issue
The `bedrock-agentcore` CLI is not working. Use the Python deployment script instead.

## Solution: Use Python Deployment Script

### From Project Root

```bash
# Deploy Spark Supervisor Agent
./scripts/deploy-spark-supervisor-agent.sh
```

### Or Manually

```bash
cd agent-code/spark-supervisor-agent
python3 agent_deployment.py
```

## What This Does

1. Configures the agent with updated code (including new model_id default)
2. Creates/updates Docker image
3. Deploys to Bedrock AgentCore
4. Saves the agent ARN to `config/deployment-config.json`

## Prerequisites

Make sure you have the toolkit installed:

```bash
pip3 install bedrock-agentcore-starter-toolkit
```

## After Agent Deployment

Deploy the wrapper Lambda:

```bash
./scripts/deploy-agent-wrapper.sh
```

Or manually:

```bash
cd agent-wrapper
zip agent_wrapper.zip agent_wrapper.py

aws lambda update-function-code \
  --function-name dev-spark-agent-wrapper \
  --zip-file fileb://agent_wrapper.zip \
  --region us-east-1
```

## Test

```bash
./scripts/test-calculation.sh "what is 7*10"
```

Or via AWS Console:
- Lambda: `dev-spark-agent-wrapper`
- Payload: `{"prompt":"what is 7*10"}`

## Full Deployment Sequence

```bash
# 1. Deploy Spark Supervisor Agent
cd agent-code/spark-supervisor-agent
python3 agent_deployment.py

# 2. Deploy Wrapper Lambda
cd ../../
zip -j /tmp/wrapper.zip agent-wrapper/agent_wrapper.py
aws lambda update-function-code \
  --function-name dev-spark-agent-wrapper \
  --zip-file fileb:///tmp/wrapper.zip \
  --region us-east-1

# 3. Test
./scripts/test-calculation.sh "what is 7*10"
```

## Expected Output

After deployment, you should see:
```
✅ Spark Supervisor Agent deployed successfully!
ARN: arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/spark_supervisor_agent-XXXXX
✅ Updated config with Spark supervisor ARN
```

## Troubleshooting

### Error: ModuleNotFoundError: No module named 'bedrock_agentcore_starter_toolkit'

Install the toolkit:
```bash
pip3 install bedrock-agentcore-starter-toolkit
```

### Error: ExpiredTokenException

Refresh your AWS credentials.

### Error: AccessDeniedException

Make sure you have permissions for:
- `bedrock-agentcore:*`
- `ecr:*`
- `iam:CreateRole` (if auto-creating execution role)

## What Changed

The agent code now includes a default model_id:

```python
# Before
if not model_id:
    raise ValueError("❌ ERROR: No model_id found...")

# After  
if not model_id:
    model_id = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
    print(f"ℹ️  No model_id provided, using default: {model_id}")
```

This means the agent will work even if the wrapper Lambda doesn't pass a model_id.

## Summary

**Don't use**: `bedrock-agentcore deploy` (CLI broken)

**Use instead**: `python3 agent_deployment.py` (Python script works)

---

**Quick Command**:
```bash
cd agent-code/spark-supervisor-agent && python3 agent_deployment.py
```
