# Complete Changes Checklist

## Summary of All Changes Made

### 1. **Wrapper Lambda Created** ✅
**Purpose**: Accept natural language queries and invoke Spark Supervisor Agent

**File**: `agent-wrapper/agent_wrapper.py`

**Key Features**:
- Accepts natural language input (not PySpark code)
- Generates unique session IDs for each request
- Invokes Bedrock AgentCore agent via `invoke_agent_runtime`
- Passes complete configuration including model ID, S3 paths, and Spark config
- Returns results with session ID for tracking

**Configuration Passed**:
```python
{
    'model_id': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'bedrock_model': 'us.anthropic.claude-3-5-sonnet-20241022-v2:0',
    'bedrock_region': 'us-east-1',
    'lambda_function': 'dev-spark-on-lambda',
    's3_bucket': 'spark-data-{account}-{region}',
    's3_output_path': 's3://bucket/{session-id}/output/',
    'spark_config': {
        'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
        'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
    }
}
```

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - Deployed manually

---

### 2. **IAM Role for Wrapper Lambda** ✅
**Purpose**: Allow wrapper Lambda to invoke Bedrock AgentCore agents

**Required Permissions**:
- `bedrock-agentcore:InvokeAgentRuntime` - Invoke agents
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents` - CloudWatch logging
- `s3:GetObject`, `s3:PutObject`, `s3:ListBucket` - S3 access (optional, for direct S3 operations)

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - Using existing Spark Lambda role

---

### 3. **Gateway Permission for Wrapper Lambda** ✅
**Purpose**: Allow AgentCore Gateway to invoke the wrapper Lambda

**Resource-Based Policy**:
```json
{
  "Effect": "Allow",
  "Principal": {
    "Service": "bedrock-agentcore.amazonaws.com"
  },
  "Action": "lambda:InvokeFunction",
  "Resource": "arn:aws:lambda:region:account:function:dev-spark-agent-wrapper"
}
```

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - Added manually

---

### 4. **Lambda Timeout Increased** ✅
**Change**: 300 seconds → 900 seconds (15 minutes, AWS maximum)

**Reason**: 
- Agent processing takes 51-60 seconds
- Code generation + execution can take longer for complex queries
- Gateway has ~30 second timeout, but Lambda continues processing

**Affected Lambdas**:
- `dev-spark-agent-wrapper` - 900 seconds ✅
- `dev-spark-on-lambda` - 300 seconds (sufficient for execution only)

**Status**: 
- Wrapper: ⚠️ **NOT IN CLOUDFORMATION** - Updated manually
- Spark Lambda: ✅ **IN CLOUDFORMATION** - 300 seconds

---

### 5. **Model ID Configuration** ✅
**Model**: `us.anthropic.claude-3-5-sonnet-20241022-v2:0` (Claude 3.5 Sonnet v2)

**Where Used**:
- Wrapper Lambda payload to agent
- Agent configuration for code generation

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - Hardcoded in wrapper Lambda

---

### 6. **S3 Session-Based Structure** ✅
**Structure**:
```
s3://spark-data-{account}-{region}/
  └── {session-id}/
      ├── {session-id}_code.py      # Generated PySpark code
      └── output/                     # Execution results
          └── part-*.csv
```

**Implementation**:
- Wrapper Lambda generates UUID session ID
- Passes `s3_output_path` to agent: `s3://bucket/{session-id}/output/`
- Agent saves generated code to: `{session-id}/{session-id}_code.py`
- Spark Lambda writes results to: `{session-id}/output/`

**Status**: ✅ **IMPLEMENTED** - In wrapper Lambda code

---

### 7. **Spark S3 Configuration** ✅
**Purpose**: Fix "No FileSystem for scheme 's3'" error

**Configuration Added**:
```python
'spark_config': {
    'spark.hadoop.fs.s3a.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    'spark.hadoop.fs.s3.impl': 'org.apache.hadoop.fs.s3a.S3AFileSystem',
    'spark.hadoop.fs.s3a.aws.credentials.provider': 'com.amazonaws.auth.DefaultAWSCredentialsProviderChain'
}
```

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - In wrapper Lambda code

---

### 8. **Gateway Target Configuration** ✅
**Target Name**: `spark-agent`
**Target Type**: Lambda
**Lambda ARN**: `arn:aws:lambda:region:account:function:dev-spark-agent-wrapper`

**Tool Schema**:
```json
[
  {
    "name": "ask_agent",
    "description": "Ask Spark Supervisor Agent a natural language question about data processing",
    "inputSchema": {
      "type": "object",
      "properties": {
        "prompt": {
          "type": "string",
          "description": "Natural language query or question"
        }
      },
      "required": ["prompt"]
    }
  }
]
```

**Status**: ⚠️ **NOT IN CLOUDFORMATION** - Added manually via Console (CloudFormation Gateway Targets have complex schema issues)

---

### 9. **Cognito Authentication** ✅
**Configuration**:
- User Pool with email-based authentication
- App Client with client secret enabled
- OAuth2 client credentials flow support
- Custom scope: `spark-api/spark.execute`

**Authentication Flow**:
1. Get token: POST to Cognito token endpoint with client credentials
2. Calculate SECRET_HASH: `base64(HMAC-SHA256(username + client_id, client_secret))`
3. Use ID token (not access token) for Gateway authentication

**Status**: ✅ **IN CLOUDFORMATION**

---

### 10. **Gateway Configuration** ✅
**Type**: Native AWS `AWS::BedrockAgentCore::Gateway`
**Authorizer**: `CUSTOM_JWT` with Cognito
**Protocol**: `MCP` (Model Context Protocol)

**Status**: ✅ **IN CLOUDFORMATION**

---

## What's Missing from CloudFormation

### Critical Missing Resources:

1. **Wrapper Lambda Function** ❌
   - Function definition
   - IAM role with `bedrock-agentcore:InvokeAgentRuntime` permission
   - Environment variables (AGENT_ARN, S3_BUCKET, etc.)
   - Timeout: 900 seconds
   - Memory: 512 MB

2. **Wrapper Lambda Permission** ❌
   - Resource-based policy allowing Gateway to invoke

3. **Gateway Targets** ❌
   - Intentionally excluded due to CloudFormation schema complexity
   - Must be added manually via Console or API

4. **Deployment Package** ❌
   - Wrapper Lambda code needs to be packaged and uploaded
   - Could use inline code or S3 bucket for deployment

---

## CloudFormation Updates Needed

### 1. Add Wrapper Lambda IAM Role
```yaml
WrapperLambdaRole:
  Type: AWS::IAM::Role
  Properties:
    RoleName: !Sub '${Environment}-spark-wrapper-lambda-role'
    AssumeRolePolicyDocument:
      Version: '2012-10-17'
      Statement:
        - Effect: Allow
          Principal:
            Service: lambda.amazonaws.com
          Action: sts:AssumeRole
    ManagedPolicyArns:
      - arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
    Policies:
      - PolicyName: WrapperLambdaPolicy
        PolicyDocument:
          Version: '2012-10-17'
          Statement:
            - Effect: Allow
              Action:
                - bedrock-agentcore:InvokeAgentRuntime
              Resource: '*'
            - Effect: Allow
              Action:
                - s3:GetObject
                - s3:PutObject
                - s3:ListBucket
              Resource:
                - !GetAtt SparkDataBucket.Arn
                - !Sub '${SparkDataBucket.Arn}/*'
            - Effect: Allow
              Action:
                - logs:CreateLogGroup
                - logs:CreateLogStream
                - logs:PutLogEvents
              Resource: '*'
```

### 2. Add Wrapper Lambda Function
```yaml
SparkAgentWrapper:
  Type: AWS::Lambda::Function
  Properties:
    FunctionName: !Sub '${Environment}-spark-agent-wrapper'
    Runtime: python3.11
    Handler: index.lambda_handler
    Role: !GetAtt WrapperLambdaRole.Arn
    Timeout: 900
    MemorySize: 512
    Environment:
      Variables:
        AGENT_ARN: !Sub 'arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:runtime/spark_supervisor_agent-XXXXX'
        S3_BUCKET: !Ref SparkDataBucket
        SPARK_LAMBDA_ARN: !GetAtt SparkOnLambda.Arn
        CODE_GEN_ARN: !Sub 'arn:aws:bedrock-agentcore:${AWS::Region}:${AWS::AccountId}:runtime/ray_code_interpreter-XXXXX'
    Code:
      ZipFile: |
        # Inline code or reference to S3 bucket
        # See agent-wrapper/agent_wrapper.py for full code
```

### 3. Add Gateway Invoke Permission
```yaml
WrapperLambdaGatewayPermission:
  Type: AWS::Lambda::Permission
  Properties:
    FunctionName: !Ref SparkAgentWrapper
    Action: lambda:InvokeFunction
    Principal: bedrock-agentcore.amazonaws.com
    SourceArn: !GetAtt SparkAgentCoreGateway.GatewayArn
```

### 4. Update Gateway Role
Add permission to invoke wrapper Lambda:
```yaml
- Effect: Allow
  Action:
    - lambda:InvokeFunction
  Resource: !GetAtt SparkAgentWrapper.Arn
```

### 5. Add Outputs
```yaml
WrapperLambdaArn:
  Description: Wrapper Lambda function ARN
  Value: !GetAtt SparkAgentWrapper.Arn
  Export:
    Name: !Sub '${Environment}-WrapperLambdaArn'

WrapperLambdaName:
  Description: Wrapper Lambda function name
  Value: !Ref SparkAgentWrapper
  Export:
    Name: !Sub '${Environment}-WrapperLambdaName'
```

---

## Deployment Considerations

### Agent ARNs
The wrapper Lambda needs agent ARNs which are created separately:
- Spark Supervisor Agent ARN
- Code Generation Agent ARN

**Options**:
1. Use Parameters to pass ARNs during stack creation
2. Use SSM Parameter Store to store ARNs
3. Update Lambda environment variables after agent deployment

### Lambda Code Deployment
**Options**:
1. **Inline Code**: Embed Python code in CloudFormation (limited to 4096 characters)
2. **S3 Bucket**: Upload code to S3, reference in CloudFormation
3. **Separate Deployment**: Deploy Lambda separately after stack creation

**Recommended**: Use S3 bucket approach for production

### Gateway Targets
**Cannot be added via CloudFormation** due to complex schema validation.

**Manual Steps Required**:
1. Deploy CloudFormation stack
2. Add Gateway Target via Console or API
3. Configure tool schema

---

## Testing Checklist

After CloudFormation deployment:

- [ ] Verify Cognito User Pool created
- [ ] Verify Gateway created and accessible
- [ ] Verify Spark Lambda deployed
- [ ] Verify Wrapper Lambda deployed
- [ ] Verify IAM roles have correct permissions
- [ ] Verify S3 bucket created
- [ ] Test Cognito authentication
- [ ] Add Gateway Target manually
- [ ] Test Gateway → Wrapper Lambda → Agent flow
- [ ] Verify S3 session-based structure
- [ ] Verify Spark S3 writes work correctly

---

## Files Modified

1. `agent-wrapper/agent_wrapper.py` - Wrapper Lambda code
2. `scripts/deploy-agent-wrapper.sh` - Deployment script (timeout updated)
3. `cloudformation/spark-complete-stack.yml` - **NEEDS UPDATES**

---

## Next Steps

1. ✅ Review this checklist
2. ⏳ Update CloudFormation template with missing resources
3. ⏳ Test deployment in clean account
4. ⏳ Document manual Gateway Target configuration
5. ⏳ Create deployment guide for new accounts
