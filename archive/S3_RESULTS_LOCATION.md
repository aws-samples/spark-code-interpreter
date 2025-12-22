# S3 Results Location

## Current Status

### ✅ What's Working
1. Agent generates PySpark code successfully
2. Code is saved to S3: `s3://spark-data-817323390093-us-east-1/scripts/`
3. Agent attempts to execute the code

### ❌ What's Failing
Spark execution is failing because:
1. Agent generates code that writes to `s3://spark-results-{session-id}/`
2. This bucket doesn't exist
3. Execution fails with S3 access errors

---

## S3 Buckets

### Main Data Bucket (Exists)
```
s3://spark-data-817323390093-us-east-1/
```

**Contents:**
- `scripts/` - Generated Spark code files
- Each file is named: `spark_script_{timestamp}.py`
- Also session-based folders: `{session-id}/{session-id}_code.py`

**Example:**
```bash
aws s3 ls s3://spark-data-817323390093-us-east-1/scripts/ --human-readable
```

### Results Bucket (Does NOT Exist)
The agent tries to write results to:
```
s3://spark-results-{session-id}/
```

This bucket is dynamically generated per session but doesn't actually exist, causing execution failures.

---

## Agent Response Format

When you invoke the agent, it returns:

```json
{
  "spark_code": "from pyspark.sql import SparkSession...",
  "execution_result": "failed",
  "execution_message": "Execution failed on both Lambda and EMR platforms...",
  "execution_output": [],
  "actual_results": [],
  "s3_output_path": null
}
```

**Fields:**
- `spark_code` - The generated PySpark code ✅
- `execution_result` - "success" or "failed" ❌ (currently failing)
- `execution_message` - Error details
- `actual_results` - Would contain the query results if execution succeeded
- `s3_output_path` - Would contain S3 path if results were written

---

## Why Execution is Failing

The agent is configured to execute the code, but:

1. **Lambda execution fails:** Missing configuration or permissions
2. **EMR execution fails:** No EMR application ID configured
3. **S3 write fails:** Results bucket doesn't exist

---

## Solutions

### Option 1: Fix S3 Configuration

Update the agent config to use the existing bucket:

```python
'config': {
    's3_bucket': 'spark-data-817323390093-us-east-1',
    's3_output_prefix': 'output/',  # Add this
    # ... other config
}
```

The agent should write results to:
```
s3://spark-data-817323390093-us-east-1/output/{session-id}/
```

### Option 2: Skip Execution (Code Generation Only)

If you only need the code, not the execution:

```python
payload = {
    'prompt': 'what is 5+5',
    'skip_execution': True  # Only generate code
}
```

This will return the code without attempting to execute it.

### Option 3: Check Lambda Execution Logs

The Spark Lambda might be executing but failing. Check its logs:

```bash
aws logs tail /aws/lambda/dev-spark-on-lambda --since 10m --region us-east-1
```

---

## Where to Find Results

### Generated Code
```bash
# List all generated code
aws s3 ls s3://spark-data-817323390093-us-east-1/scripts/ --recursive

# Download specific code file
aws s3 cp s3://spark-data-817323390093-us-east-1/scripts/spark_script_1766412052.py -
```

### Execution Results (when working)
Results would be in:
```
s3://spark-data-817323390093-us-east-1/output/{session-id}/
```

Or in the Lambda response under `actual_results` field.

---

## Current Behavior

**When you call the agent:**

1. ✅ Agent receives prompt: "what is 5+5"
2. ✅ Agent generates PySpark code
3. ✅ Code saved to S3: `s3://spark-data-817323390093-us-east-1/scripts/spark_script_*.py`
4. ❌ Agent attempts execution → fails
5. ❌ Returns: `execution_result: "failed"`

**The code IS generated and saved to S3, but execution fails.**

---

## Testing

### Get Generated Code
```bash
# List recent code files
aws s3 ls s3://spark-data-817323390093-us-east-1/scripts/ \
  --recursive --human-readable | tail -5

# Download the latest code
LATEST=$(aws s3 ls s3://spark-data-817323390093-us-east-1/scripts/ \
  --recursive | sort | tail -1 | awk '{print $4}')
aws s3 cp s3://spark-data-817323390093-us-east-1/$LATEST -
```

### Check Lambda Response
```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"what is 5+5"}' \
  /tmp/response.json

# Parse the response
cat /tmp/response.json | jq '.body' -r | jq '.result' -r | jq '.'
```

---

## Summary

**S3 Bucket for Results:**
```
s3://spark-data-817323390093-us-east-1/
```

**What's there:**
- ✅ Generated code: `scripts/spark_script_*.py`
- ❌ Execution results: Not yet (execution failing)

**Next Steps:**
1. Fix S3 output configuration
2. Or use code-generation-only mode
3. Or debug Lambda execution failures

The agent IS working - it's generating code and saving it to S3. The execution part needs configuration fixes.
