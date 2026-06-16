# System Architecture

This document describes the architecture of the Spark Code Interpreter system.

## Overview

The Spark Code Interpreter is a serverless system that uses AWS Bedrock AgentCore to orchestrate Spark code generation and execution. It supports multiple data sources (S3, AWS Glue, PostgreSQL, Snowflake) and execution platforms (Lambda, EMR Serverless).

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         User/Client                              │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Application Load Balancer                       │
│                    (Internet-facing)                             │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Backend Lambda Function                       │
│                      (FastAPI Backend)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  • Request validation                                     │  │
│  │  • Session management                                     │  │
│  │  • Configuration loading                                  │  │
│  │  • Agent invocation                                       │  │
│  │  • Result retrieval                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Bedrock AgentCore Runtime                       │
│                                                                   │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         Spark Supervisor Agent                          │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  Tools:                                           │  │    │
│  │  │  • call_code_generation_agent()                   │  │    │
│  │  │  • validate_spark_code()                          │  │    │
│  │  │  • select_execution_platform()                    │  │    │
│  │  │  • execute_spark_code_lambda()                    │  │    │
│  │  │  • execute_spark_code_emr()                       │  │    │
│  │  │  • extract_execution_logs()                       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
│                             │                                     │
│                             ▼                                     │
│  ┌────────────────────────────────────────────────────────┐    │
│  │         Code Generation Agent                           │    │
│  │  ┌──────────────────────────────────────────────────┐  │    │
│  │  │  • Generates PySpark code                         │  │    │
│  │  │  • Intelligent column matching                    │  │    │
│  │  │  • Multi-source support                           │  │    │
│  │  │  • Optimization suggestions                       │  │    │
│  │  └──────────────────────────────────────────────────┘  │    │
│  └────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
┌──────────────────────────┐  ┌──────────────────────────┐
│   Lambda Execution       │  │   EMR Serverless         │
│   (Small datasets)       │  │   (Large datasets)       │
│                          │  │                          │
│  • Spark on Lambda       │  │  • Spark 3.x             │
│  • < 100MB data          │  │  • Auto-scaling          │
│  • 5 min timeout         │  │  • 10+ min jobs          │
│  • 3GB memory            │  │  • Custom resources      │
└──────────┬───────────────┘  └──────────┬───────────────┘
           │                             │
           └──────────────┬──────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Sources                              │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   S3 CSV     │  │  AWS Glue    │  │  PostgreSQL  │          │
│  │   Files      │  │  Catalog     │  │  Database    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                   │
│  ┌──────────────┐                                                │
│  │  Snowflake   │                                                │
│  │  (Optional)  │                                                │
│  └──────────────┘                                                │
└─────────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    S3 Results Bucket                             │
│                                                                   │
│  • Generated code                                                │
│  • Execution results                                             │
│  • Logs and metadata                                             │
│  • Lifecycle policies                                            │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Application Load Balancer (ALB)

**Purpose**: Entry point for all HTTP requests

**Features**:
- Internet-facing
- Health check monitoring
- SSL/TLS termination (optional)
- Request routing to backend Lambda

**Configuration**:
- Listener: Port 80 (HTTP) or 443 (HTTPS)
- Target: Backend Lambda function
- Health check: `/health` endpoint

### 2. Backend Lambda Function

**Purpose**: FastAPI application handling API requests

**Responsibilities**:
- Request validation and parsing
- Session management
- Configuration loading
- Agent invocation
- Result retrieval and formatting
- Error handling

**Key Endpoints**:
- `POST /spark/generate` - Generate and execute Spark code
- `GET /spark/result/{session_id}` - Retrieve execution results
- `GET /health` - Health check
- `POST /postgres/connections` - Manage PostgreSQL connections
- `GET /glue/databases` - List Glue databases

**Configuration**:
- Runtime: Python 3.11
- Memory: 512MB
- Timeout: 60 seconds
- Environment variables for configuration

### 3. Bedrock AgentCore Runtime

**Purpose**: Orchestration layer for AI agents

**Features**:
- Agent lifecycle management
- Tool execution
- Session management
- Streaming responses
- Error handling and retries

**Agents**:

#### Spark Supervisor Agent

**Role**: Orchestrates the entire Spark workflow

**Tools**:
1. `call_code_generation_agent()` - Invokes code generation agent
2. `validate_spark_code()` - Validates generated code
3. `select_execution_platform()` - Chooses Lambda or EMR
4. `execute_spark_code_lambda()` - Executes on Lambda
5. `execute_spark_code_emr()` - Executes on EMR
6. `extract_execution_logs()` - Retrieves execution logs

**Workflow**:
```
1. Receive user prompt
2. Call code generation agent
3. Validate generated code
4. Select execution platform
5. Execute code
6. Extract and return results
```

#### Code Generation Agent

**Role**: Generates PySpark code from natural language

**Features**:
- Intelligent column matching
- Multi-source support (S3, Glue, PostgreSQL, Snowflake)
- Optimization suggestions
- Error handling
- Security best practices

**Input**:
- User prompt
- Data source context
- Schema information
- Output path

**Output**:
- Executable PySpark code
- Comments and documentation

### 4. Execution Platforms

#### Lambda Execution

**Use Case**: Small datasets (< 100MB)

**Features**:
- Fast cold start (2-5 seconds)
- Cost-effective for small jobs
- 5-minute timeout
- 3GB memory

**Limitations**:
- Maximum 300-second execution
- Limited memory (3GB)
- No persistent storage

**Configuration**:
```python
FunctionName: dev-spark-on-lambda
Runtime: python3.11
MemorySize: 3008
Timeout: 300
```

#### EMR Serverless Execution

**Use Case**: Large datasets (> 100MB)

**Features**:
- Auto-scaling
- Custom resource allocation
- Longer execution time (10+ minutes)
- Persistent storage

**Limitations**:
- Slower cold start (2-3 minutes)
- Higher cost
- VPC configuration required

**Configuration**:
```python
ApplicationId: 00g1k848jaqqjf09
ReleaseLabel: emr-6.15.0
Type: Spark
MaximumCapacity:
  Cpu: 100 vCPU
  Memory: 200 GB
```

### 5. Data Sources

#### S3 CSV Files

**Access Method**: Direct S3 read

**Code Pattern**:
```python
df = spark.read.option("header", "true").csv("s3://bucket/path/file.csv")
```

**Requirements**:
- S3 bucket access
- IAM permissions

#### AWS Glue Catalog

**Access Method**: Spark table API

**Code Pattern**:
```python
spark = SparkSession.builder \
    .config("spark.sql.warehouse.dir", "s3://bucket/warehouse/") \
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \
    .enableHiveSupport() \
    .getOrCreate()

df = spark.table("database.table")
```

**Requirements**:
- Glue database and tables
- IAM permissions for Glue
- Hive support enabled

#### PostgreSQL Database

**Access Method**: JDBC connection

**Code Pattern**:
```python
spark = SparkSession.builder \
    .config("spark.jars", "s3://bucket/jars/postgresql-42.7.8.jar") \
    .getOrCreate()

df = spark.read.format("jdbc") \
    .option("url", "jdbc:postgresql://host:5432/dbname") \
    .option("dbtable", "schema.table") \
    .option("user", username) \
    .option("password", password) \
    .option("driver", "org.postgresql.Driver") \
    .load()
```

**Requirements**:
- JDBC driver in S3
- Network connectivity
- Credentials in Secrets Manager

#### Snowflake (Optional)

**Access Method**: JDBC connection

**Code Pattern**:
```python
spark = SparkSession.builder \
    .config("spark.jars", "s3://bucket/jars/snowflake-jdbc-3.14.4.jar") \
    .getOrCreate()

df = spark.read.format("jdbc") \
    .option("url", "jdbc:snowflake://account.snowflakecomputing.com") \
    .option("dbtable", "database.schema.table") \
    .option("user", username) \
    .option("password", password) \
    .option("driver", "net.snowflake.client.jdbc.SnowflakeDriver") \
    .load()
```

**Requirements**:
- Snowflake JDBC driver
- Snowflake account
- Credentials in Secrets Manager

### 6. Storage

#### S3 Results Bucket

**Purpose**: Store generated code, results, and logs

**Structure**:
```
s3://spark-data-ACCOUNT-us-east-1/
├── scripts/              # Generated Spark code
├── output/               # Execution results
├── logs/                 # Execution logs
│   ├── lambda/
│   └── emr/
└── jars/                 # JDBC drivers
    ├── postgresql-42.7.8.jar
    └── snowflake-jdbc-3.14.4.jar
```

**Lifecycle Policies**:
- Output files: 30 days retention
- Log files: 7 days retention
- Scripts: No expiration

## Data Flow

### Request Flow

1. **Client Request**:
   ```
   POST /spark/generate
   {
     "prompt": "analyze sales by month",
     "session_id": "abc123",
     "execution_platform": "auto",
     "s3_input_path": "s3://bucket/data.csv"
   }
   ```

2. **Backend Processing**:
   - Validate request
   - Load configuration
   - Create session
   - Invoke Spark Supervisor Agent

3. **Agent Orchestration**:
   - Supervisor calls Code Generation Agent
   - Code Generation Agent generates PySpark code
   - Supervisor validates code
   - Supervisor selects execution platform
   - Supervisor executes code

4. **Code Execution**:
   - Lambda or EMR executes Spark code
   - Reads from data sources
   - Processes data
   - Writes results to S3

5. **Result Retrieval**:
   - Supervisor extracts logs
   - Backend formats results
   - Returns to client

### Code Generation Flow

```
User Prompt
    │
    ▼
Code Generation Agent
    │
    ├─→ Parse prompt
    ├─→ Identify data sources
    ├─→ Match columns intelligently
    ├─→ Generate PySpark code
    └─→ Add error handling
    │
    ▼
Generated Code
    │
    ▼
Validation
    │
    ├─→ Check SparkSession creation
    ├─→ Verify data source access
    ├─→ Validate output path
    └─→ Check for security issues
    │
    ▼
Validated Code
```

### Execution Flow

```
Validated Code
    │
    ▼
Platform Selection
    │
    ├─→ Check file size
    ├─→ Check data source type
    └─→ Select Lambda or EMR
    │
    ▼
Execution
    │
    ├─→ Lambda (< 100MB)
    │   ├─→ Invoke function
    │   ├─→ Execute Spark code
    │   └─→ Write to S3
    │
    └─→ EMR (> 100MB)
        ├─→ Upload code to S3
        ├─→ Start job run
        ├─→ Monitor progress
        └─→ Write to S3
    │
    ▼
Results in S3
```

## Security Architecture

### IAM Roles and Permissions

#### Lambda Execution Role

**Permissions**:
- S3: Read/write to data bucket
- Glue: Read catalog metadata
- CloudWatch: Write logs

#### EMR Execution Role

**Permissions**:
- S3: Read/write to data bucket
- Glue: Read/write catalog metadata
- CloudWatch: Write logs

#### Backend Lambda Role

**Permissions**:
- Bedrock AgentCore: Invoke agents
- Lambda: Invoke Spark Lambda
- EMR: Start/monitor jobs
- S3: Read/write to data bucket
- CloudWatch: Write logs

#### AgentCore Runtime Role

**Permissions**:
- Bedrock: Invoke models
- Lambda: Invoke Spark Lambda
- EMR: Start/monitor jobs
- S3: Read/write to data bucket
- Glue: Read catalog metadata
- CloudWatch: Write logs

### Network Security

**VPC Configuration**:
- Private subnets for EMR
- Public subnets for ALB
- NAT Gateway for internet access
- Security groups for access control

**Security Groups**:
- ALB: Allow inbound 80/443 from internet
- Lambda: Allow outbound to AWS services
- EMR: Allow outbound to AWS services and data sources

### Data Security

**Encryption**:
- S3: Server-side encryption (SSE-S3)
- Secrets Manager: Encrypted at rest
- CloudWatch Logs: Encrypted

**Access Control**:
- IAM roles with least privilege
- S3 bucket policies
- VPC endpoints for private access

## Scalability

### Horizontal Scaling

**Lambda**:
- Concurrent executions: 1000 (default)
- Auto-scaling based on load
- No manual intervention

**EMR Serverless**:
- Auto-scaling workers
- Dynamic resource allocation
- Maximum capacity limits

**AgentCore**:
- Multiple concurrent sessions
- Automatic scaling
- Rate limiting

### Vertical Scaling

**Lambda**:
- Memory: 128MB - 3008MB
- CPU: Proportional to memory
- Timeout: Up to 300 seconds

**EMR**:
- Executor memory: Configurable
- Executor cores: Configurable
- Driver memory: Configurable

## Monitoring and Observability

### CloudWatch Metrics

**Lambda Metrics**:
- Invocations
- Duration
- Errors
- Throttles
- Concurrent executions

**EMR Metrics**:
- Job duration
- Job failures
- Resource utilization
- Data processed

**Bedrock Metrics**:
- Model invocations
- Throttling
- Errors
- Latency

### CloudWatch Logs

**Log Groups**:
- `/aws/lambda/dev-spark-supervisor-invocation` - Backend logs
- `/aws/lambda/dev-spark-on-lambda` - Spark execution logs
- `/aws/bedrock-agentcore/runtimes/spark_supervisor_agent-*/DEFAULT` - Agent logs
- `/aws/bedrock-agentcore/runtimes/code_generation_agent-*/DEFAULT` - Code gen logs

### CloudWatch Alarms

**Recommended Alarms**:
- Lambda errors > 5 in 5 minutes
- EMR job failures > 3 in 1 hour
- Bedrock throttling > 10 in 5 minutes
- S3 bucket size > 100GB

## Cost Optimization

### Lambda Costs

**Factors**:
- Invocations: $0.20 per 1M requests
- Duration: $0.0000166667 per GB-second
- Data transfer: $0.09 per GB (out)

**Optimization**:
- Use appropriate memory size
- Minimize execution time
- Use provisioned concurrency for predictable workloads

### EMR Costs

**Factors**:
- vCPU: $0.052 per vCPU-hour
- Memory: $0.0057 per GB-hour
- Storage: $0.08 per GB-month

**Optimization**:
- Use auto-stop (15 min idle timeout)
- Right-size worker resources
- Use spot instances (if available)

### Bedrock Costs

**Factors**:
- Model invocations: Model-specific pricing
- Input tokens: $0.003 per 1K tokens (Haiku)
- Output tokens: $0.015 per 1K tokens (Haiku)

**Optimization**:
- Use Haiku for simple tasks
- Minimize prompt size
- Cache results when possible

### S3 Costs

**Factors**:
- Storage: $0.023 per GB-month
- Requests: $0.0004 per 1K PUT requests
- Data transfer: $0.09 per GB (out)

**Optimization**:
- Use lifecycle policies
- Compress results
- Minimize data transfer

## High Availability

### Multi-AZ Deployment

**Components**:
- ALB: Deployed across multiple AZs
- Lambda: Automatically multi-AZ
- EMR: Subnet configuration for multiple AZs
- S3: Automatically replicated

### Disaster Recovery

**Backup Strategy**:
- S3: Versioning enabled
- Configuration: Version controlled in git
- Infrastructure: CloudFormation templates

**Recovery Procedures**:
1. Redeploy CloudFormation stack
2. Restore configuration from git
3. Redeploy agents
4. Verify functionality

## Performance Optimization

### Lambda Performance

**Optimizations**:
- Increase memory for more CPU
- Use provisioned concurrency
- Optimize Spark code
- Cache dependencies

### EMR Performance

**Optimizations**:
- Appropriate worker sizing
- Partition data effectively
- Use broadcast joins
- Enable dynamic allocation

### Agent Performance

**Optimizations**:
- Minimize prompt size
- Use streaming responses
- Cache code generation results
- Optimize tool execution

## Future Enhancements

### Planned Features

1. **Real-time Streaming**: Support for Spark Structured Streaming
2. **ML Integration**: Integration with SageMaker for ML workflows
3. **Query Optimization**: Automatic query optimization suggestions
4. **Cost Tracking**: Per-query cost tracking and reporting
5. **Multi-Region**: Support for multi-region deployments
6. **API Gateway**: Replace ALB with API Gateway for better API management
7. **Authentication**: Add JWT/OAuth authentication
8. **Rate Limiting**: Implement per-user rate limiting
9. **Caching**: Cache frequently used queries
10. **Monitoring Dashboard**: Custom CloudWatch dashboard

### Potential Improvements

1. **Performance**: Reduce cold start times
2. **Cost**: Optimize resource usage
3. **Security**: Add encryption in transit
4. **Scalability**: Support for larger datasets
5. **Usability**: Improve error messages
6. **Documentation**: Add more examples
7. **Testing**: Comprehensive test suite
8. **CI/CD**: Automated deployment pipeline
9. **Monitoring**: Enhanced observability
10. **Compliance**: Add audit logging
