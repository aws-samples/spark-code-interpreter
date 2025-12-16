# Unified Backend Architecture - Ray & Spark Code Interpreters

## Overview

This backend supports both Ray and Spark code generation, validation, and execution through a unified FastAPI interface with framework-specific supervisor agents.

## Architecture

```
┌─────────────┐
│  Frontend   │
│ (Framework  │
│  Selector)  │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────┐
│         FastAPI Backend (main.py)        │
│  - Framework routing                     │
│  - Session management                    │
│  - S3/Glue data source handling          │
└──────┬──────────────────────┬───────────┘
       │                      │
       v                      v
┌──────────────┐      ┌──────────────┐
│ Ray Workflow │      │Spark Workflow│
└──────┬───────┘      └──────┬───────┘
       │                     │
       v                     v
┌──────────────┐      ┌──────────────┐
│Ray Supervisor│      │Spark Supervisor│
│   Agent      │      │    Agent      │
│ (AgentCore)  │      │  (AgentCore)  │
└──────┬───────┘      └──────┬────────┘
       │                     │
       └──────────┬──────────┘
                  v
         ┌────────────────┐
         │ Code Generation│
         │     Agent      │
         │  (Shared)      │
         └────────────────┘
```

## Components

### 1. Shared Code Generation Agent
- **Location**: `backend/code-generation-agent/`
- **Purpose**: Generates code for both Ray and Spark
- **Input**: Prompt + framework-specific system prompt
- **Output**: Generated code (Ray or Spark)
- **Reusability**: Single agent serves both frameworks

### 2. Ray Supervisor Agent
- **Location**: `backend/supervisor-agent/`
- **Purpose**: Validates and executes Ray code
- **Tools**:
  - `validate_ray_code`: Syntax and safety checks
  - `execute_ray_code`: Runs on Ray cluster via MCP Gateway
  - `fetch_ray_results`: Retrieves execution results
- **Validation**: Ray-specific (imports, cluster connection, etc.)

### 3. Spark Supervisor Agent
- **Location**: `backend/spark-supervisor-agent/`
- **Purpose**: Validates and executes Spark code
- **Tools**:
  - `validate_spark_code`: Spark-specific validation
    - S3 workflow: Checks spark.read, S3 paths
    - Glue workflow: Checks spark.table(), Hive support
  - `execute_spark_code`: Runs on Lambda or EMR Serverless
  - `fetch_spark_results`: Retrieves results from S3
- **Validation**: Framework-specific (Glue vs S3, platform selection)

### 4. FastAPI Backend
- **Location**: `backend/main.py`
- **Purpose**: Unified API with framework routing
- **Endpoints**:
  - `/generate` - Ray code generation
  - `/execute` - Ray code execution
  - `/spark/generate` - Spark code generation
  - `/spark/validate-execute` - Spark validation & execution
  - `/upload-csv` - CSV upload (shared)
  - `/glue/*` - Glue catalog access (shared)

## Workflow Comparison

### Ray Workflow
1. Frontend sends prompt with `framework: "ray"`
2. Backend calls Ray Supervisor Agent
3. Supervisor delegates to Code Generation Agent with Ray system prompt
4. Generated code validated for Ray (imports, cluster refs)
5. Executed on Ray cluster via MCP Gateway
6. Results fetched and returned

### Spark Workflow
1. Frontend sends prompt with `framework: "spark"` + data source
2. Backend calls Spark Supervisor Agent
3. Supervisor delegates to Code Generation Agent with Spark system prompt
4. Generated code validated for Spark:
   - S3: `spark.read`, S3 paths
   - Glue: `spark.table()`, Hive support
5. Executed on Lambda (small) or EMR (large)
6. Results fetched from S3 and returned

## Code Reusability

### Shared Components
- ✅ Code Generation Agent (single deployment)
- ✅ CSV upload logic
- ✅ Glue catalog integration
- ✅ S3 operations
- ✅ Session management

### Framework-Specific Components
- Ray Supervisor: Ray validation + MCP Gateway execution
- Spark Supervisor: Spark validation + Lambda/EMR execution

## Validation Logic

### Ray Validation
```python
- Check Ray imports (ray.init, @ray.remote)
- Verify cluster connection code
- Ensure proper Ray patterns
- No Spark-specific code
```

### Spark Validation (S3)
```python
- Check spark.read usage
- Verify S3 path in code
- Ensure output write to S3
- SparkSession creation
```

### Spark Validation (Glue)
```python
- Check spark.table() usage
- Verify Hive support enabled
- Ensure Glue table references
- Proper catalog access
```

## Deployment

### Deploy Spark Supervisor Agent
```bash
cd backend/spark-supervisor-agent
./deploy.sh
```

### Update Backend Configuration
```bash
# In backend/main.py, update:
SPARK_SUPERVISOR_ARN = 'arn:aws:bedrock-agentcore:...'
```

### Environment Variables
```bash
# Spark Configuration
export SPARK_S3_BUCKET=spark-data-260005718447-us-east-1
export SPARK_LAMBDA=sparkOnLambda-spark-code-interpreter
export SPARK_EMR_APP=00fv6g7rptsov009
export SPARK_SUPERVISOR_ARN=arn:aws:bedrock-agentcore:...

# Ray Configuration (existing)
export RAY_PRIVATE_IP=...
export RAY_PUBLIC_IP=...
```

## API Usage

### Generate Ray Code
```bash
POST /generate
{
  "prompt": "Calculate sum of numbers 1-100",
  "session_id": "session-123",
  "framework": "ray"
}
```

### Generate Spark Code (S3)
```bash
POST /spark/generate
{
  "prompt": "Analyze sales data",
  "session_id": "session-123",
  "framework": "spark",
  "s3_input_path": "s3://bucket/data.csv",
  "execution_platform": "lambda"
}
```

### Generate Spark Code (Glue)
```bash
POST /spark/generate
{
  "prompt": "Join customer and orders tables",
  "session_id": "session-123",
  "framework": "spark",
  "selected_tables": ["db.customers", "db.orders"],
  "execution_platform": "emr"
}
```

## Benefits

1. **Maximum Code Reuse**: Single code generation agent
2. **Clear Separation**: Framework-specific validation isolated
3. **Scalable**: Easy to add new frameworks
4. **Maintainable**: Each supervisor owns its validation logic
5. **Flexible**: Frontend controls framework selection

## Next Steps

1. Deploy Spark Supervisor Agent
2. Update frontend to include framework selector
3. Test both workflows end-to-end
4. Add monitoring and logging
