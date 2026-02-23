# Configuration Reference

Complete reference for all configuration options in the Spark Code Interpreter system.

## Configuration Files

### 1. CloudFormation Parameters

**File**: `cloudformation/spark-complete-stack.yml`

```yaml
Parameters:
  Environment:
    Type: String
    Default: dev
    Description: Environment name (dev/prod)
  
  BedrockModel:
    Type: String
    Default: us.anthropic.claude-haiku-4-5-20251001-v1:0
    Description: Bedrock model ID for agents
  
  VpcId:
    Type: AWS::EC2::VPC::Id
    Description: VPC ID for EMR and Lambda
  
  PrivateSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Private subnet IDs for EMR (minimum 2)
  
  PublicSubnetIds:
    Type: List<AWS::EC2::Subnet::Id>
    Description: Public subnet IDs for ALB (minimum 2)
```

### 2. Backend Configuration

**File**: `backend/config_snowflake.py`

#### Global Settings

```python
"global": {
    "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0",
    "code_gen_agent_arn": "arn:aws:bedrock-agentcore:...",
    "bedrock_region": "us-east-1"
}
```

**Options**:
- `bedrock_model`: Bedrock model ID for agent invocations
- `code_gen_agent_arn`: ARN of code generation agent
- `bedrock_region`: AWS region for Bedrock service

#### Spark Settings

```python
"spark": {
    "s3_bucket": "spark-data-ACCOUNT-us-east-1",
    "lambda_function": "dev-spark-on-lambda",
    "emr_application_id": "00g1k848jaqqjf09",
    "emr_postgres_application_id": "00g1k848jaqqjf09",
    "max_retries": 3,
    "file_size_threshold_mb": 100,
    "result_preview_rows": 100,
    "presigned_url_expiry_hours": 24,
    "lambda_timeout_seconds": 300,
    "emr_timeout_minutes": 10,
    "supervisor_arn": "arn:aws:bedrock-agentcore:..."
}
```

**Options**:
- `s3_bucket`: S3 bucket for Spark data and results
- `lambda_function`: Lambda function name for Spark execution
- `emr_application_id`: EMR Serverless application ID for Glue/S3
- `emr_postgres_application_id`: EMR application ID for PostgreSQL
- `max_retries`: Maximum retry attempts for failed operations
- `file_size_threshold_mb`: File size threshold for Lambda vs EMR selection
- `result_preview_rows`: Number of rows to preview in results
- `presigned_url_expiry_hours`: Expiry time for S3 presigned URLs
- `lambda_timeout_seconds`: Lambda execution timeout (max 300)
- `emr_timeout_minutes`: EMR job timeout in minutes
- `supervisor_arn`: ARN of Spark supervisor agent

#### PostgreSQL Settings

```python
"postgres": {
    "connections": [],
    "default_connection": None,
    "jdbc_driver_path": "s3://bucket/jars/postgresql-42.7.8.jar",
    "secrets_manager_prefix": "spark/postgres/",
    "connection_timeout": 10,
    "query_timeout": 30,
    "use_dedicated_emr": True
}
```

**Options**:
- `connections`: List of PostgreSQL connection configurations
- `default_connection`: Default connection name to use
- `jdbc_driver_path`: S3 path to PostgreSQL JDBC driver JAR
- `secrets_manager_prefix`: Prefix for Secrets Manager secret names
- `connection_timeout`: Connection timeout in seconds
- `query_timeout`: Query timeout in seconds
- `use_dedicated_emr`: Use dedicated EMR application for PostgreSQL

**Connection Configuration**:
```python
{
    "name": "my-postgres",
    "host": "postgres.example.com",
    "port": 5432,
    "database": "mydb",
    "auth_method": "secrets_manager",  # or "iam" or "user_password"
    "secret_arn": "arn:aws:secretsmanager:...",
    "jdbc_url": "jdbc:postgresql://host:5432/dbname"
}
```

#### Snowflake Settings

```python
"snowflake": {
    "enabled": False,
    "secret_name": "",
    "jdbc_driver_path": "s3://bucket/jars/snowflake-jdbc-3.14.4.jar",
    "connection_timeout": 30,
    "query_timeout": 300,
    "use_dedicated_emr": False
}
```

**Options**:
- `enabled`: Enable Snowflake integration
- `secret_name`: Secrets Manager secret name for Snowflake credentials
- `jdbc_driver_path`: S3 path to Snowflake JDBC driver JAR
- `connection_timeout`: Connection timeout in seconds
- `query_timeout`: Query timeout in seconds
- `use_dedicated_emr`: Use dedicated EMR application for Snowflake

### 3. Agent Configuration

**File**: `agent-code/spark-supervisor-agent/.bedrock_agentcore.yaml`

```yaml
name: spark-supervisor-agent
runtime: python3.11
region: us-east-1
model_id: us.anthropic.claude-haiku-4-5-20251001-v1:0
timeout: 300
memory: 512
environment:
  AWS_REGION: us-east-1
```

**Options**:
- `name`: Agent name (must be unique)
- `runtime`: Python runtime version
- `region`: AWS region for deployment
- `model_id`: Bedrock model ID
- `timeout`: Agent timeout in seconds
- `memory`: Memory allocation in MB
- `environment`: Environment variables

### 4. Deployment Configuration

**File**: `config/deployment-config.json` (generated during deployment)

```json
{
  "account_id": "025523569182",
  "region": "us-east-1",
  "environment": "dev",
  "s3_bucket": "spark-data-025523569182-us-east-1",
  "lambda_function": "dev-spark-on-lambda",
  "emr_application_id": "00g1k848jaqqjf09",
  "emr_execution_role_arn": "arn:aws:iam::025523569182:role/dev-spark-emr-execution-role",
  "alb_url": "http://dev-spark-alb-123456789.us-east-1.elb.amazonaws.com",
  "bedrock_model": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
}
```

## Environment Variables

All configuration values can be overridden with environment variables:

### AWS Configuration

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=025523569182
export AWS_PROFILE=default  # Optional
```

### Bedrock Configuration

```bash
export BEDROCK_MODEL=us.anthropic.claude-haiku-4-5-20251001-v1:0
export CODE_GEN_AGENT_ARN=arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/...
export SPARK_SUPERVISOR_ARN=arn:aws:bedrock-agentcore:us-east-1:ACCOUNT:runtime/...
```

### Spark Configuration

```bash
export DATA_BUCKET=spark-data-ACCOUNT-us-east-1
export SPARK_LAMBDA_FUNCTION=dev-spark-on-lambda
export EMR_APPLICATION_ID=00g1k848jaqqjf09
export EMR_POSTGRES_APPLICATION_ID=00g1k848jaqqjf09
```

### PostgreSQL Configuration

```bash
export POSTGRES_JDBC_DRIVER=s3://bucket/jars/postgresql-42.7.8.jar
export POSTGRES_SECRET_ARN=arn:aws:secretsmanager:us-east-1:ACCOUNT:secret:NAME
```

### Snowflake Configuration

```bash
export SNOWFLAKE_ENABLED=true
export SNOWFLAKE_SECRET_NAME=snowflake-credentials
export SNOWFLAKE_JDBC_DRIVER=s3://bucket/jars/snowflake-jdbc-3.14.4.jar
```

## Configuration Precedence

Configuration values are loaded in this order (later overrides earlier):

1. **Default values** in `config_snowflake.py`
2. **Configuration file** (`settings.json`)
3. **Environment variables**
4. **Runtime parameters** (passed by backend)

## Updating Configuration

### Method 1: Edit Configuration File

```bash
cd backend
vi config_snowflake.py
# Make changes
# Redeploy backend
```

### Method 2: Use Environment Variables

```bash
export SPARK_LAMBDA_FUNCTION=new-function-name
# Restart backend
```

### Method 3: Use Update Script

```bash
cd scripts
./update-config.sh --lambda-function new-function-name
```

### Method 4: Update CloudFormation Stack

```bash
aws cloudformation update-stack \
  --stack-name dev-spark-complete-stack \
  --use-previous-template \
  --parameters ParameterKey=Environment,ParameterValue=prod
```

## Configuration Best Practices

1. **Use environment variables for secrets**: Never hardcode credentials
2. **Use CloudFormation parameters**: For infrastructure configuration
3. **Version control configuration**: Track changes in git
4. **Separate dev/prod configs**: Use different environments
5. **Document custom values**: Add comments for non-standard settings
6. **Test configuration changes**: In dev before prod
7. **Backup before changes**: Keep previous working configuration
8. **Use Secrets Manager**: For all sensitive data
9. **Validate after changes**: Run test suite
10. **Monitor after changes**: Watch CloudWatch logs

## Common Configuration Patterns

### Multi-Environment Setup

```python
# config_snowflake.py
import os

ENV = os.getenv('ENVIRONMENT', 'dev')

CONFIG = {
    'dev': {
        'lambda_function': 'dev-spark-on-lambda',
        'emr_application_id': 'dev-app-id'
    },
    'prod': {
        'lambda_function': 'prod-spark-on-lambda',
        'emr_application_id': 'prod-app-id'
    }
}

CURRENT_CONFIG = CONFIG[ENV]
```

### Dynamic Resource Discovery

```python
# Automatically discover resources
import boto3

def get_lambda_function():
    lambda_client = boto3.client('lambda')
    functions = lambda_client.list_functions()
    return next(f['FunctionName'] for f in functions['Functions'] 
                if 'spark-on-lambda' in f['FunctionName'])
```

### Configuration Validation

```python
def validate_config(config):
    required_keys = ['s3_bucket', 'lambda_function', 'emr_application_id']
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required config: {key}")
    return True
```

## Troubleshooting Configuration

### Check Current Configuration

```python
from backend.config_snowflake import load_config
config = load_config()
print(json.dumps(config, indent=2))
```

### Verify Resource Existence

```bash
# Check Lambda function
aws lambda get-function --function-name dev-spark-on-lambda

# Check EMR application
aws emr-serverless get-application --application-id APP_ID

# Check S3 bucket
aws s3 ls s3://spark-data-ACCOUNT-us-east-1/

# Check agent
aws bedrock-agentcore get-agent-runtime --agent-runtime-arn ARN
```

### Test Configuration

```bash
cd scripts
./test-deployment.sh
```

## Configuration Schema

For reference, here's the complete configuration schema:

```json
{
  "global": {
    "bedrock_model": "string",
    "code_gen_agent_arn": "string",
    "bedrock_region": "string"
  },
  "spark": {
    "s3_bucket": "string",
    "lambda_function": "string",
    "emr_application_id": "string",
    "emr_postgres_application_id": "string",
    "max_retries": "integer",
    "file_size_threshold_mb": "integer",
    "result_preview_rows": "integer",
    "presigned_url_expiry_hours": "integer",
    "lambda_timeout_seconds": "integer",
    "emr_timeout_minutes": "integer",
    "supervisor_arn": "string"
  },
  "postgres": {
    "connections": "array",
    "default_connection": "string",
    "jdbc_driver_path": "string",
    "secrets_manager_prefix": "string",
    "connection_timeout": "integer",
    "query_timeout": "integer",
    "use_dedicated_emr": "boolean"
  },
  "snowflake": {
    "enabled": "boolean",
    "secret_name": "string",
    "jdbc_driver_path": "string",
    "connection_timeout": "integer",
    "query_timeout": "integer",
    "use_dedicated_emr": "boolean"
  }
}
```

## Security Considerations

1. **Never commit secrets**: Use Secrets Manager or environment variables
2. **Restrict IAM permissions**: Follow least privilege principle
3. **Use VPC endpoints**: For private access to AWS services
4. **Enable encryption**: For S3 buckets and secrets
5. **Rotate credentials**: Regularly update passwords and keys
6. **Audit configuration**: Track who changes what
7. **Use HTTPS**: For all API endpoints
8. **Validate inputs**: Sanitize all user inputs
9. **Monitor access**: CloudWatch logs and CloudTrail
10. **Regular security reviews**: Audit configuration quarterly
