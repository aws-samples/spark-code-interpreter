# S3 Output Path Fix

## Problem
After Spark code execution, the actual S3 path where results were written was not being passed back from the Lambda to the calling supervisor agent. This caused the `fetch_spark_results` tool to fail because it was looking in the wrong S3 location.

## Root Cause
The data flow had a gap:

1. **Spark Lambda** (`sparkLambdaHandler.py`) executed code and wrote results to S3
2. Lambda returned execution results but **did NOT include the actual S3 output path**
3. **Supervisor Agent** (`spark_supervisor_agent.py`) only knew the original input path, not where files were actually written
4. When Spark code wrote to subdirectories (e.g., `s3://bucket/session/output/results/`), the supervisor couldn't find the files

## Solution

### 1. Modified `sparkLambdaHandler.py`
Added the actual S3 output path to the Lambda response:

```python
# Extract actual S3 output path from result if available
actual_s3_output_path = None
if isinstance(result, dict) and 's3_output_path' in result:
    actual_s3_output_path = result['s3_output_path']
elif bucket and s3_file_path:
    # Construct the base output path
    actual_s3_output_path = f"s3://{bucket}/{s3_file_path}"

tool_result = {
    "result": result,
    "s3_output_path": actual_s3_output_path,  # NEW: Include actual output path
    "image_dict": image_holder,
    "plotly": plotly_holder
}
```

### 2. Modified `spark_supervisor_agent.py` - `execute_spark_code_lambda` function
Updated to extract and use the actual S3 path from Lambda response:

```python
result = json.loads(response['Payload'].read())

# Parse the response body if it's a string
if 'body' in result:
    body = json.loads(result['body']) if isinstance(result['body'], str) else result['body']
else:
    body = result

# Extract actual S3 output path from Lambda response
actual_s3_output_path = body.get('s3_output_path', s3_output_path)

lambda_status = 'success' if result.get('statusCode') == 200 else 'error'

return {
    'status': lambda_status,
    'execution_platform': 'lambda',
    's3_output_path': actual_s3_output_path,  # NEW: Use actual path from Lambda
    'result': body,
    'lambda_function': config['lambda_function']
}
```

## Files Modified
1. `cloudformation-template/us-east-1-stable-jwt/Docker/sparkLambdaHandler.py`
2. `cloudformation-template/us-east-1-stable-jwt/agent-code/spark-supervisor-agent/spark_supervisor_agent.py`
3. `cloudformation-template/us-east-1-stable-jwt/archive/backend-development/spark-supervisor-agent/spark_supervisor_agent.py`

## Testing
After deploying these changes:

1. Deploy the updated Spark Lambda (Docker image)
2. Deploy the updated Spark Supervisor Agent
3. Test with a calculation that writes to S3:
   ```bash
   aws lambda invoke \
     --function-name dev-spark-agent-wrapper \
     --payload '{"prompt":"what is 6*20"}' \
     --region us-east-1 \
     /tmp/test_result.json
   ```

The supervisor agent should now correctly receive the S3 output path and be able to fetch results using `fetch_spark_results`.

## Benefits
- Supervisor agent can now find results regardless of subdirectory structure
- Proper error handling when S3 path is missing
- Consistent behavior between Lambda and EMR execution platforms
- Better debugging with explicit S3 paths in responses
