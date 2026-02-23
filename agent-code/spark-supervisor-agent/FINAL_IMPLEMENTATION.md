# Final Implementation - Spark Supervisor Agent

## Overview

Split `execute_spark_code` into two separate tools (`execute_spark_code_lambda` and `execute_spark_code_emr`) with minimal changes to preserve original working behavior.

## Two Flows

### 1. GENERATE Flow (Code Generation + Validation + Execution)
- Generates code
- Validates code
- **Executes for validation** (automatic platform selection)
- Returns validated code + execution results

### 2. EXECUTE Flow (Execution Only)
- Takes pre-validated code
- **Executes code** (user-specified or auto-selected platform)
- Returns execution results only

## Platform Selection Logic

### GENERATE Flow - Validation Execution (Automatic)

**No tool call needed - built into prompt logic:**

```
If selected_tables provided → Use EMR (execute_spark_code_emr)
Otherwise → Use Lambda (execute_spark_code_lambda)
```

**Reason:**
- Glue tables require Hive support → EMR
- S3 files or sample data → Lambda (faster)

### EXECUTE Flow - Final Execution (User Choice or Auto)

**execution_platform values:**

1. **'lambda'**: Always use Lambda (explicit)
2. **'emr'**: Always use EMR (explicit)
3. **'auto'**: Call `select_execution_platform` tool
   - File size > 500MB → EMR
   - File size ≤ 500MB → Lambda
   - Unknown size → Lambda (default)

## Tools

### New Tools (3)

1. **`select_execution_platform(s3_input_path, file_size_mb)`**
   - Only used in EXECUTE flow when execution_platform='auto'
   - Returns 'lambda' or 'emr' based on file size threshold

2. **`execute_spark_code_lambda(spark_code, s3_output_path)`**
   - Executes on AWS Lambda
   - Used for: S3 validation, Lambda execution

3. **`execute_spark_code_emr(spark_code, s3_output_path)`**
   - Executes on EMR Serverless
   - Used for: Glue validation, EMR execution

### Removed Tools (1)

- **`execute_spark_code`** - Replaced by separate Lambda and EMR tools

## System Prompt Changes

### GENERATE REQUEST Workflow

**Step 5 - Validation Execution:**
```
- If selected_tables are provided: Use EMR (call execute_spark_code_emr)
- Otherwise: Use Lambda (call execute_spark_code_lambda)
```

No tool call for platform selection - it's automatic based on data source.

### EXECUTE REQUEST Workflow

**Step 1 - Platform Selection:**
```
- If execution_platform == 'auto':
  - Call select_execution_platform(s3_input_path, file_size_mb)
  - Use returned platform
- Otherwise: Use execution_platform value directly
```

## Examples

### Example 1: GENERATE with Glue Tables

```python
payload = {
    "prompt": "Join customers and orders",
    "selected_tables": ["db.customers", "db.orders"],
    "s3_output_path": "s3://bucket/output/",
    "skip_generation": False  # GENERATE flow
}

# Flow:
# 1. Generate code
# 2. Validate code
# 3. Validation execution: EMR (selected_tables present)
#    → execute_spark_code_emr() called automatically
# 4. Return validated code + results
```

### Example 2: GENERATE with S3 File

```python
payload = {
    "prompt": "Analyze sales",
    "s3_input_path": "s3://bucket/sales.csv",
    "s3_output_path": "s3://bucket/output/",
    "skip_generation": False  # GENERATE flow
}

# Flow:
# 1. Generate code
# 2. Validate code
# 3. Validation execution: Lambda (no selected_tables)
#    → execute_spark_code_lambda() called automatically
# 4. Return validated code + results
```

### Example 3: EXECUTE with Auto Platform

```python
payload = {
    "spark_code": "...",  # Pre-validated code
    "execution_platform": "auto",
    "file_size_mb": 1000,
    "s3_output_path": "s3://bucket/output/",
    "skip_generation": True  # EXECUTE flow
}

# Flow:
# 1. Platform selection: select_execution_platform() → 'emr' (1000MB > 500MB)
# 2. Execute: execute_spark_code_emr() called
# 3. Return execution results
```

### Example 4: EXECUTE with Explicit Platform

```python
payload = {
    "spark_code": "...",  # Pre-validated code
    "execution_platform": "lambda",
    "s3_output_path": "s3://bucket/output/",
    "skip_generation": True  # EXECUTE flow
}

# Flow:
# 1. Execute: execute_spark_code_lambda() called directly
# 2. Return execution results
```

## Key Points

✅ **Minimal changes**: Only split execution tool, preserved original logic  
✅ **GENERATE flow**: Automatic platform selection (no tool call)  
✅ **EXECUTE flow**: User choice or auto-selection (tool call if 'auto')  
✅ **Original behavior**: Glue → EMR, S3 → Lambda (preserved)  
✅ **No simulations**: All real AWS service calls  

## Agent Tools List

```python
tools=[
    select_execution_platform,      # For EXECUTE flow with 'auto'
    fetch_glue_table_schema,
    call_code_generation_agent,
    extract_python_code,
    validate_spark_code,
    execute_spark_code_lambda,      # Lambda execution
    execute_spark_code_emr,         # EMR execution
    extract_execution_logs,
    fetch_spark_results
]
```

## Configuration

```python
config = {
    "file_size_threshold_mb": 500,  # For auto selection in EXECUTE flow
    "bedrock_region": "us-east-1",
    "s3_bucket": "your-bucket",
    "lambda_function": "your-lambda",
    "emr_application_id": "your-emr-app"
}
```

## Deployment

```bash
conda activate bedrock-sdk
cd backend/spark-supervisor-agent
python agent_deployment.py
```

## Summary

The implementation is now simplified:
- **GENERATE flow**: Validation platform is automatic (Glue → EMR, S3 → Lambda)
- **EXECUTE flow**: Execution platform is user choice or auto-selected
- **Minimal changes**: Only split the execution tool, preserved all original logic
- **No extra complexity**: No unnecessary tool calls or selection logic
