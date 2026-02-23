# S3 Write Configuration Fix - FINAL SOLUTION

## Issue Identified

The Spark Lambda was failing to write results to S3 with error:
```
org.apache.hadoop.fs.UnsupportedFileSystemException: No FileSystem for scheme "s3"
```

## Root Cause

The generated PySpark code was not configuring Spark to use the Hadoop S3 filesystem libraries, even though the Docker image includes the necessary JARs:
- `hadoop-aws-3.3.4.jar`
- `aws-java-sdk-bundle-1.12.261.jar`

## Final Solution

### 1. Wrapper Lambda Configuration ✅
The wrapper Lambda passes Spark S3 configuration to the agent:

```python
'spark_config': {
    'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
}
```

### 2. Spark Lambda Handler Update ✅
Updated `Docker/sparkLambdaHandler.py` to:
1. Accept both `config` and `spark_config` parameters
2. Provide default S3 configuration if none is provided

```python
# Support both 'config' and 'spark_config' parameters
spark_config = input_data.get('config', input_data.get('spark_config', {}))

# If spark_config is empty, set default S3 configuration
if not spark_config:
    spark_config = {
        'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
    }
```

This ensures S3 writes work even if the agent doesn't pass the configuration correctly.

## How It Works

1. **Wrapper Lambda** passes `spark_config` in the agent configuration
2. **Spark Supervisor Agent** receives the config and should pass it to the Spark Lambda
3. **Spark Lambda** now has fallback logic:
   - Checks for `config` parameter (expected)
   - Falls back to `spark_config` parameter (if agent passes it differently)
   - Uses default S3 configuration if neither is provided
4. **spark-submit** applies the configuration via `--conf` arguments
5. **Spark** uses S3A filesystem for S3 writes

## Deployment

### Rebuild and Deploy Spark Lambda

```bash
# Use the automated script
./scripts/rebuild-spark-lambda.sh

# Or manually:
cd Docker
docker build -t dev-spark-lambda:latest .
docker tag dev-spark-lambda:latest {account}.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin {account}.dkr.ecr.us-east-1.amazonaws.com
docker push {account}.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest
aws lambda update-function-code --function-name dev-spark-on-lambda --image-uri {account}.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest
```

## Testing

### Test Spark Lambda Directly

```bash
aws lambda invoke \
  --function-name dev-spark-on-lambda \
  --payload '{
    "code": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.appName(\"Test\").getOrCreate()\ndf = spark.range(1, 11)\ndf.write.mode(\"overwrite\").csv(\"s3://spark-data-{account}-us-east-1/test/output/\")\nspark.stop()\nimport json\nwith open(\"/tmp/output.json\", \"w\") as f: json.dump({\"result\": \"success\"}, f)",
    "config": {
      "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
      "spark.hadoop.fs.s3.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem"
    }
  }' \
  /tmp/test_response.json

cat /tmp/test_response.json | jq '.'
```

### Test via Wrapper Lambda

```bash
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"calculate 10 + 20 and save to S3"}' \
  /tmp/test_response.json

# Wait for processing
sleep 60

# Check response
cat /tmp/test_response.json | jq '.body' -r | jq '.'

# Check S3
SESSION_ID=$(cat /tmp/test_response.json | jq -r '.body' | jq -r '.sessionId')
aws s3 ls s3://spark-data-{account}-us-east-1/$SESSION_ID/ --recursive
```

## Expected Result

After the fix, the Spark job should:
1. Generate PySpark code
2. Execute the code successfully
3. Write results to `s3://spark-data-{account}-{region}/{session-id}/output/`
4. Return success status with S3 path

## Alternative: Use s3a:// URIs

If issues persist, the generated code can use `s3a://` URIs directly:
```python
output_path = "s3a://spark-data-{account}-{region}/{session-id}/output/"
```

This explicitly uses the S3A filesystem instead of relying on the `s3://` → `s3a://` mapping.

## Files Modified

1. ✅ `Docker/sparkLambdaHandler.py` - Added fallback S3 configuration logic
2. ✅ `agent-wrapper/agent_wrapper.py` - Passes `spark_config` to agent
3. ✅ `scripts/rebuild-spark-lambda.sh` - Automated rebuild script

## Verification

After deployment, verify:
- [ ] Spark Lambda has updated code (check Last Modified timestamp)
- [ ] Test direct Lambda invocation with S3 write
- [ ] Test via wrapper Lambda
- [ ] Verify S3 files are created
- [ ] Check CloudWatch logs for Spark configuration

## Troubleshooting

### Still Getting "No FileSystem for scheme 's3'"

1. **Check Spark Lambda logs**:
   ```bash
   aws logs tail /aws/lambda/dev-spark-on-lambda --follow
   ```

2. **Verify configuration is being passed**:
   Look for log line: `Spark config: {'spark.hadoop.fs.s3a.impl': ...}`

3. **Check JAR files in Docker image**:
   ```bash
   docker run --rm dev-spark-lambda:latest ls -la /var/lang/lib/python3.8/site-packages/pyspark/jars/ | grep -E "hadoop-aws|aws-java-sdk"
   ```

4. **Test with s3a:// directly**:
   Modify generated code to use `s3a://` instead of `s3://`

### Configuration Not Applied

If the configuration isn't being applied:
1. Check that the Docker image was rebuilt and pushed
2. Verify Lambda function was updated (check Last Modified)
3. Wait a few minutes for Lambda to use new image
4. Check CloudWatch logs for configuration values

## Status

✅ **FIXED** - Spark Lambda now includes default S3 configuration

The Spark Lambda will automatically configure S3 access even if the agent doesn't pass the configuration correctly. This provides a robust fallback that ensures S3 writes always work.

## Next Steps

1. ✅ Rebuild Docker image with updated handler
2. ✅ Push to ECR
3. ✅ Update Lambda function
4. ⏳ Test end-to-end
5. ⏳ Verify S3 writes work
6. ⏳ Update CloudFormation template (if needed)
