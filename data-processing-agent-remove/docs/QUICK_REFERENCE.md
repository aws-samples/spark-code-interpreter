# Quick Reference - Unified Ray & Spark Backend

## File Structure

```
backend/
├── main.py                          # Unified FastAPI backend
├── config.py                        # Configuration management
├── spark_supervisor_agent.py        # Spark supervisor (standalone)
│
├── code-generation-agent/           # Shared code gen agent
│   ├── agents.py
│   ├── .bedrock_agentcore.yaml
│   └── requirements.txt
│
├── supervisor-agent/                # Ray supervisor agent
│   ├── supervisor_agents.py
│   ├── .bedrock_agentcore.yaml
│   └── requirements.txt
│
└── spark-supervisor-agent/          # Spark supervisor agent
    ├── spark_supervisor_agent.py
    ├── .bedrock_agentcore.yaml
    ├── requirements.txt
    ├── Dockerfile
    └── deploy.sh
```

## Key Endpoints

### Ray Endpoints (Existing)
- `POST /generate` - Generate Ray code
- `POST /execute` - Execute Ray code
- `GET /ray/status` - Ray cluster status
- `GET /ray/jobs` - List Ray jobs

### Spark Endpoints (New)
- `POST /spark/generate` - Generate Spark code
- `POST /spark/validate-execute` - Validate & execute Spark
- `GET /spark/config` - Get Spark configuration

### Shared Endpoints
- `POST /upload-csv` - Upload CSV to S3
- `GET /glue/databases` - List Glue databases
- `GET /glue/tables/{db}` - List tables in database
- `POST /glue/select-tables` - Select tables for query
- `GET /settings` - Get settings
- `POST /settings` - Update settings

## Agent Responsibilities

### Code Generation Agent (Shared)
- **Input**: Prompt + system prompt (Ray or Spark)
- **Output**: Generated code
- **Used By**: Both Ray and Spark supervisors

### Ray Supervisor Agent
- **Validates**: Ray imports, cluster patterns, @ray.remote
- **Executes**: Via MCP Gateway to Ray cluster
- **Returns**: Execution results

### Spark Supervisor Agent
- **Validates**: 
  - S3: spark.read, S3 paths
  - Glue: spark.table(), Hive support
- **Executes**: Lambda (small) or EMR (large)
- **Returns**: Results from S3

## Validation Rules

### Ray Validation
```python
✓ Has Ray imports (ray.init, @ray.remote)
✓ Proper Ray patterns
✓ Cluster connection code
✗ No Spark-specific code
```

### Spark Validation - S3
```python
✓ Has spark.read
✓ S3 path in code
✓ Output write to S3
✓ SparkSession creation
✗ No Ray-specific code
```

### Spark Validation - Glue
```python
✓ Has spark.table()
✓ Hive support enabled
✓ Glue table references
✓ Catalog access
✗ No spark.read for Glue tables
```

## Deployment Commands

### Deploy Spark Supervisor
```bash
cd backend/spark-supervisor-agent
./deploy.sh
# Copy ARN from output
```

### Update Backend Config
```bash
# Edit backend/main.py
SPARK_SUPERVISOR_ARN = 'arn:aws:bedrock-agentcore:...'
```

### Restart Backend
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

## Environment Variables

```bash
# Spark
export SPARK_S3_BUCKET=spark-data-260005718447-us-east-1
export SPARK_LAMBDA=sparkOnLambda-spark-code-interpreter
export SPARK_EMR_APP=00fv6g7rptsov009
export SPARK_SUPERVISOR_ARN=<from-deployment>

# Ray (existing)
export RAY_PRIVATE_IP=<existing>
export RAY_PUBLIC_IP=<existing>
```

## Testing

### Test Ray (Existing)
```bash
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Calculate first 10 primes", "session_id": "test"}'
```

### Test Spark - S3
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze sales data",
    "session_id": "test",
    "s3_input_path": "s3://bucket/data.csv",
    "execution_platform": "lambda"
  }'
```

### Test Spark - Glue
```bash
curl -X POST http://localhost:8000/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Join customers and orders",
    "session_id": "test",
    "selected_tables": ["db.customers", "db.orders"],
    "execution_platform": "emr"
  }'
```

## Troubleshooting

### Spark Supervisor Not Found
```bash
# Check ARN is set
echo $SPARK_SUPERVISOR_ARN

# Verify deployment
bedrock-agentcore list
```

### Validation Fails
```bash
# Check logs
tail -f backend.log

# Verify code generation
# Look for validation_errors in response
```

### Execution Fails
```bash
# Check Lambda logs (for Spark)
aws logs tail /aws/lambda/sparkOnLambda-spark-code-interpreter

# Check EMR logs (for Spark)
aws emr-serverless get-job-run --application-id $SPARK_EMR_APP --job-run-id <id>

# Check Ray logs (for Ray)
# Access Ray dashboard at http://<RAY_PUBLIC_IP>:8265
```

## Code Patterns

### Ray Code Pattern
```python
import ray

@ray.remote
def my_function(x):
    return x * 2

ray.init()
results = ray.get([my_function.remote(i) for i in range(10)])
print(results)
```

### Spark Code Pattern - S3
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Analysis").getOrCreate()
df = spark.read.option("header", "true").csv("s3://bucket/data.csv")
result = df.groupBy("column").count()
result.write.mode("overwrite").csv("s3://bucket/output")
```

### Spark Code Pattern - Glue
```python
from pyspark.sql import SparkSession

spark = SparkSession.builder.enableHiveSupport().getOrCreate()
df = spark.table("database.table")
result = df.filter(df.column > 100)
result.write.mode("overwrite").csv("s3://bucket/output")
```
