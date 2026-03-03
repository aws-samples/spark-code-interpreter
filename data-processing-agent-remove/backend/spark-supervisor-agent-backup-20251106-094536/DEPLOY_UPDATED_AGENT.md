# Deploy Updated Spark Supervisor Agent

## Quick Deployment

```bash
# 1. Activate bedrock-sdk conda environment
conda activate bedrock-sdk

# 2. Navigate to spark-supervisor-agent directory
cd /Users/nmurich/strands-agents/agent-core/data-processing-agent/backend/spark-supervisor-agent

# 3. Deploy the agent
python agent_deployment.py
```

## What Changed

The `execute_spark_code` tool has been split into two separate tools:
- `execute_spark_code_lambda` - For Lambda execution
- `execute_spark_code_emr` - For EMR Serverless execution

## Verification

After deployment, verify the agent is working:

```bash
# Check agent status
python get_arn.py
```

Expected output should show:
- Agent ARN
- Status: READY
- Two new tools: execute_spark_code_lambda, execute_spark_code_emr

## Testing

Test the updated agent with a simple request:

```python
import boto3
import json

bedrock_runtime = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

# Test Lambda execution
payload = {
    "prompt": "Generate sample data and analyze it",
    "execution_platform": "lambda",
    "s3_output_path": "s3://your-bucket/output/test/",
    "session_id": "test-session-123",
    "config": {
        "bedrock_region": "us-east-1",
        "s3_bucket": "your-bucket",
        "lambda_function": "your-lambda-function",
        "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    }
}

response = bedrock_runtime.invoke_agent_runtime(
    agentRuntimeArn='arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR',
    runtimeSessionId='test-session-123',
    payload=json.dumps(payload)
)

print(response['response'].read().decode('utf-8'))
```

## Rollback

If you need to rollback to the previous version:

```bash
# 1. Restore the old spark_supervisor_agent.py from git
git checkout HEAD~1 backend/spark-supervisor-agent/spark_supervisor_agent.py

# 2. Redeploy
python agent_deployment.py
```

## No Backend Changes Required

The backend (`backend/main.py`) does not need any changes because:
- It already passes `execution_platform` parameter
- The agent internally routes to the correct execution tool
- Response format remains unchanged

## Monitoring

Monitor the agent execution in CloudWatch:

```bash
# Tail agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --follow \
  --region us-east-1
```

Look for log messages indicating which execution tool was called:
- "Using execution platform: lambda" → calls execute_spark_code_lambda
- "Using execution platform: emr" → calls execute_spark_code_emr
