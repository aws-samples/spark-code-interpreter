# CloudFormation Stack Updates - Complete

## Summary

All changes have been incorporated into the CloudFormation stack (`cloudformation/spark-complete-stack.yml`). The stack is now ready for deployment in new AWS accounts.

## What Was Added to CloudFormation

### 1. **New Parameters** ✅

```yaml
SparkSupervisorAgentArn:
  Type: String
  Description: ARN of the Spark Supervisor Agent (deployed separately)
  Default: ''

CodeGenerationAgentArn:
  Type: String
  Description: ARN of the Code Generation Agent (deployed separately)
  Default: ''

BedrockModel:
  Type: String
  Default: us.anthropic.claude-3-5-sonnet-20241022-v2:0
  Description: Bedrock model ID (updated to Claude 3.5 Sonnet v2)
```

### 2. **Wrapper Lambda IAM Role** ✅

```yaml
WrapperLambdaRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub '${Environment}-spark-wrapper-lambda-role'
    Policies:
      - PolicyName: WrapperLambdaPolicy
        PolicyDocument:
          Statement:
            - Effect: Allow
              Action:
                - bedrock-agentcore:InvokeAgentRuntime  # Key permission
              Resource: '*'
            - Effect: Allow
              Action:
                - s3:GetObject
                - s3:PutObject
                - s3:ListBucket
              Resource:
                - !GetAtt SparkDataBucket.Arn
                - !Sub '${SparkDataBucket.Arn}/*'
```

### 3. **Wrapper Lambda Function** ✅

```yaml
SparkAgentWrapper:
  Type: AWS::Lambda::Function
  Properties:
    FunctionName: !Sub '${Environment}-spark-agent-wrapper'
    Runtime: python3.11
    Handler: index.lambda_handler
    Role: !GetAtt WrapperLambdaRole.Arn
    Timeout: 900  # 15 minutes (AWS maximum)
    MemorySize: 512
    Environment:
      Variables:
        AGENT_ARN: !Ref SparkSupervisorAgentArn
        S3_BUCKET: !Ref SparkDataBucket
        SPARK_LAMBDA_ARN: !GetAtt SparkOnLambda.Arn
        CODE_GEN_ARN: !Ref CodeGenerationAgentArn
        BEDROCK_MODEL: !Ref BedrockModel
    Code:
      ZipFile: |
        # Inline Python code with all features:
        # - Natural language input
        # - Session ID generation
        # - S3 session-based paths
        # - Spark S3 configuration
        # - Model ID configuration
```

**Key Features in Code**:
- Accepts natural language queries (not PySpark code)
- Generates UUID session IDs
- Configures S3 paths: `s3://bucket/{session-id}/output/`
- Passes Spark S3 configuration:
  ```python
  'spark_config': {
      'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
      'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
      'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
  }
  ```

### 4. **Gateway Permission for Wrapper Lambda** ✅

```yaml
WrapperLambdaGatewayPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref SparkAgentWrapper
    Action: lambda:InvokeFunction
    Principal: bedrock-agentcore.amazonaws.com
    SourceArn: !GetAtt SparkAgentCoreGateway.GatewayArn
```

### 5. **Updated Gateway Role** ✅

Added permission to invoke wrapper Lambda:

```yaml
- Effect: Allow
  Action:
    - lambda:InvokeFunction
  Resource:
    - !GetAtt SparkOnLambda.Arn
    - !GetAtt SparkAgentWrapper.Arn  # Added
```

### 6. **New Outputs** ✅

```yaml
WrapperLambdaFunctionName:
  Description: Wrapper Lambda function name
  Value: !Ref SparkAgentWrapper

WrapperLambdaFunctionArn:
  Description: Wrapper Lambda function ARN
  Value: !GetAtt SparkAgentWrapper.Arn

GatewayTargetInstructions:
  Description: Instructions for adding Gateway Target (must be done manually)
  Value: !Sub |
    Gateway Targets cannot be added via CloudFormation...
    [Complete instructions included]
```

## What's Still Manual

### Gateway Targets ⚠️

**Why**: CloudFormation Gateway Target schema is complex and error-prone. Multiple validation errors occur with different property configurations.

**Solution**: Add manually after stack deployment via:
1. AWS Console (recommended)
2. AWS CLI
3. AWS SDK

**Documentation**: See `GATEWAY_TARGET_CONFIG.md` and `DEPLOYMENT_GUIDE.md`

## Complete Feature List

### ✅ Included in CloudFormation

1. **Cognito User Pool** - JWT authentication
2. **Cognito App Client** - OAuth2 with client secret
3. **AgentCore Gateway** - MCP protocol with JWT auth
4. **Gateway IAM Role** - Permissions for Gateway
5. **Wrapper Lambda** - Natural language → Agent invocation
6. **Wrapper Lambda IAM Role** - Bedrock AgentCore permissions
7. **Wrapper Lambda Permission** - Gateway invoke permission
8. **Spark Lambda** - PySpark execution (Docker image)
9. **Spark Lambda IAM Role** - S3 and Glue permissions
10. **S3 Bucket** - Session-based data storage
11. **EMR Serverless** - Alternative execution platform
12. **EMR IAM Role** - Execution permissions
13. **AgentCore Runtime Role** - Agent execution permissions
14. **All Outputs** - ARNs, URLs, and configuration values

### ⚠️ Manual Steps Required

1. **Deploy Agents First** - Get ARNs before stack deployment
2. **Build Docker Image** - Spark Lambda container
3. **Push to ECR** - Container registry
4. **Add Gateway Target** - After stack deployment
5. **Create Cognito Users** - Optional, for user auth

## Deployment Flow

```
1. Deploy Agents (Python scripts)
   ↓
2. Build & Push Docker Image
   ↓
3. Deploy CloudFormation Stack (with Agent ARNs)
   ↓
4. Add Gateway Target (Manual)
   ↓
5. Test End-to-End
```

## Configuration Highlights

### Model ID
- **Default**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- **Configurable**: Via CloudFormation parameter

### Lambda Timeouts
- **Wrapper Lambda**: 900 seconds (15 minutes, AWS maximum)
- **Spark Lambda**: 300 seconds (5 minutes, sufficient for execution)

### S3 Structure
```
s3://spark-data-{account}-{region}/
  └── {session-id}/
      ├── {session-id}_code.py      # Generated code
      └── output/                     # Results
          └── part-*.csv
```

### Spark Configuration
Automatically configured for S3 access:
- S3A filesystem implementation
- AWS credentials provider chain
- Hadoop S3 libraries (already in Docker image)

## Testing the Stack

### Quick Test

```bash
# Deploy stack
aws cloudformation create-stack \
  --stack-name dev-spark-complete-stack \
  --template-body file://cloudformation/spark-complete-stack.yml \
  --parameters ... \
  --capabilities CAPABILITY_NAMED_IAM

# Wait for completion
aws cloudformation wait stack-create-complete \
  --stack-name dev-spark-complete-stack

# Add Gateway Target (manual)
# See DEPLOYMENT_GUIDE.md

# Test wrapper Lambda
aws lambda invoke \
  --function-name dev-spark-agent-wrapper \
  --payload '{"prompt":"calculate 10 + 20"}' \
  /tmp/test.json

# Check results
cat /tmp/test.json | jq '.'
```

## Files Updated

1. ✅ `cloudformation/spark-complete-stack.yml` - Complete stack with all resources
2. ✅ `COMPLETE_CHANGES_CHECKLIST.md` - Detailed change list
3. ✅ `DEPLOYMENT_GUIDE.md` - Step-by-step deployment instructions
4. ✅ `CLOUDFORMATION_UPDATES_COMPLETE.md` - This file

## Files for Reference

- `agent-wrapper/agent_wrapper.py` - Full wrapper Lambda code (for updates)
- `scripts/deploy-agent-wrapper.sh` - Deployment script (for manual deployment)
- `GATEWAY_TARGET_CONFIG.md` - Gateway Target schema
- `S3_WRITE_FIX.md` - S3 configuration details
- `WHY_NO_CLOUDFORMATION_TARGETS.md` - Explanation of manual Gateway Targets

## Validation

The CloudFormation template has been updated with:
- ✅ All IAM roles and permissions
- ✅ All Lambda functions
- ✅ All environment variables
- ✅ Correct timeouts (900s for wrapper)
- ✅ Model ID configuration
- ✅ S3 session-based structure
- ✅ Spark S3 configuration
- ✅ Gateway permissions
- ✅ Complete outputs
- ✅ Deployment instructions

## Known Limitations

1. **Gateway Timeout**: ~30 seconds (not configurable)
   - **Impact**: Gateway may timeout, but Lambda continues
   - **Solution**: Check S3 for results or invoke Lambda directly

2. **Bedrock Throttling**: May occur with high request volume
   - **Impact**: `modelStreamErrorException` errors
   - **Solution**: Wait and retry, or request quota increase

3. **Gateway Targets**: Cannot be added via CloudFormation
   - **Impact**: Manual step required after deployment
   - **Solution**: Use Console or CLI (documented)

## Success Criteria

After deployment, you should have:
- ✅ Cognito User Pool with JWT authentication
- ✅ AgentCore Gateway with MCP support
- ✅ Wrapper Lambda accepting natural language
- ✅ Spark Lambda executing PySpark code
- ✅ S3 bucket with session-based structure
- ✅ All IAM roles and permissions configured
- ✅ Gateway Target configured (manual step)
- ✅ End-to-end flow working

## Next Steps

1. Deploy in test account using `DEPLOYMENT_GUIDE.md`
2. Verify all resources created correctly
3. Test end-to-end flow
4. Document any account-specific configurations
5. Create CI/CD pipeline for updates

---

**Status**: ✅ **COMPLETE** - CloudFormation stack is ready for deployment in new accounts
