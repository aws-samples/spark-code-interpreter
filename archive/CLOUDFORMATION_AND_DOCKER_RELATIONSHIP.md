# CloudFormation and Docker Image Relationship

## Overview

The CloudFormation stack and Docker image work together but are deployed separately. Understanding this relationship is important for successful deployment.

## Architecture

```
CloudFormation Stack
    ├── Cognito User Pool
    ├── AgentCore Gateway
    ├── Wrapper Lambda (inline Python code)
    ├── Spark Lambda (references Docker image) ← DOCKER IMAGE
    ├── S3 Bucket
    ├── EMR Serverless
    └── IAM Roles
```

## What's in CloudFormation

The CloudFormation template (`cloudformation/spark-complete-stack.yml`) defines:

1. **Infrastructure Resources**:
   - Cognito User Pool and App Client
   - AgentCore Gateway
   - S3 Bucket
   - EMR Serverless Application
   - IAM Roles and Policies

2. **Wrapper Lambda** (inline code):
   - Python code embedded in CloudFormation
   - Can be updated by updating the stack
   - Contains natural language → agent invocation logic

3. **Spark Lambda** (Docker reference):
   - **Only references** the Docker image location
   - Does NOT contain the actual code
   - Points to: `{account}.dkr.ecr.{region}.amazonaws.com/dev-spark-lambda:latest`

## What's in Docker Image

The Docker image (`Docker/`) contains:

1. **Spark Lambda Handler** (`sparkLambdaHandler.py`):
   - PySpark execution logic
   - S3 configuration handling ← **S3 FIX IS HERE**
   - Error handling and logging

2. **Spark Runtime**:
   - Apache Spark 3.3.0
   - Hadoop libraries
   - AWS SDK JARs
   - Python dependencies

3. **Configuration**:
   - Spark configuration
   - Log4j settings
   - JAR downloads

## Deployment Relationship

### Initial Deployment

```
1. Build Docker Image
   ↓
2. Push to ECR
   ↓
3. Deploy CloudFormation Stack
   (references Docker image)
```

### Updating Docker Code (S3 Fix)

```
1. Modify Docker/sparkLambdaHandler.py
   ↓
2. Rebuild Docker Image
   ↓
3. Push to ECR (same tag: latest)
   ↓
4. Update Lambda Function
   (CloudFormation stack NOT updated)
```

**Key Point**: CloudFormation stack does NOT need to be updated when Docker code changes, because it only references the image location, not the image content.

## S3 Fix Example

### What Changed

**File**: `Docker/sparkLambdaHandler.py`

**Change**: Added automatic S3 configuration

```python
# Before (missing S3 config)
spark_config = input_data.get('config', '')

# After (with S3 config fallback)
spark_config = input_data.get('config', input_data.get('spark_config', {}))
if not spark_config:
    spark_config = {
        'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
    }
```

### How to Apply

**Option 1: Automated**
```bash
./scripts/rebuild-spark-lambda.sh
```

**Option 2: Manual**
```bash
cd Docker
docker build -t dev-spark-lambda:latest .
docker push {account}.dkr.ecr.{region}.amazonaws.com/dev-spark-lambda:latest
aws lambda update-function-code \
  --function-name dev-spark-on-lambda \
  --image-uri {account}.dkr.ecr.{region}.amazonaws.com/dev-spark-lambda:latest
```

**CloudFormation**: No update needed! ✅

## When to Update What

### Update CloudFormation Stack When:
- ✅ Adding/removing AWS resources
- ✅ Changing IAM permissions
- ✅ Modifying Lambda configuration (timeout, memory, env vars)
- ✅ Updating wrapper Lambda code (inline)
- ✅ Changing Gateway configuration
- ✅ Modifying S3 bucket settings

### Rebuild Docker Image When:
- ✅ Changing Spark Lambda handler code
- ✅ Updating Spark version
- ✅ Adding/removing JAR files
- ✅ Modifying Python dependencies
- ✅ Changing Spark configuration
- ✅ **Fixing S3 write issues** ← Current case

### Update Lambda Function When:
- ✅ After rebuilding Docker image
- ✅ To force Lambda to use new image version
- ✅ When CloudFormation references wrong image

## CloudFormation Template Notes

The template includes comments about the Docker image:

```yaml
# Spark Lambda - Executes PySpark code
# NOTE: The Docker image must include S3 configuration support
# See Docker/sparkLambdaHandler.py for S3A filesystem configuration
# Build and push image before deploying this stack:
#   cd Docker && docker build -t dev-spark-lambda:latest .
#   docker push {account}.dkr.ecr.{region}.amazonaws.com/dev-spark-lambda:latest
SparkOnLambda:
  Type: AWS::Lambda::Function
  Properties:
    FunctionName: !Sub '${Environment}-spark-on-lambda'
    PackageType: Image
    Code:
      ImageUri: !Sub '${AWS::AccountId}.dkr.ecr.${AWS::Region}.amazonaws.com/${Environment}-spark-lambda:latest'
```

## Deployment Checklist

### New Account Deployment

- [ ] 1. Deploy Bedrock Agents (get ARNs)
- [ ] 2. Build Docker image with S3 fix
- [ ] 3. Create ECR repository
- [ ] 4. Push Docker image to ECR
- [ ] 5. Deploy CloudFormation stack (with agent ARNs)
- [ ] 6. Add Gateway Target (manual)
- [ ] 7. Test end-to-end

### Applying S3 Fix to Existing Deployment

- [ ] 1. Rebuild Docker image (includes S3 fix)
- [ ] 2. Push to ECR (overwrites :latest tag)
- [ ] 3. Update Lambda function (force new image)
- [ ] 4. Test S3 writes
- [ ] 5. ~~Update CloudFormation~~ (NOT needed)

## Common Mistakes

### ❌ Mistake 1: Updating CloudFormation for Docker Changes
**Wrong**: Update CloudFormation stack after changing Docker code
**Right**: Just rebuild and push Docker image, then update Lambda

### ❌ Mistake 2: Forgetting to Update Lambda
**Wrong**: Push Docker image but don't update Lambda function
**Right**: After pushing image, run `aws lambda update-function-code`

### ❌ Mistake 3: Not Building Docker Before CloudFormation
**Wrong**: Deploy CloudFormation stack before Docker image exists
**Right**: Build and push Docker image first, then deploy stack

### ❌ Mistake 4: Modifying Wrong File
**Wrong**: Try to add S3 config to CloudFormation template
**Right**: Add S3 config to `Docker/sparkLambdaHandler.py`

## Verification

### Check CloudFormation Stack
```bash
aws cloudformation describe-stacks \
  --stack-name dev-spark-complete-stack \
  --query 'Stacks[0].StackStatus'
```

### Check Docker Image in ECR
```bash
aws ecr describe-images \
  --repository-name dev-spark-lambda \
  --query 'imageDetails[0].imagePushedAt'
```

### Check Lambda Function Image
```bash
aws lambda get-function \
  --function-name dev-spark-on-lambda \
  --query 'Code.ImageUri'
```

### Check Lambda Last Modified
```bash
aws lambda get-function \
  --function-name dev-spark-on-lambda \
  --query 'Configuration.LastModified'
```

## Summary

| Component | Location | Update Method | Includes S3 Fix? |
|-----------|----------|---------------|------------------|
| Infrastructure | CloudFormation | `aws cloudformation update-stack` | No |
| Wrapper Lambda | CloudFormation (inline) | `aws cloudformation update-stack` | No (not needed) |
| Spark Lambda Code | Docker Image | Rebuild + Push + Update Lambda | **YES** ✅ |
| Spark Lambda Config | CloudFormation | `aws cloudformation update-stack` | No (references only) |

## Key Takeaway

**The S3 fix is in the Docker image code, not in CloudFormation.**

To apply the fix:
1. Rebuild Docker image: `./scripts/rebuild-spark-lambda.sh`
2. CloudFormation stays the same ✅

---

**Status**: CloudFormation template is correct and includes notes about Docker image requirements. The S3 fix must be applied by rebuilding the Docker image.
