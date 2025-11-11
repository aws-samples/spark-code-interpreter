# Spark Configuration Integration

## ✅ Configuration Integrated

All Spark code interpreter configuration from `config.json` has been integrated into the unified backend.

## Configuration Details

### From Spark Code Interpreter config.json
```json
{
  "s3_bucket": "spark-data-260005718447-us-east-1",
  "lambda_function": "sparkOnLambda-spark-code-interpreter",
  "emr_application_id": "00fv6g7rptsov009",
  "bedrock_region": "us-east-1",
  "bedrock_model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
  "max_retries": 5,
  "file_size_threshold_mb": 500,
  "result_preview_rows": 100,
  "presigned_url_expiry_hours": 24,
  "lambda_timeout_seconds": 300,
  "emr_timeout_minutes": 60
}
```

## Integration Points

### 1. Spark Supervisor Agent (`spark_supervisor_agent.py`)

**Configuration Function**:
```python
def load_spark_config():
    return {
        "s3_bucket": "spark-data-260005718447-us-east-1",
        "lambda_function": "sparkOnLambda-spark-code-interpreter",
        "emr_application_id": "00fv6g7rptsov009",
        "bedrock_region": "us-east-1",
        "bedrock_model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "max_retries": 5,
        "file_size_threshold_mb": 500,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "lambda_timeout_seconds": 300,
        "emr_timeout_minutes": 60
    }
```

**Used In**:
- ✅ `validate_spark_code()` - Uses `file_size_threshold_mb`
- ✅ `execute_spark_code()` - Uses `lambda_function`, `emr_application_id`, `lambda_timeout_seconds`, `emr_timeout_minutes`
- ✅ `fetch_spark_results()` - Uses `result_preview_rows`, `presigned_url_expiry_hours`

### 2. Lambda Execution

**Function**: `sparkOnLambda-spark-code-interpreter`
**Timeout**: 300 seconds (5 minutes)
**Region**: us-east-1

**Implementation**:
```python
lambda_client.invoke(
    FunctionName=config['lambda_function'],
    InvocationType='RequestResponse',
    Payload=json.dumps({
        'spark_code': spark_code,
        's3_output_path': s3_output_path
    })
)
```

### 3. EMR Serverless Execution

**Application ID**: `00fv6g7rptsov009`
**Timeout**: 60 minutes
**Region**: us-east-1

**Implementation**:
```python
emr_client.start_job_run(
    applicationId=config['emr_application_id'],
    executionRoleArn=EMR_EXECUTION_ROLE_ARN,
    jobDriver={
        'sparkSubmit': {
            'entryPoint': script_path,
            'sparkSubmitParameters': '--conf spark.executor.memory=4g --conf spark.executor.cores=2'
        }
    }
)
```

### 4. S3 Configuration

**Bucket**: `spark-data-260005718447-us-east-1`
**Region**: us-east-1

**Used For**:
- Storing Spark scripts for EMR execution
- Storing execution results
- Temporary data storage

### 5. File Size Threshold

**Threshold**: 500 MB

**Logic**:
- Files ≤ 500MB → Execute on Lambda
- Files > 500MB → Execute on EMR Serverless
- Can be overridden by `execution_platform` parameter

### 6. Result Preview

**Preview Rows**: 100
**Presigned URL Expiry**: 24 hours

**Features**:
- Returns first 100 rows by default
- Generates presigned URL for full results download
- URL valid for 24 hours

### 7. Backend API Endpoint

**Endpoint**: `GET /spark/config`

**Response**:
```json
{
  "s3_bucket": "spark-data-260005718447-us-east-1",
  "lambda_function": "sparkOnLambda-spark-code-interpreter",
  "emr_application_id": "00fv6g7rptsov009",
  "bedrock_region": "us-east-1",
  "bedrock_model": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
  "max_retries": 5,
  "file_size_threshold_mb": 500,
  "result_preview_rows": 100,
  "presigned_url_expiry_hours": 24,
  "lambda_timeout_seconds": 300,
  "emr_timeout_minutes": 60
}
```

## Configuration Usage

### Automatic Platform Selection
```python
# Based on file size
if file_size_mb > 500:
    execution_platform = 'emr'
else:
    execution_platform = 'lambda'
```

### Lambda Execution Flow
1. Validate Spark code
2. Invoke Lambda function: `sparkOnLambda-spark-code-interpreter`
3. Wait up to 300 seconds for response
4. Fetch results from S3
5. Return first 100 rows + presigned URL

### EMR Execution Flow
1. Validate Spark code
2. Upload script to S3: `s3://spark-data-260005718447-us-east-1/scripts/`
3. Start EMR job on application: `00fv6g7rptsov009`
4. Poll job status every 10 seconds
5. Timeout after 60 minutes
6. Fetch results from S3
7. Return first 100 rows + presigned URL

## Testing Configuration

### Test Lambda Config
```bash
curl http://localhost:8000/spark/config | jq '.lambda_function'
# Output: "sparkOnLambda-spark-code-interpreter"
```

### Test EMR Config
```bash
curl http://localhost:8000/spark/config | jq '.emr_application_id'
# Output: "00fv6g7rptsov009"
```

### Test File Size Threshold
```bash
curl http://localhost:8000/spark/config | jq '.file_size_threshold_mb'
# Output: 500
```

## Environment Variables (Optional Override)

While configuration is hardcoded, these environment variables can be used for overrides:

```bash
export SPARK_S3_BUCKET=spark-data-260005718447-us-east-1
export SPARK_LAMBDA_FUNCTION=sparkOnLambda-spark-code-interpreter
export SPARK_EMR_APP_ID=00fv6g7rptsov009
export EMR_EXECUTION_ROLE_ARN=arn:aws:iam::260005718447:role/EMRServerlessExecutionRole
```

## Deployment Status

- ✅ Configuration integrated into `spark_supervisor_agent.py`
- ✅ Lambda function details included
- ✅ EMR application ID included
- ✅ S3 bucket configured
- ✅ Timeouts configured
- ✅ File size threshold configured
- ✅ Result preview settings configured
- ✅ Backend API endpoint added
- ✅ Agent redeployed with updated config

## Verification

### Check Agent Has Config
```bash
# View agent logs
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-EZPQeDGCjR-DEFAULT \
  --since 5m | grep -i config
```

### Test Execution
```bash
# Test Lambda execution (small file)
curl -X POST http://localhost:8000/spark/validate-execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "<spark-code>",
    "execution_platform": "lambda",
    "file_size_mb": 100
  }'

# Test EMR execution (large file)
curl -X POST http://localhost:8000/spark/validate-execute \
  -H "Content-Type: application/json" \
  -d '{
    "code": "<spark-code>",
    "execution_platform": "emr",
    "file_size_mb": 1000
  }'
```

## Configuration Benefits

1. **Consistent Settings**: Same config as original Spark code interpreter
2. **Automatic Platform Selection**: Based on file size threshold
3. **Proper Timeouts**: Lambda (5 min), EMR (60 min)
4. **Result Management**: Preview rows + presigned URLs
5. **Resource Identification**: Correct Lambda function and EMR application
6. **Region Consistency**: All resources in us-east-1

## Next Steps

1. ✅ Configuration integrated
2. ✅ Agent redeployed
3. ⏳ Test Lambda execution with actual function
4. ⏳ Test EMR execution with actual application
5. ⏳ Verify S3 bucket access
6. ⏳ Test end-to-end workflow
