# Quick Start - Spark Integration

## ✅ Deployment Complete

**Spark Supervisor Agent ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR`

## Start Backend

```bash
cd /Users/nmurich/strands-agents/agent-core/data-processing-agent/backend
python -m uvicorn main:app --reload --port 8000
```

## Test Spark Endpoints

### Generate Spark Code (S3)
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Calculate average sales by region",
    "session_id": "test-123",
    "framework": "spark",
    "s3_input_path": "s3://spark-data-260005718447-us-east-1/sales.csv",
    "execution_platform": "lambda"
  }'
```

### Generate Spark Code (Glue)
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Join customers and orders tables",
    "session_id": "test-123",
    "framework": "spark",
    "selected_tables": ["northwind.customers", "northwind.orders"],
    "execution_platform": "emr"
  }'
```

### Validate & Execute
```bash
curl -X POST http://localhost:8000/spark/validate-execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "<generated-spark-code>",
    "session_id": "test-123",
    "s3_input_path": "s3://bucket/data.csv",
    "execution_platform": "lambda"
  }'
```

## Test Ray Endpoints (Existing)

### Generate Ray Code
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Calculate first 10 prime numbers",
    "session_id": "test-123"
  }'
```

## Monitor Logs

### Spark Supervisor
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --log-stream-name-prefix "2025/10/15/[runtime-logs]" --follow
```

### Ray Supervisor
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/supervisor_agent-caFwzSALky-DEFAULT \
  --log-stream-name-prefix "2025/10/15/[runtime-logs]" --follow
```

## Check Agent Status

```bash
# Spark
aws bedrock-agentcore get-runtime \
  --runtime-id spark_supervisor_agent-EZPQeDGCjR \
  --region us-east-1

# Ray
aws bedrock-agentcore get-runtime \
  --runtime-id supervisor_agent-caFwzSALky \
  --region us-east-1
```

## Redeploy Agent

```bash
cd backend/spark-supervisor-agent
/Users/nmurich/opt/anaconda3/envs/bedrock-sdk/bin/python agent_deployment.py
```

## API Endpoints

| Endpoint | Method | Framework | Purpose |
|----------|--------|-----------|---------|
| `/generate` | POST | Ray | Generate Ray code |
| `/execute` | POST | Ray | Execute Ray code |
| `/spark/generate` | POST | Spark | Generate Spark code |
| `/spark/validate-execute` | POST | Spark | Validate & execute Spark |
| `/upload-csv` | POST | Both | Upload CSV to S3 |
| `/glue/databases` | GET | Both | List Glue databases |
| `/glue/tables/{db}` | GET | Both | List tables |
| `/ray/status` | GET | Ray | Ray cluster status |

## Configuration

### Agent ARNs (in backend/main.py)
```python
SUPERVISOR_AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky'
SPARK_SUPERVISOR_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR'
```

### Environment Variables
```bash
# Spark
export SPARK_S3_BUCKET=spark-data-260005718447-us-east-1
export SPARK_LAMBDA=sparkOnLambda-spark-code-interpreter
export SPARK_EMR_APP=00fv6g7rptsov009

# Ray
export RAY_PRIVATE_IP=<ip>
export RAY_PUBLIC_IP=<ip>
```

## Troubleshooting

### Backend won't start
```bash
# Check Python version
python --version  # Should be 3.12+

# Install dependencies
pip install fastapi uvicorn boto3 requests
```

### Agent not responding
```bash
# Check agent status
aws bedrock-agentcore get-runtime --runtime-id spark_supervisor_agent-EZPQeDGCjR

# Check logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT --since 1h
```

### Validation fails
- Check CloudWatch logs for validation errors
- Verify S3 paths or Glue table names
- Ensure proper Spark syntax

## Next Steps

1. ✅ Backend deployed and configured
2. ⏳ Test Spark endpoints
3. ⏳ Add framework selector to frontend
4. ⏳ End-to-end testing

## Documentation

- `UNIFIED_ARCHITECTURE.md` - Complete architecture
- `DEPLOYMENT_SUMMARY.md` - Deployment details
- `SPARK_INTEGRATION_SUMMARY.md` - Integration guide
- `DEPLOYMENT_COMPLETE.md` - Completion status
