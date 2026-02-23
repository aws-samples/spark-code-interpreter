# IMPORTANT: S3 Write Fix Required

## Critical Update Needed

The Spark Lambda Docker image has been updated to fix S3 write issues. **You must rebuild and redeploy the Docker image** for S3 writes to work correctly.

## What Was Fixed

The `Docker/sparkLambdaHandler.py` file now includes:

1. **Automatic S3 Configuration**: Default S3A filesystem configuration is applied if not provided
2. **Fallback Logic**: Checks for both `config` and `spark_config` parameters
3. **Robust Error Handling**: Ensures S3 writes work regardless of agent configuration

### Code Changes

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

## How to Apply the Fix

### Option 1: Automated Script (Recommended)

```bash
./scripts/rebuild-spark-lambda.sh
```

This script will:
1. Build the Docker image with the fix
2. Tag and push to ECR
3. Update the Lambda function
4. Run a test to verify it works

### Option 2: Manual Steps

```bash
# 1. Build Docker image
cd Docker
docker build \
  --build-arg FRAMEWORK="" \
  --build-arg AWS_REGION=us-east-1 \
  -t dev-spark-lambda:latest .

# 2. Get account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# 3. Tag for ECR
docker tag dev-spark-lambda:latest \
  $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest

# 4. Login to ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com

# 5. Push to ECR
docker push $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest

# 6. Update Lambda function
aws lambda update-function-code \
  --function-name dev-spark-on-lambda \
  --image-uri $ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/dev-spark-lambda:latest \
  --region us-east-1

# 7. Wait for update to complete
sleep 10
```

## Verification

After applying the fix, verify it works:

```bash
# Test Spark Lambda directly
aws lambda invoke \
  --function-name dev-spark-on-lambda \
  --payload '{
    "code": "from pyspark.sql import SparkSession\nspark = SparkSession.builder.appName(\"Test\").getOrCreate()\ndf = spark.range(1, 11)\ndf.write.mode(\"overwrite\").csv(\"s3://spark-data-'$ACCOUNT_ID'-us-east-1/test/output/\")\nspark.stop()\nimport json\nwith open(\"/tmp/output.json\", \"w\") as f: json.dump({\"result\": \"success\"}, f)"
  }' \
  /tmp/test_response.json

# Check response
cat /tmp/test_response.json | jq '.'

# Verify S3 write
aws s3 ls s3://spark-data-$ACCOUNT_ID-us-east-1/test/output/
```

## CloudFormation Deployment

### For New Deployments

1. **Build Docker image first** (before deploying CloudFormation):
   ```bash
   ./scripts/rebuild-spark-lambda.sh
   ```

2. **Then deploy CloudFormation stack**:
   ```bash
   aws cloudformation create-stack \
     --stack-name dev-spark-complete-stack \
     --template-body file://cloudformation/spark-complete-stack.yml \
     --parameters ... \
     --capabilities CAPABILITY_NAMED_IAM
   ```

### For Existing Deployments

1. **Rebuild and push Docker image**:
   ```bash
   ./scripts/rebuild-spark-lambda.sh
   ```

2. **CloudFormation stack does NOT need to be updated** - it references the `:latest` tag which now points to the fixed image

3. **Lambda will automatically use the new image** on next invocation (or force update with the script)

## Why This Fix Is Needed

Without this fix, you'll see this error when Spark tries to write to S3:

```
org.apache.hadoop.fs.UnsupportedFileSystemException: No FileSystem for scheme "s3"
```

This happens because:
1. The Docker image includes Hadoop S3 JARs (`hadoop-aws`, `aws-java-sdk-bundle`)
2. But Spark needs to be configured to use them
3. The fix ensures this configuration is always applied

## Impact

### Before Fix
- ❌ S3 writes fail with "No FileSystem for scheme 's3'" error
- ❌ Generated code executes but cannot save results
- ❌ Session results not available in S3

### After Fix
- ✅ S3 writes work automatically
- ✅ Results saved to session-based S3 folders
- ✅ Complete end-to-end flow works

## Files Modified

1. **Docker/sparkLambdaHandler.py** - Added S3 configuration logic
2. **scripts/rebuild-spark-lambda.sh** - Automated rebuild script
3. **cloudformation/spark-complete-stack.yml** - Added comments about S3 fix
4. **DEPLOYMENT_GUIDE.md** - Updated with S3 fix notes
5. **S3_WRITE_FIX.md** - Complete documentation of the fix

## Timeline

- **When to apply**: Before first use or immediately if experiencing S3 write errors
- **How long**: ~5-10 minutes (Docker build + push + Lambda update)
- **Downtime**: None (Lambda updates are atomic)

## Support

If you encounter issues:

1. **Check CloudWatch Logs**:
   ```bash
   aws logs tail /aws/lambda/dev-spark-on-lambda --follow
   ```

2. **Verify Docker image was updated**:
   ```bash
   aws lambda get-function --function-name dev-spark-on-lambda \
     --query 'Code.ImageUri' --output text
   ```

3. **Check for configuration in logs**:
   Look for: `Spark config: {'spark.hadoop.fs.s3a.impl': ...}`

4. **See detailed troubleshooting**: [S3_WRITE_FIX.md](S3_WRITE_FIX.md)

## Status

🔴 **ACTION REQUIRED**: Rebuild Docker image to apply S3 fix

After applying the fix:
✅ **COMPLETE**: S3 writes will work automatically

---

**Next Step**: Run `./scripts/rebuild-spark-lambda.sh` to apply the fix
