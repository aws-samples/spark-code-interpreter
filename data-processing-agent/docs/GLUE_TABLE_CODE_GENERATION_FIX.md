# Glue Table Code Generation Fix

## Issue
The code generation agent was generating incorrect Ray code for reading Glue tables. It was using `ray.data.read_sql()` with Athena connection strings instead of `ray.data.read_parquet()` with the S3 location.

## Root Cause
Both the supervisor agent and code generation agent had incorrect instructions in their system prompts:
- **Incorrect**: `ray.data.read_sql("SELECT * FROM database.table", connection_uri="awsathena://")`
- **Correct**: `ray.data.read_parquet("s3://bucket/path/")`

Glue tables store their data in S3 (typically as Parquet files), and Ray should read directly from the S3 location, not through SQL queries.

## Solution
Updated system prompts in both agents to use the correct Ray API for reading Glue tables.

### Files Changed

#### 1. supervisor-backend/supervisor_agents.py
**Changed**: Line ~145 in `call_code_generation_agent()` function

**Before**:
```python
- For Glue tables: ray.data.read_sql("SELECT * FROM database.table", connection_uri="awsathena://")
```

**After**:
```python
- For Glue tables: ray.data.read_parquet("s3://location-from-prompt")
```

**Full Pattern Before**:
```python
GLUE TABLE READING:
When prompt mentions Glue table "database.table":
```python
ds = ray.data.read_sql("SELECT * FROM database.table", connection_uri="awsathena://")
```
```

**Full Pattern After**:
```python
GLUE TABLE READING:
When prompt mentions Glue table "database.table at s3://bucket/path/":
```python
ds = ray.data.read_parquet("s3://bucket/path/")
```
```

#### 2. backend/agents.py
**Changed**: Line ~30 in `create_code_generation_agent()` function

**Before**:
```python
- ray.data.read_sql(sql, connection_uri) - Read from SQL query (use for Glue tables)
...
- For Glue tables: Use ray.data.read_sql() with SQL query like "SELECT * FROM database.table"
...
GLUE TABLE PATTERN:
For Glue table "database.table":
ds = ray.data.read_sql("SELECT * FROM database.table", connection_uri="awsathena://")
```

**After**:
```python
- ray.data.read_parquet(s3_path) - Read Parquet from S3 (use for Glue tables)
...
- For Glue tables: Use S3 location from "at s3://..." with ray.data.read_parquet()
...
GLUE TABLE PATTERN:
For Glue table "database.table at s3://bucket/path/":
ds = ray.data.read_parquet("s3://bucket/path/")
```

## How It Works

### Data Flow
1. **User selects Glue tables** in the UI
2. **Backend (main.py)** retrieves table metadata from AWS Glue:
   ```python
   {
       'database': 'northwind',
       'table': 'customers',
       'location': 's3://my-data-lake/northwind/customers/'
   }
   ```
3. **Backend formats prompt** with table information:
   ```
   Available Glue tables:
     - northwind.customers at s3://my-data-lake/northwind/customers/
     - northwind.orders at s3://my-data-lake/northwind/orders/
   ```
4. **Supervisor agent** passes this to code generation agent with system prompt
5. **Code generation agent** generates Ray code:
   ```python
   import ray
   ray.init()
   
   customers_ds = ray.data.read_parquet("s3://my-data-lake/northwind/customers/")
   orders_ds = ray.data.read_parquet("s3://my-data-lake/northwind/orders/")
   
   # Process data...
   print("Results:", results)
   ```

### Why read_parquet() Instead of read_sql()?
- Glue tables are metadata pointers to S3 data (usually Parquet format)
- Ray can read directly from S3 without SQL layer overhead
- Faster and more efficient for distributed processing
- No need for Athena connection or query execution

## Deployment

Both agents were redeployed with the fix:

### Code Generation Agent
```bash
cd supervisor-backend
conda run -n bedrock-sdk python agent_deployment.py
```
- **ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9`
- **Build**: CodeBuild completed in 40s
- **Status**: ✅ Deployed

### Supervisor Agent
```bash
cd backend
conda run -n bedrock-sdk python agent_deployment.py
```
- **ARN**: `arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky`
- **Build**: CodeBuild completed in 40s
- **Status**: ✅ Deployed

## Testing

### Manual Test
1. Start the backend: `./start.sh`
2. Open UI: http://localhost:5173
3. Select Glue tables from the left panel
4. Generate code with prompt: "Analyze the customer data"
5. Verify generated code uses `ray.data.read_parquet()` with correct S3 paths

### Expected Generated Code
```python
import ray
ray.init()

# Read from Glue table location
customers = ray.data.read_parquet("s3://my-data-lake/northwind/customers/")

# Process data
result = customers.take_all()
print("Customer count:", len(result))
print("Sample records:", result[:5])
```

## Verification Checklist
- [x] System prompts updated in both agents
- [x] Code generation agent deployed
- [x] Supervisor agent deployed
- [x] Backend correctly formats Glue table information
- [x] No changes to CSV file handling
- [x] No changes to execution flow
- [x] No direct Lambda calls (only through AgentCore Gateway)
- [x] No simulation code added

## Key Points
1. **CSV files** → `ray.data.read_csv("s3://path/to/file.csv")`
2. **Glue tables** → `ray.data.read_parquet("s3://path/to/table/")`
3. **Data sources** passed in prompt text (not via tool calls)
4. **Agent extracts** S3 paths from formatted prompt
5. **No breaking changes** to existing CSV functionality

## Related Files
- `/Users/nmurich/strands-agents/agent-core/ray-code-interpreter-agent/supervisor-backend/supervisor_agents.py`
- `/Users/nmurich/strands-agents/agent-core/ray-code-interpreter-agent/backend/agents.py`
- `/Users/nmurich/strands-agents/agent-core/ray-code-interpreter-agent/backend/main.py` (no changes needed)

## Reference Implementation
The working implementation from `/Users/nmurich/strands-agents/agent-core/ray-code-interpreter` was used as reference for the correct Glue table handling pattern.
