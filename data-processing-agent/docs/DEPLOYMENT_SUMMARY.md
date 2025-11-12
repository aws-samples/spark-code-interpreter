# Spark Supervisor Agent Deployment Summary

## Deployment Details

### Agent Information
- **Agent Name**: `spark_supervisor_agent`
- **Agent ID**: `spark_supervisor_agent-EZPQeDGCjR`
- **Agent ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR`
- **Region**: `us-east-1`
- **Account**: `260005718447`
- **Status**: `READY`

### Deployment Method
- **Tool**: Bedrock AgentCore Starter Toolkit
- **Build Method**: CodeBuild (ARM64)
- **Conda Environment**: `bedrock-sdk`
- **Deployment Time**: ~35 seconds

### Resources Created
1. **ECR Repository**: `260005718447.dkr.ecr.us-east-1.amazonaws.com/bedrock-agentcore-spark_supervisor_agent`
2. **Execution Role**: `arn:aws:iam::260005718447:role/AmazonBedrockAgentCoreSDKRuntime-us-east-1-976e96fdb5`
3. **CodeBuild Project**: `bedrock-agentcore-spark_supervisor_agent-builder`
4. **Memory Resource**: `spark_supervisor_agent_mem-B91TKC4fb6` (STM_ONLY)

### Configuration Files
- **Entrypoint**: `spark_supervisor_agent.py`
- **Requirements**: `requirements.txt` (strands-agents, boto3, pandas)
- **Config**: `.bedrock_agentcore.yaml`
- **Dockerfile**: Auto-generated

## Backend Integration

### Updated Files
- `backend/main.py`: Added `SPARK_SUPERVISOR_ARN` constant

### Configuration
```python
SPARK_SUPERVISOR_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR'
```

## Monitoring & Logs

### CloudWatch Logs
```bash
# Tail logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --log-stream-name-prefix "2025/10/15/[runtime-logs]" --follow

# View recent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --log-stream-name-prefix "2025/10/15/[runtime-logs]" --since 1h
```

### Observability Dashboard
https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#gen-ai-observability/agent-core

### Features Enabled
- ✅ CloudWatch Logs
- ✅ X-Ray Tracing
- ✅ Transaction Search
- ✅ GenAI Observability Dashboard

## Agent Capabilities

### Tools Available
1. **validate_spark_code**: Validates Spark code for S3 or Glue workflows
2. **execute_spark_code**: Executes on Lambda or EMR Serverless
3. **fetch_spark_results**: Retrieves results from S3

### Validation Logic
- **S3 Workflow**: Checks `spark.read`, S3 paths, output writes
- **Glue Workflow**: Checks `spark.table()`, Hive support, catalog access

### Execution Platforms
- **Lambda**: For files ≤500MB
- **EMR Serverless**: For files >500MB

## Testing

### Test Deployment
```bash
cd backend/spark-supervisor-agent
/Users/nmurich/opt/anaconda3/envs/bedrock-sdk/bin/python get_arn.py
```

### Test Agent Invocation
```python
import boto3
import json

bedrock_runtime = boto3.client('bedrock-agentcore-runtime', region_name='us-east-1')

payload = {
    "spark_code": "from pyspark.sql import SparkSession...",
    "s3_input_path": "s3://bucket/data.csv",
    "execution_platform": "lambda"
}

response = bedrock_runtime.invoke_agent(
    agentId='spark_supervisor_agent-EZPQeDGCjR',
    sessionId='test-session',
    inputText=json.dumps(payload)
)
```

## Next Steps

1. ✅ Deploy Spark supervisor agent - **COMPLETED**
2. ✅ Update backend configuration - **COMPLETED**
3. ⏳ Test Spark endpoints
4. ⏳ Frontend integration (add framework selector)
5. ⏳ End-to-end testing

## Rollback Instructions

### Undeploy Agent
```bash
cd backend/spark-supervisor-agent
/Users/nmurich/opt/anaconda3/envs/bedrock-sdk/bin/python -c "
from bedrock_agentcore_starter_toolkit import Runtime
runtime = Runtime()
runtime.configure(
    entrypoint='spark_supervisor_agent.py',
    agent_name='spark_supervisor_agent',
    region='us-east-1'
)
runtime.delete()
"
```

### Revert Backend Changes
```python
# In backend/main.py, change:
SPARK_SUPERVISOR_ARN = ''  # or remove the line
```

## Cost Considerations

### Resources
- **AgentCore Runtime**: Pay per invocation
- **CodeBuild**: ~$0.005 per build minute (ARM64)
- **ECR Storage**: ~$0.10 per GB/month
- **CloudWatch Logs**: ~$0.50 per GB ingested

### Estimated Monthly Cost
- Light usage (<1000 invocations): ~$5-10
- Medium usage (1000-10000 invocations): ~$20-50
- Heavy usage (>10000 invocations): ~$100+

## Support & Troubleshooting

### Common Issues

**Issue**: Agent not responding
```bash
# Check agent status
aws bedrock-agentcore get-runtime \
  --runtime-id spark_supervisor_agent-EZPQeDGCjR \
  --region us-east-1
```

**Issue**: Validation errors
```bash
# Check CloudWatch logs for validation details
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --since 1h
```

**Issue**: Execution failures
```bash
# Check Lambda logs (for Spark execution)
aws logs tail /aws/lambda/sparkOnLambda-spark-code-interpreter --since 1h

# Check EMR logs (for Spark execution)
aws emr-serverless get-job-run \
  --application-id 00fv6g7rptsov009 \
  --job-run-id <job-run-id>
```

## References

- [Bedrock AgentCore Documentation](https://docs.aws.amazon.com/bedrock/latest/userguide/agents-agentcore.html)
- [Strands Agents Documentation](https://github.com/aws-samples/strands-agents)
- [Ray Code Interpreter](../backend/README.md)
- [Unified Architecture](../backend/UNIFIED_ARCHITECTURE.md)
