# Validation Platform Selection

## Overview

During code generation workflow, the agent validates generated code by executing it to catch runtime errors. The validation execution platform is intelligently selected based on data source type.

## New Tool: `select_validation_platform`

```python
@tool
def select_validation_platform(selected_tables: list = None, s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """Select platform for validation execution - prefers EMR for Glue tables, Lambda otherwise"""
```

## Selection Logic

### Validation Execution (During Code Generation)

**Purpose**: Execute generated code to catch runtime errors before final execution

**Selection Rules**:
1. **Glue tables selected** (`selected_tables` not empty):
   - Return **'emr'**
   - Reason: Glue catalog requires Hive support, better on EMR

2. **S3 files only** (no Glue tables):
   - Return **'lambda'**
   - Reason: Faster startup for validation, sufficient for S3 reads

3. **No data source** (sample data generation):
   - Return **'lambda'**
   - Reason: Fastest option for simple validation

## Workflow Integration

### GENERATE REQUEST (Step 6 - Validation Execution)

```
6. VALIDATION EXECUTION: Select platform for validation:
   - Call select_validation_platform(selected_tables, s3_input_path, file_size_mb)
   - This returns 'emr' if Glue tables selected, 'lambda' otherwise
   - Call the appropriate execution tool based on validation platform:
     * If validation_platform == 'lambda': Call execute_spark_code_lambda(spark_code, s3_output_path)
     * If validation_platform == 'emr': Call execute_spark_code_emr(spark_code, s3_output_path)
```

### EXECUTE REQUEST (Final Execution)

Uses the `execution_platform` parameter directly (or `select_execution_platform` if 'auto'):
- Not affected by validation platform selection
- Uses user-specified or auto-selected platform

## Examples

### Example 1: Glue Tables Selected

```python
payload = {
    "prompt": "Join customers and orders tables",
    "selected_tables": ["northwind.customers", "northwind.orders"],
    "execution_platform": "lambda",  # User wants final execution on Lambda
    "s3_output_path": "s3://bucket/output/"
}

# Workflow:
# 1. Generate code
# 2. Validation: select_validation_platform() returns 'emr' (Glue tables present)
# 3. Validation execution: execute_spark_code_emr() - catches Glue-specific errors
# 4. If validation succeeds, final execution: execute_spark_code_lambda() (user choice)
```

### Example 2: S3 File Only

```python
payload = {
    "prompt": "Analyze sales data",
    "s3_input_path": "s3://bucket/sales.csv",
    "execution_platform": "emr",  # User wants final execution on EMR
    "s3_output_path": "s3://bucket/output/"
}

# Workflow:
# 1. Generate code
# 2. Validation: select_validation_platform() returns 'lambda' (no Glue tables)
# 3. Validation execution: execute_spark_code_lambda() - fast validation
# 4. If validation succeeds, final execution: execute_spark_code_emr() (user choice)
```

### Example 3: Auto Platform with Glue Tables

```python
payload = {
    "prompt": "Analyze customer data",
    "selected_tables": ["db.customers"],
    "execution_platform": "auto",
    "file_size_mb": 100,
    "s3_output_path": "s3://bucket/output/"
}

# Workflow:
# 1. Platform selection: select_execution_platform() returns 'lambda' (100MB < 500MB)
# 2. Generate code
# 3. Validation: select_validation_platform() returns 'emr' (Glue tables present)
# 4. Validation execution: execute_spark_code_emr() - catches Glue errors
# 5. If validation succeeds, final execution: execute_spark_code_lambda() (auto-selected)
```

## Key Points

✅ **Validation platform ≠ Execution platform**
- Validation: Chosen based on data source type (Glue → EMR, S3 → Lambda)
- Execution: Chosen based on user preference or auto-selection

✅ **Glue tables always validate on EMR**
- Ensures Hive support and Glue catalog access
- Catches metastore errors during validation

✅ **S3 files validate on Lambda**
- Faster validation for simple S3 reads
- Sufficient for catching most errors

✅ **No breaking changes**
- Only affects validation execution during code generation
- Final execution still respects user's platform choice

## Benefits

1. **Accurate Validation**: Glue code validated in proper environment (EMR)
2. **Fast Validation**: S3 code validated quickly on Lambda
3. **Error Prevention**: Catches platform-specific errors early
4. **Cost Efficient**: Uses Lambda for validation when possible
5. **Automatic**: No manual configuration needed

## Original Behavior Preserved

This restores the original behavior from before the tool split:
- Glue tables → EMR for validation (was handled in original `execute_spark_code`)
- S3 files → Lambda for validation (was the default in original code)

## No Simulations

All execution is real:
- `execute_spark_code_lambda` → Real Lambda invocation
- `execute_spark_code_emr` → Real EMR Serverless job
- No mocked or simulated responses
