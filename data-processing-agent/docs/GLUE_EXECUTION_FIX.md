# Glue Table Execution Fix - Retry Logic and Configuration

## Issues Fixed

### 1. No Retry Logic on Execution Failures
**Problem**: Supervisor agent executed code once and returned, even if execution failed
- Static validation (`validate_spark_code`) only checked for string patterns
- Didn't detect runtime errors like Derby metastore failures
- No iteration to regenerate code with error feedback

**Fix**: Updated supervisor system prompt to include retry logic:
- Up to 5 attempts to generate and execute code
- On execution failure: Extract error logs and regenerate with error context
- Example: "Previous code failed with: {error}. Fix the issue and regenerate code."
- Continues until success or max attempts reached

### 2. Missing Glue Catalog Configuration
**Problem**: Generated code used `enableHiveSupport()` without proper Glue catalog configuration
- Lambda tried to create Derby metastore at `/var/task/metastore_db` (read-only)
- Error: `Directory /var/task/metastore_db cannot be created`
- Missing warehouse.dir and Glue catalog factory class settings

**Fix**: Updated code generation system prompt with critical Glue configuration:
```python
spark = SparkSession.builder \
    .appName("GlueQuery") \
    .config("spark.sql.warehouse.dir", "s3://bucket/warehouse/") \
    .config("spark.hadoop.hive.metastore.warehouse.dir", "s3://bucket/warehouse/") \
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \
    .enableHiveSupport() \
    .getOrCreate()
```

### 3. Missing S3 Bucket Context
**Problem**: Code generation didn't know which S3 bucket to use for warehouse configuration

**Fix**: 
- Added `s3_output_path` parameter to `call_code_generation_agent`
- Extract bucket from output path and pass to code generation
- Context includes: "S3 bucket for warehouse: s3://bucket/warehouse/"

## Changes Made

### File: `spark_supervisor_agent.py`

#### 1. Code Generation System Prompt
**Added**:
- Glue catalog configuration section with complete SparkSession setup
- Explicit instructions to include warehouse.dir and factory.class configs
- Note about preventing Derby metastore errors on Lambda

#### 2. Supervisor System Prompt
**Added**:
- Retry logic workflow (up to 5 attempts)
- Error analysis and feedback loop
- Specific error handling for Derby metastore, column names, permissions
- Instructions to regenerate code with error context on failures

#### 3. Code Generation Tool
**Modified**:
- Added `s3_output_path` parameter
- Extract S3 bucket from output path
- Pass warehouse bucket location in context for Glue tables

## How It Works Now

### Workflow with Retry Logic

```
Attempt 1:
  1. Fetch Glue table schema
  2. Generate code with Glue catalog config
  3. Validate code (static)
  4. Execute code
  5. Check execution status
  
If FAILED:
  6. Extract execution logs and error
  7. Analyze error (e.g., "Derby metastore error")
  8. Go to Attempt 2 with error feedback

Attempt 2:
  1. Generate code with error context
     Prompt: "Previous code failed with Derby metastore error. 
              Ensure Glue catalog configuration is included."
  2. Validate code
  3. Execute code
  4. Check execution status
  
If SUCCESS or max attempts (5):
  5. Extract logs
  6. Fetch results from S3
  7. Return final response
```

### Generated Code Pattern (Glue Tables)

**Before** (Failed):
```python
spark = SparkSession.builder \
    .appName("Query") \
    .enableHiveSupport() \
    .getOrCreate()
# ❌ Tries to create Derby metastore, fails on Lambda
```

**After** (Works):
```python
spark = SparkSession.builder \
    .appName("GlueQuery") \
    .config("spark.sql.warehouse.dir", "s3://spark-data-260005718447-us-east-1/warehouse/") \
    .config("spark.hadoop.hive.metastore.warehouse.dir", "s3://spark-data-260005718447-us-east-1/warehouse/") \
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \
    .enableHiveSupport() \
    .getOrCreate()
# ✅ Uses Glue catalog, no Derby metastore needed
```

## Testing

### Test Case 1: Glue Table Query (Lambda)
```python
payload = {
    "prompt": "Find top 10 transactions by closing price from nasdaq table",
    "selected_tables": [{"database": "northwind", "table": "nasdaq"}],
    "execution_engine": "lambda"
}
```

**Expected**:
- Attempt 1: May fail with Derby error
- Attempt 2: Regenerates with Glue catalog config
- Result: Success with data in actual_results

### Test Case 2: Glue Table Query (EMR)
```python
payload = {
    "prompt": "Analyze sales by category from orders table",
    "selected_tables": [{"database": "northwind", "table": "orders"}],
    "execution_engine": "emr"
}
```

**Expected**:
- Generates code with Glue catalog config
- Executes successfully on EMR
- Returns formatted results

### Test Case 3: CSV File (No Regression)
```python
payload = {
    "prompt": "Analyze uploaded CSV file",
    "s3_input_path": "s3://bucket/data.csv",
    "execution_engine": "lambda"
}
```

**Expected**:
- Uses spark.read.csv() (no Glue config)
- Works as before
- No regression in CSV functionality

## Key Points

1. **Retry Logic**: Agent now iterates up to 5 times on execution failures
2. **Error Feedback**: Execution errors are passed back to code generation
3. **Glue Configuration**: Proper warehouse.dir and factory.class settings included
4. **No Regression**: CSV and Ray code generation unaffected
5. **Platform Agnostic**: Works on both Lambda and EMR

## Files Modified

- `backend/spark-supervisor-agent/spark_supervisor_agent.py`
  - Updated code generation system prompt (Glue config)
  - Updated supervisor system prompt (retry logic)
  - Modified `call_code_generation_agent` (S3 bucket context)

## Deployment

```bash
cd backend/spark-supervisor-agent
source ~/.bash_profile
conda activate bedrock-sdk
./deploy.sh
```

## Status

✅ Retry logic added to supervisor agent
✅ Glue catalog configuration in code generation prompt
✅ S3 bucket context passed for warehouse configuration
✅ No changes to CSV or Ray code generation
✅ Deployed to AgentCore runtime
