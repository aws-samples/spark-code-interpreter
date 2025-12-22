# Troubleshooting Guide

This guide covers common issues and their solutions for the Spark Code Interpreter deployment.

## Common Issues

### 1. Bedrock Throttling

**Symptom**:
```
serviceUnavailableException: Bedrock is unable to process your request
```

**Cause**: AWS Bedrock service quota limits being exceeded

**Solutions**:
- **Wait between requests**: Allow 10-15 minutes between agent invocations
- **Request quota increase**: 
  ```bash
  # Check current quotas
  aws service-quotas get-service-quota \
    --service-code bedrock \
    --quota-code L-XXXX \
    --region us-east-1
  
  # Request increase via AWS Support Console
  ```
- **Use different model**: Switch to Claude Haiku 4.5 (higher quotas)
  ```python
  # In config_snowflake.py
  "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
  ```

**Prevention**:
- Implement exponential backoff in client code
- Use request queuing system
- Monitor CloudWatch metrics for throttling

### 2. Lambda Function Not Found

**Symptom**:
```
ResourceNotFoundException: Function not found: arn:aws:lambda:us-east-1:ACCOUNT:function:sparkOnLambda-spark-code-interpreter
```

**Cause**: Incorrect Lambda function name in configuration

**Solutions**:
1. **Verify function exists**:
   ```bash
   aws lambda list-functions --region us-east-1 | grep spark
   ```

2. **Update configuration**:
   ```bash
   # In config_snowflake.py
   "lambda_function": "dev-spark-on-lambda"  # Use actual function name
   ```

3. **Check CloudFormation outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name dev-spark-complete-stack \
     --query 'Stacks[0].Outputs[?OutputKey==`SparkLambdaFunctionName`].OutputValue' \
     --output text
   ```

### 3. EMR Cross-Account Role Error

**Symptom**:
```
AccessDeniedException: Cross-account pass role is not allowed
```

**Cause**: EMR execution role ARN contains wrong account ID

**Solutions**:
1. **Get current account ID**:
   ```bash
   aws sts get-caller-identity --query Account --output text
   ```

2. **Update EMR role ARN**:
   ```python
   # In spark_supervisor_agent.py
   executionRoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/dev-spark-emr-execution-role"
   ```

3. **Verify role exists**:
   ```bash
   aws iam get-role --role-name dev-spark-emr-execution-role
   ```

### 4. S3 Access Denied

**Symptom**:
```
AccessDenied: Access Denied when writing to s3://bucket/path
```

**Cause**: IAM role lacks S3 permissions or bucket doesn't exist

**Solutions**:
1. **Verify bucket exists**:
   ```bash
   aws s3 ls s3://spark-data-ACCOUNT-us-east-1/
   ```

2. **Check IAM role permissions**:
   ```bash
   aws iam get-role-policy \
     --role-name dev-spark-lambda-role \
     --policy-name SparkLambdaPolicy
   ```

3. **Add S3 permissions**:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "s3:GetObject",
       "s3:PutObject",
       "s3:DeleteObject",
       "s3:ListBucket"
     ],
     "Resource": [
       "arn:aws:s3:::spark-data-ACCOUNT-us-east-1",
       "arn:aws:s3:::spark-data-ACCOUNT-us-east-1/*"
     ]
   }
   ```

### 5. Agent Deployment Fails

**Symptom**:
```
ModuleNotFoundError: No module named 'bedrock_agentcore.cli'
```

**Cause**: bedrock-agentcore CLI not installed

**Solutions**:
1. **Install CLI**:
   ```bash
   pip install bedrock-agentcore-starter-toolkit
   ```

2. **Verify installation**:
   ```bash
   bedrock-agentcore --version
   ```

3. **Use correct Python environment**:
   ```bash
   python3 -m pip install bedrock-agentcore-starter-toolkit
   ```

### 6. EMR Job Timeout

**Symptom**:
```
Job exceeded timeout of 10 minutes
```

**Cause**: EMR job taking longer than configured timeout

**Solutions**:
1. **Increase timeout**:
   ```python
   # In config_snowflake.py
   "emr_timeout_minutes": 20  # Increase from 10
   ```

2. **Optimize Spark code**:
   - Use partitioning
   - Filter early
   - Cache intermediate results
   - Increase executor resources

3. **Check EMR logs**:
   ```bash
   aws emr-serverless get-job-run \
     --application-id APP_ID \
     --job-run-id JOB_RUN_ID
   ```

### 7. Lambda Timeout

**Symptom**:
```
Task timed out after 300.00 seconds
```

**Cause**: Lambda execution exceeding 5-minute limit

**Solutions**:
1. **Use EMR for large datasets**:
   ```python
   # Automatically select based on file size
   if file_size_mb > 100:
       platform = 'emr'
   ```

2. **Optimize Spark code**:
   - Reduce data processing
   - Use sampling for large datasets
   - Optimize transformations

3. **Increase Lambda resources**:
   ```yaml
   # In CloudFormation
   MemorySize: 3008  # Maximum
   Timeout: 300      # Maximum
   ```

### 8. VPC Configuration Issues

**Symptom**:
```
Cannot connect to EMR application in VPC
```

**Cause**: Incorrect VPC/subnet configuration

**Solutions**:
1. **Verify VPC has internet access**:
   - NAT Gateway for private subnets
   - Internet Gateway for public subnets

2. **Check security groups**:
   ```bash
   aws ec2 describe-security-groups \
     --group-ids sg-xxxxx
   ```

3. **Verify subnet configuration**:
   ```bash
   aws ec2 describe-subnets --subnet-ids subnet-xxxxx
   ```

### 9. PostgreSQL Connection Fails

**Symptom**:
```
Connection refused or timeout when connecting to PostgreSQL
```

**Cause**: Network, credentials, or JDBC driver issues

**Solutions**:
1. **Verify JDBC driver exists**:
   ```bash
   aws s3 ls s3://spark-data-ACCOUNT-us-east-1/jars/postgresql-42.7.8.jar
   ```

2. **Check credentials in Secrets Manager**:
   ```bash
   aws secretsmanager get-secret-value \
     --secret-id arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:NAME
   ```

3. **Test connectivity**:
   ```bash
   # From Lambda/EMR VPC
   telnet postgres-host 5432
   ```

4. **Verify security group rules**:
   - PostgreSQL security group allows inbound on port 5432
   - From Lambda/EMR security group

### 10. Glue Catalog Errors

**Symptom**:
```
Database does not exist or table not found
```

**Cause**: Glue catalog not configured or table doesn't exist

**Solutions**:
1. **Verify Glue database exists**:
   ```bash
   aws glue get-database --name database_name
   ```

2. **List tables**:
   ```bash
   aws glue get-tables --database-name database_name
   ```

3. **Check IAM permissions**:
   ```json
   {
     "Effect": "Allow",
     "Action": [
       "glue:GetDatabase",
       "glue:GetTable",
       "glue:GetPartitions"
     ],
     "Resource": "*"
   }
   ```

## Debugging Steps

### Check CloudWatch Logs

**Backend Lambda logs**:
```bash
aws logs tail /aws/lambda/dev-spark-supervisor-invocation --follow
```

**Agent logs**:
```bash
aws logs tail /aws/bedrock-agentcore/runtimes/spark_supervisor_agent-*/DEFAULT --follow
```

**Spark Lambda logs**:
```bash
aws logs tail /aws/lambda/dev-spark-on-lambda --follow
```

**EMR logs** (in S3):
```bash
aws s3 ls s3://spark-data-ACCOUNT-us-east-1/logs/emr/ --recursive
```

### Verify Configuration

**Check deployed stack**:
```bash
aws cloudformation describe-stacks --stack-name dev-spark-complete-stack
```

**Verify Lambda function**:
```bash
aws lambda get-function --function-name dev-spark-on-lambda
```

**Check EMR application**:
```bash
aws emr-serverless get-application --application-id APP_ID
```

**Verify S3 bucket**:
```bash
aws s3 ls s3://spark-data-ACCOUNT-us-east-1/
```

### Test Components

**Test Lambda directly**:
```bash
aws lambda invoke \
  --function-name dev-spark-on-lambda \
  --payload '{"spark_code":"print(\"test\")","s3_output_path":"s3://bucket/test"}' \
  response.json
```

**Test agent invocation**:
```bash
curl -X POST http://ALB_URL/spark/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "create a simple dataset",
    "session_id": "test-123",
    "execution_platform": "lambda"
  }'
```

## Performance Optimization

### Lambda Performance

1. **Increase memory**: More memory = more CPU
   ```yaml
   MemorySize: 3008  # Maximum
   ```

2. **Use provisioned concurrency**: Eliminate cold starts
   ```bash
   aws lambda put-provisioned-concurrency-config \
     --function-name dev-spark-on-lambda \
     --provisioned-concurrent-executions 1
   ```

3. **Optimize Spark code**:
   - Use broadcast joins for small tables
   - Partition data appropriately
   - Cache frequently used DataFrames

### EMR Performance

1. **Adjust worker configuration**:
   ```python
   --conf spark.executor.memory=4g
   --conf spark.executor.cores=2
   --conf spark.driver.memory=2g
   ```

2. **Use appropriate file formats**:
   - Parquet for columnar data
   - ORC for ACID operations
   - CSV only for small datasets

3. **Enable dynamic allocation**:
   ```python
   --conf spark.dynamicAllocation.enabled=true
   --conf spark.dynamicAllocation.minExecutors=1
   --conf spark.dynamicAllocation.maxExecutors=10
   ```

## Monitoring and Alerts

### CloudWatch Metrics

**Lambda metrics**:
- Duration
- Errors
- Throttles
- Concurrent executions

**EMR metrics**:
- Job duration
- Job failures
- Resource utilization

**Bedrock metrics**:
- Model invocations
- Throttling
- Errors

### Set Up Alerts

```bash
# Create SNS topic
aws sns create-topic --name spark-alerts

# Subscribe to topic
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:ACCOUNT:spark-alerts \
  --protocol email \
  --notification-endpoint your-email@example.com

# Create CloudWatch alarm
aws cloudwatch put-metric-alarm \
  --alarm-name spark-lambda-errors \
  --alarm-description "Alert on Lambda errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:ACCOUNT:spark-alerts
```

## Getting Help

1. **Check logs first**: Most issues are visible in CloudWatch logs
2. **Verify configuration**: Ensure all values match deployed resources
3. **Test components individually**: Isolate the failing component
4. **Check AWS service health**: https://status.aws.amazon.com/
5. **Review service quotas**: Ensure you haven't hit limits
6. **Consult documentation**: See DEPLOYMENT.md and CONFIGURATION.md

## Common Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `serviceUnavailableException` | Bedrock throttling | Wait or request quota increase |
| `ResourceNotFoundException` | Resource doesn't exist | Verify resource name/ARN |
| `AccessDeniedException` | IAM permissions | Check role policies |
| `TimeoutException` | Operation too slow | Increase timeout or optimize |
| `ValidationException` | Invalid parameters | Check parameter format |
| `ThrottlingException` | Rate limit exceeded | Implement backoff |

## Best Practices

1. **Always check logs first** - Most issues are logged
2. **Use CloudWatch Insights** - Query logs efficiently
3. **Monitor service quotas** - Prevent throttling
4. **Test in dev first** - Don't test in production
5. **Keep backups** - Backup configuration and data
6. **Document changes** - Track what you modify
7. **Use version control** - Track infrastructure changes
8. **Set up alerts** - Know when things break
9. **Regular updates** - Keep dependencies current
10. **Load test** - Know your limits before production
