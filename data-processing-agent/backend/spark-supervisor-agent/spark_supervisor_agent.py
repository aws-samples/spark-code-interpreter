"""Spark Supervisor Agent - Orchestrates code generation, validation, and execution"""

import os
import json
import boto3
from typing import Union
from strands import Agent, tool
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

# Get region from boto3 session
session = boto3.Session()
AWS_REGION = session.region_name or 'us-east-1'

# Global session tracking
CURRENT_SESSION_ID = None

def load_spark_config():
    """Load Spark configuration - will be overridden by runtime config"""
    return {}

# Global config that will be set by the runtime
RUNTIME_CONFIG = None

def set_runtime_config(config):
    """Set runtime configuration passed from backend"""
    global RUNTIME_CONFIG
    RUNTIME_CONFIG = config

def get_config():
    """Get configuration - runtime config takes precedence"""
    if RUNTIME_CONFIG:
        return RUNTIME_CONFIG
    return load_spark_config()

@tool
def extract_python_code(text: str) -> str:
    """Extract Python code from markdown-formatted text
    
    Args:
        text: Text containing Python code in markdown format
    
    Returns:
        Extracted Python code without markdown markers
    """
    import re
    
    # Remove thinking tags
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    
    # Extract code from markdown blocks
    code_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Try without language specifier
    code_match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    
    # Return as-is if no markdown found
    return text.strip()

@tool
def call_code_generation_agent(prompt: str, session_id: str, s3_input_path: str = None, selected_tables: list = None, selected_postgres_tables: list = None, s3_output_path: str = None) -> str:
    """Call Code Generation Agent to generate Spark code"""
    import boto3
    
    agentcore_client = boto3.client(
        'bedrock-agentcore',
        region_name=AWS_REGION,
        config=boto3.session.Config(read_timeout=300, connect_timeout=60)
    )
    
    # Spark-specific system prompt with intelligent column matching
    spark_system_prompt = """You are a Spark code generation specialist with intelligent column matching capabilities.

Generate PySpark code for data analysis with automatic column name resolution.

CRITICAL - DO NOT SYNTHESIZE DATA:
- NEVER create sample data, synthetic data, or fake data in the code
- NEVER use createDataFrame with hardcoded values
- ALWAYS read from the actual data sources provided in the context
- If data sources are provided (S3, Glue, PostgreSQL), you MUST read from them
- Only generate sample data if the user explicitly requests it AND no data sources are provided
- ABSOLUTELY FORBIDDEN: Do NOT create fallback synthetic data "in case connection fails"
- ABSOLUTELY FORBIDDEN: Do NOT create sample data as a backup or alternative
- If PostgreSQL/Glue/S3 is in context, that is the ONLY data source - no alternatives allowed

INTELLIGENT COLUMN MATCHING:
- When user mentions column names that don't exactly match, find the closest matching column
- Use fuzzy matching, partial matching, and semantic understanding
- For example: "sales" could match "total_sales", "sales_amount", "monthly_sales"
- "date" could match "order_date", "created_at", "timestamp"
- "price" could match "unit_price", "total_price", "cost"
- NEVER error on column names - always find the best match and use it

DATA SOURCES:
- S3 files: Use spark.read.option("header", "true").csv(s3_path)
- Glue tables: Use spark.table("database.table") with Glue catalog configuration
- PostgreSQL tables: Use JDBC with credentials based on auth_method from context

CRITICAL - SPARK COLUMN OPERATIONS:
- NEVER use Python lists directly in Spark operations
- For filtering multiple values: Use col("column").isin([val1, val2, val3]) NOT col("column") == [val1, val2, val3]
- For array literals: Use array([lit(val1), lit(val2), lit(val3)]) NOT [val1, val2, val3]
- For column selection: Use df.select("col1", "col2") NOT df.select(["col1", "col2"])
- Always import required functions: from pyspark.sql.functions import col, lit, array, when, etc.

CRITICAL - GLUE CATALOG CONFIGURATION:
When the prompt mentions "Glue tables:" or contains table names, you MUST include these exact configurations:

spark = SparkSession.builder \\
    .appName("GlueQuery") \\
    .config("spark.sql.warehouse.dir", "ACTUAL_S3_BUCKET_FROM_CONTEXT") \\
    .config("spark.hadoop.hive.metastore.warehouse.dir", "ACTUAL_S3_BUCKET_FROM_CONTEXT") \\
    .config("hive.metastore.client.factory.class", 
            "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory") \\
    .enableHiveSupport() \\
    .getOrCreate()

Replace ACTUAL_S3_BUCKET_FROM_CONTEXT with the S3 bucket provided in the prompt context.
Example: If context says "S3 bucket for warehouse: s3://my-bucket/warehouse/", use that exact path.

THEN read from Glue table using: df = spark.table("database.table")

FORBIDDEN FOR GLUE TABLES:
- DO NOT use spark.read.csv() to read from table location directly
- DO NOT read from S3 paths when Glue tables are provided
- MUST use spark.table("database.table") to read from Glue catalog
- MUST include ALL 4 Glue configurations above (warehouse.dir, hadoop.hive.metastore.warehouse.dir, factory.class, enableHiveSupport)

WITHOUT these configurations, the code will fail with Derby metastore errors.

POSTGRESQL DATA SOURCES - MANDATORY INSTRUCTIONS:
When PostgreSQL tables are in context, you MUST use JDBC connection with exact values from context.

CRITICAL: DO NOT use environment variables, hardcoded values, or placeholders. Use ONLY the actual values provided in the context.

1. SPARK CONFIGURATION - Use exact JDBC driver path from context:
   spark = SparkSession.builder \\
       .appName("PostgreSQLQuery") \\
       .config("spark.jars", "ACTUAL_JDBC_DRIVER_PATH_FROM_CONTEXT") \\
       .getOrCreate()
   
   Example: If context shows "JDBC Driver: s3://bucket/jars/postgresql-42.7.8.jar"
   Then use: .config("spark.jars", "s3://bucket/jars/postgresql-42.7.8.jar")

2. GET CREDENTIALS - Use exact Secret ARN from context (NO environment variables):

   WRONG - NEVER DO THIS:
   username = os.environ.get('DB_USERNAME')  # FORBIDDEN
   password = os.environ.get('DB_PASSWORD')  # FORBIDDEN
   secret_arn = os.getenv('SECRET_ARN')      # FORBIDDEN
   
   CORRECT - ALWAYS DO THIS:

   A. If auth_method is 'secrets_manager':
      import boto3, json
      secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
      secret = secrets_client.get_secret_value(SecretId='ACTUAL_SECRET_ARN_FROM_CONTEXT')
      creds = json.loads(secret['SecretString'])
      username = creds['username']
      password = creds['password']
      
      Example: If context shows "Secret ARN: arn:aws:secretsmanager:us-east-1:123:secret:my-secret-abc123"
      Then use: SecretId='arn:aws:secretsmanager:us-east-1:123:secret:my-secret-abc123'
   
   B. If auth_method is 'iam':
      import boto3
      rds_client = boto3.client('rds', region_name='us-east-1')
      password = rds_client.generate_db_auth_token(
          DBHostname='ACTUAL_HOST_FROM_CONTEXT',
          Port=ACTUAL_PORT_FROM_CONTEXT,
          DBUsername='ACTUAL_USERNAME_FROM_CONTEXT',
          Region='us-east-1'
      )
      username = 'ACTUAL_USERNAME_FROM_CONTEXT'
      
      Example: If context shows "Host: mydb.rds.amazonaws.com" and "Port: 5432"
      Then use: DBHostname='mydb.rds.amazonaws.com', Port=5432
   
   C. If auth_method is 'user_password':
      import boto3, json
      secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
      secret = secrets_client.get_secret_value(SecretId='ACTUAL_SECRET_ARN_FROM_CONTEXT')
      creds = json.loads(secret['SecretString'])
      username = creds['username']
      password = creds['password']

3. READ FROM POSTGRESQL - Use exact JDBC URL from context:
   df = spark.read.format("jdbc") \\
       .option("url", "ACTUAL_JDBC_URL_FROM_CONTEXT") \\
       .option("dbtable", "schema.table") \\
       .option("user", username) \\
       .option("password", password) \\
       .option("driver", "org.postgresql.Driver") \\
       .load()
   
   Example: If context shows "JDBC URL: jdbc:postgresql://host:5432/dbname"
   Then use: .option("url", "jdbc:postgresql://host:5432/dbname")

4. PERFORMANCE OPTIMIZATION:
   - Use predicates for pushdown: .option("predicates", ["id > 1000"])
   - Partition reads: .option("partitionColumn", "id")
   - Fetch size: .option("fetchsize", "1000")

5. JOINING POSTGRESQL WITH OTHER SOURCES:
   - Read PostgreSQL table → Spark DataFrame
   - Read Glue/S3 → Spark DataFrame
   - Join in Spark: df1.join(df2, condition)

FORBIDDEN FOR POSTGRESQL:
- DO NOT use os.environ or os.getenv for any PostgreSQL values
- DO NOT use placeholder text like "YOUR_SECRET_ARN" or "REPLACE_WITH_ARN"
- DO NOT hardcode generic values - use the EXACT values from context
- The Secret ARN, JDBC URL, JDBC Driver path MUST match what's in the context exactly
- ALWAYS include JDBC driver in spark.jars configuration
- Use schema.table format for dbtable option
- Include error handling for connection failures
- Write results to S3 output path (never back to PostgreSQL)

REQUIREMENTS:
- Create SparkSession with appropriate config
- For Glue tables: Include ALL 4 configurations above (warehouse.dir, hadoop.hive.metastore.warehouse.dir, factory.class, enableHiveSupport)
- For PostgreSQL: Include JDBC driver in spark.jars and fetch credentials based on auth_method from context
- CRITICAL: Read data from ALL provided sources (S3, Glue, PostgreSQL) - NEVER synthesize or create fake data
- CRITICAL: If PostgreSQL tables are listed in context, you MUST read from them using JDBC - do NOT create sample data
- CRITICAL: If Glue tables are listed in context, you MUST read from them using spark.table() - do NOT create sample data
- CRITICAL: If S3 path is listed in context, you MUST read from it using spark.read.csv() - do NOT create sample data
- Automatically detect and use closest matching columns from the actual data
- Perform requested analysis using matched columns
- Write results to S3 path specified in "Write results to:" context (if provided) using .write.mode("overwrite").csv()
- Include error handling
- Show schema and sample data from actual sources
- Import all required Spark functions: from pyspark.sql.functions import col, lit, array, when, sum, count, etc.

FORBIDDEN:
- DO NOT use spark.createDataFrame() with hardcoded data when data sources are provided
- DO NOT generate synthetic data when actual data sources are available
- DO NOT create sample rows or fake data
- ABSOLUTELY FORBIDDEN: DO NOT use os.environ.get(), os.getenv(), or any environment variables for credentials
- ABSOLUTELY FORBIDDEN: DO NOT use placeholders like "YOUR_SECRET_ARN" or "REPLACE_WITH_VALUE"

COLUMN MATCHING EXAMPLES:
- User says "analyze sales by month" : find columns like "sales_amount", "total_sales" + "order_date", "month", "created_at"
- User says "group by category" : find columns like "product_category", "category_name", "type"
- User says "filter by price > 100" : find columns like "unit_price", "total_price", "amount"

COMMON SPARK PATTERNS:
- Filtering: df.filter(col("column_name") > value) or df.filter(col("column_name").isin([val1, val2]))
- Grouping: df.groupBy("column_name").agg(sum("other_column").alias("total"))
- Selecting: df.select("col1", "col2", col("col3").alias("new_name"))
- Creating arrays: df.withColumn("new_col", array(lit(val1), lit(val2)))

Return only executable Python code with intelligent column matching."""

    # Build context
    data_context = ""
    
    # S3 CSV files
    if s3_input_path:
        data_context += f"\nS3 CSV file: {s3_input_path}"
    
    # Glue tables
    if selected_tables:
        # Handle both string list and dict list formats
        if selected_tables and isinstance(selected_tables[0], dict):
            table_names = [f"{t['database']}.{t['table']}" for t in selected_tables]
            data_context += f"\nGlue tables: {', '.join(table_names)}"
            # Use location from first table for warehouse config
            if selected_tables[0].get('location'):
                data_context += f"\nS3 bucket for warehouse: {selected_tables[0]['location']}"
        else:
            data_context += f"\nGlue tables: {', '.join(selected_tables)}"
            # Extract S3 bucket for warehouse configuration
            if s3_output_path and s3_output_path.startswith('s3://'):
                bucket = s3_output_path.split('/')[2]
                data_context += f"\nS3 bucket for warehouse: s3://{bucket}/warehouse/"
    
    # PostgreSQL table handling
    if selected_postgres_tables:
        postgres_context = "\n\nPostgreSQL tables:\n"
        for pg_table in selected_postgres_tables:
            postgres_context += f"- Connection: {pg_table['connection_name']}\n"
            postgres_context += f"  {pg_table['database']}.{pg_table['schema']}.{pg_table['table']}\n"
            postgres_context += f"  JDBC URL: {pg_table['jdbc_url']}\n"
            postgres_context += f"  Auth Method: {pg_table.get('auth_method', 'secrets_manager')}\n"
            postgres_context += f"  Secret ARN: {pg_table['secret_arn']}\n"
            
            # Add host/port/username for IAM auth
            if pg_table.get('auth_method') == 'iam':
                postgres_context += f"  Host: {pg_table.get('host', '')}\n"
                postgres_context += f"  Port: {pg_table.get('port', 5432)}\n"
                # Username would be in the secret for IAM auth
            
            # Add columns if available (from fetch_postgres_table_schema or frontend)
            if 'columns' in pg_table and pg_table['columns']:
                columns_str = ', '.join([f"{c['name']} ({c['type']})" for c in pg_table['columns'][:5]])
                postgres_context += f"  Columns: {columns_str}\n"
        
        data_context += postgres_context
        
        # Add JDBC driver path (backend passes it at top level)
        config = get_config()
        jdbc_driver = config.get('jdbc_driver_path')
        if jdbc_driver:
            data_context += f"\nJDBC Driver: {jdbc_driver}\n"
    
    # Add output path to context
    if s3_output_path:
        data_context += f"\nWrite results to: {s3_output_path}"
    
    full_prompt = f"{prompt}{data_context}"
    
    # Get model ID from runtime config
    config = get_config()
    model_id = config.get('model_id') or config.get('bedrock_model')
    
    if not model_id:
        raise ValueError("❌ ERROR: No model_id found in runtime configuration. Please ensure model_id is set in the backend context.")
    
    print(f"🔍 DEBUG - Using model_id: {model_id}")
    print(f"🔍 DEBUG - Config bedrock_model: {config.get('bedrock_model')}")
    
    payload = {
        "prompt": full_prompt,
        "system_prompt": spark_system_prompt,
        "session_id": session_id,
        "model_id": model_id
    }
    
    # Get code generation agent ARN from runtime config
    config = get_config()
    code_gen_agent_arn = config.get('code_gen_agent_arn')
    
    try:
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=code_gen_agent_arn,
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Read streaming response
        if 'response' in response:
            code = response['response'].read().decode('utf-8')
            # Clean up code blocks
            if code.startswith('```python'):
                code = code[10:-3].strip()
            elif code.startswith('```'):
                code = code[3:-3].strip()
            return code
        else:
            return "CODE_GEN_ERROR: No response from code generation agent"
            
    except Exception as e:
        return f"CODE_GEN_ERROR: {str(e)}"

@tool
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """Intelligently select execution platform based on file size threshold
    
    Args:
        s3_input_path: S3 path to input file (optional, for size detection)
        file_size_mb: File size in MB if known
    
    Returns:
        Selected platform: 'lambda' or 'emr'
    """
    import boto3
    config = get_config()
    threshold = config.get('file_size_threshold_mb', 500)
    
    # If file size provided, use it
    if file_size_mb > 0:
        return 'emr' if file_size_mb > threshold else 'lambda'
    
    # Try to detect file size from S3 path
    if s3_input_path and s3_input_path.startswith('s3://'):
        try:
            s3_client = boto3.client('s3', region_name=config['bedrock_region'])
            bucket = s3_input_path.replace('s3://', '').split('/')[0]
            key = '/'.join(s3_input_path.replace('s3://', '').split('/')[1:])
            
            response = s3_client.head_object(Bucket=bucket, Key=key)
            size_mb = response['ContentLength'] / (1024 * 1024)
            return 'emr' if size_mb > threshold else 'lambda'
        except:
            pass
    
    # Default to lambda for unknown sizes
    return 'lambda'

@tool
def validate_spark_code(spark_code: str, s3_input_path: str = None, selected_tables: list = None) -> dict:
    """Validate Spark code for correctness and safety
    
    Args:
        spark_code: Generated Spark code to validate
        s3_input_path: S3 path for input data (if using S3)
        selected_tables: List of Glue tables (if using Glue)
    
    Returns:
        Validation result with status and errors
    """
    validation_errors = []
    is_glue = bool(selected_tables)
    
    # Basic validation
    if 'SparkSession' not in spark_code:
        validation_errors.append("Code must create a SparkSession")
    
    # Glue-specific validation
    if is_glue:
        if not any(f'spark.table(' in spark_code for table in (selected_tables or [])):
            validation_errors.append("Code should use spark.table() for Glue catalog")
        if 'enableHiveSupport()' not in spark_code:
            validation_errors.append("Must enable Hive support for Glue catalog")
    # S3-specific validation
    elif s3_input_path:
        if s3_input_path not in spark_code:
            validation_errors.append("Code should read from specified S3 path")
        if 'spark.read' not in spark_code:
            validation_errors.append("Code should use spark.read for S3 data")
    
    # Output validation - allow display-only operations
    has_display = any(x in spark_code for x in ['.show(', '.printSchema(', 'print('])
    if '.write' not in spark_code and not has_display:
        validation_errors.append("Code should write results to S3 or display data")
    
    return {
        'status': 'success' if not validation_errors else 'validation_failed',
        'validated': len(validation_errors) == 0,
        'validation_errors': validation_errors,
        'spark_code': spark_code
    }

@tool
def execute_spark_code_lambda(spark_code: str, s3_output_path: str) -> dict:
    """Execute validated Spark code on AWS Lambda
    
    Args:
        spark_code: Validated Spark code
        s3_output_path: S3 path for output
    
    Returns:
        Execution result from Lambda
    """
    import boto3
    from botocore.config import Config
    config = get_config()
    
    # Save validated code to S3 for backend retrieval
    global CURRENT_SESSION_ID
    if CURRENT_SESSION_ID and config.get('s3_bucket'):
        s3_client = boto3.client('s3', region_name=config['bedrock_region'])
        code_key = f"{CURRENT_SESSION_ID}/{CURRENT_SESSION_ID}_code.py"
        s3_client.put_object(
            Bucket=config['s3_bucket'],
            Key=code_key,
            Body=spark_code.encode('utf-8')
        )
    
    lambda_client = boto3.client(
        'lambda',
        region_name=config['bedrock_region'],
        config=Config(read_timeout=320, connect_timeout=10)
    )
    
    payload = {
        'spark_code': spark_code,
        's3_output_path': s3_output_path
    }
    
    response = lambda_client.invoke(
        FunctionName=config['lambda_function'],
        InvocationType='RequestResponse',
        Payload=json.dumps(payload)
    )
    
    result = json.loads(response['Payload'].read())
    lambda_status = 'success' if result.get('status') == 'success' else 'error'
    
    return {
        'status': lambda_status,
        'execution_platform': 'lambda',
        's3_output_path': s3_output_path,
        'result': result,
        'lambda_function': config['lambda_function']
    }

@tool
def execute_spark_code_emr(spark_code: str, s3_output_path: str) -> dict:
    """Execute validated Spark code on EMR Serverless
    
    Args:
        spark_code: Validated Spark code
        s3_output_path: S3 path for output
    
    Returns:
        Execution result from EMR
    """
    import boto3
    import time
    config = get_config()
    
    # Save validated code to S3 for backend retrieval
    global CURRENT_SESSION_ID
    if CURRENT_SESSION_ID and config.get('s3_bucket'):
        s3_client = boto3.client('s3', region_name=config['bedrock_region'])
        code_key = f"{CURRENT_SESSION_ID}/{CURRENT_SESSION_ID}_code.py"
        s3_client.put_object(
            Bucket=config['s3_bucket'],
            Key=code_key,
            Body=spark_code.encode('utf-8')
        )
    
    emr_client = boto3.client('emr-serverless', region_name=config['bedrock_region'])
    s3_client = boto3.client('s3', region_name=config['bedrock_region'])
    
    # Use EMR application ID provided by backend (already selected based on data source)
    # Backend passes emr_postgres_application_id for PostgreSQL, emr_application_id for Glue
    app_id = config.get('emr_postgres_application_id') or config.get('emr_application_id')
    
    # Use JDBC driver if provided by backend
    jdbc_driver = config.get('jdbc_driver_path', '')
    
    # Upload code to S3
    script_key = f"scripts/spark_script_{int(time.time())}.py"
    s3_client.put_object(
        Bucket=config['s3_bucket'],
        Key=script_key,
        Body=spark_code.encode('utf-8')
    )
    script_path = f"s3://{config['s3_bucket']}/{script_key}"
    
    # Build spark-submit parameters
    spark_params = '--conf spark.executor.memory=4g --conf spark.executor.cores=2'
    if jdbc_driver:
        spark_params += f' --jars {jdbc_driver}'
    
    # Start EMR job
    response = emr_client.start_job_run(
        applicationId=app_id,
        executionRoleArn=os.environ.get('EMR_EXECUTION_ROLE_ARN', 
            f"arn:aws:iam::{os.environ.get('AWS_ACCOUNT_ID', '260005718447')}:role/EMRServerlessExecutionRole"),
        jobDriver={
            'sparkSubmit': {
                'entryPoint': script_path,
                'sparkSubmitParameters': spark_params
            }
        },
        configurationOverrides={
            'monitoringConfiguration': {
                's3MonitoringConfiguration': {
                    'logUri': f"s3://{config['s3_bucket']}/logs/emr/"
                },
                'cloudWatchLoggingConfiguration': {
                    'enabled': True
                }
            }
        }
    )
    
    job_run_id = response['jobRunId']
    
    # Wait for job completion (with timeout)
    timeout = config['emr_timeout_minutes'] * 60
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        job_status = emr_client.get_job_run(
            applicationId=app_id,
            jobRunId=job_run_id
        )
        
        state = job_status['jobRun']['state']
        
        if state in ['SUCCESS', 'FAILED', 'CANCELLED']:
            return {
                'status': 'success' if state == 'SUCCESS' else 'error',
                'execution_platform': 'emr',
                's3_output_path': s3_output_path,
                'job_run_id': job_run_id,
                'job_state': state,
                'emr_application_id': app_id
            }
        
        time.sleep(10)
    
    return {
        'status': 'timeout',
        'execution_platform': 'emr',
        'job_run_id': job_run_id,
        'message': f'Job exceeded timeout of {config["emr_timeout_minutes"]} minutes'
    }

@tool
def extract_execution_logs(execution_result: Union[dict, str]) -> dict:
    """Extract execution results from Lambda or EMR CloudWatch logs including print statements
    
    Args:
        execution_result: Result from execute_spark_code containing platform and identifiers (dict or JSON string)
    
    Returns:
        Extracted log data with execution results and print statements
    """
    import boto3
    import time
    import json
    
    # Parse if string
    if isinstance(execution_result, str):
        try:
            execution_result = json.loads(execution_result.replace("'", '"'))
        except:
            execution_result = eval(execution_result)
    
    logs_client = boto3.client('logs', region_name=AWS_REGION)
    platform = execution_result.get('execution_platform')
    
    try:
        if platform == 'lambda':
            # Extract from Lambda logs
            function_name = execution_result.get('lambda_function', 'SparkExecutor')
            log_group = f'/aws/lambda/{function_name}'
            
            # Query recent logs
            end_time = int(time.time() * 1000)
            start_time = end_time - (5 * 60 * 1000)  # Last 5 minutes
            
            query = logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString='fields @message | sort @timestamp desc | limit 100',
                limit=100
            )
            
            query_id = query['queryId']
            time.sleep(2)
            
            result = logs_client.get_query_results(queryId=query_id)
            messages = [r[0]['value'] for r in result.get('results', []) if r]
            
            # Filter for execution output (exclude AWS internal logs and DataFrame .show() output)
            output_lines = [m for m in messages 
                           if not any(x in m for x in ['START RequestId', 'END RequestId', 'REPORT RequestId', 'INIT_START'])
                           and not ('+--' in m or (m.strip().startswith('|') and m.strip().endswith('|')))]
            
            return {
                'status': 'success',
                'platform': 'lambda',
                'log_messages': messages,
                'execution_output': output_lines,
                'rows_written': next((m for m in messages if 'rows written' in m.lower() or 'row(s)' in m.lower()), None)
            }
            
        elif platform == 'emr':
            # Extract from EMR logs - try S3 first, then CloudWatch
            job_run_id = execution_result.get('job_run_id')
            app_id = execution_result.get('emr_application_id')
            
            if not job_run_id or not app_id:
                return {'status': 'error', 'error': 'Missing EMR job identifiers'}
            
            # Try S3 logs first (more reliable for EMR Serverless)
            try:
                import gzip
                config = get_config()
                s3_client = boto3.client('s3', region_name=config['bedrock_region'])
                log_prefix = f"logs/emr/applications/{app_id}/jobs/{job_run_id}"
                
                response = s3_client.list_objects_v2(
                    Bucket=config['s3_bucket'],
                    Prefix=log_prefix
                )
                
                output_lines = []
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    # Focus on SPARK_DRIVER stdout and stderr logs
                    if ('SPARK_DRIVER' in key and ('stdout' in key or 'stderr' in key) and 
                        not key.endswith('_SUCCESS')):
                        
                        try:
                            log_obj = s3_client.get_object(Bucket=config['s3_bucket'], Key=key)
                            log_data = log_obj['Body'].read()
                            
                            # Handle gzipped files
                            if key.endswith('.gz'):
                                log_content = gzip.decompress(log_data).decode('utf-8')
                            else:
                                log_content = log_data.decode('utf-8')
                            
                            # Extract meaningful lines - exclude DataFrame .show() table formatting
                            lines = [line.strip() for line in log_content.split('\n') 
                                    if line.strip() and (
                                        'print(' in line.lower() or 
                                        'row(s)' in line.lower() or 
                                        'rows written' in line.lower() or
                                        'completed' in line.lower() or 
                                        'processing' in line.lower() or
                                        'analysis' in line.lower() or
                                        'result' in line.lower()
                                    ) and not (
                                        '+--' in line or  # Exclude DataFrame borders
                                        (line.startswith('|') and line.endswith('|') and '|' in line[1:-1])  # Exclude DataFrame rows
                                    )]
                            output_lines.extend(lines)
                        except Exception as file_error:
                            print(f"Error reading log file {key}: {file_error}")
                            continue
                
                if output_lines:
                    return {
                        'status': 'success',
                        'platform': 'emr',
                        'log_source': 's3',
                        'execution_output': output_lines[:50],
                        'log_messages': output_lines,
                        'job_run_id': job_run_id
                    }
            except Exception as s3_error:
                print(f"S3 log extraction failed: {s3_error}")
            
            # Fallback to CloudWatch logs
            log_group = f'/aws/emr-serverless/{app_id}'
            
            end_time = int(time.time() * 1000)
            start_time = end_time - (10 * 60 * 1000)
            
            query = logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=f'fields @message | filter @message like /{job_run_id}/ | sort @timestamp desc | limit 100',
                limit=100
            )
            
            query_id = query['queryId']
            time.sleep(3)
            
            result = logs_client.get_query_results(queryId=query_id)
            messages = [r[0]['value'] for r in result.get('results', []) if r]
            
            output_lines = [m for m in messages if any(x in m.lower() for x in ['stdout', 'print', 'row(s)', 'completed', 'written'])]
            
            return {
                'status': 'success',
                'platform': 'emr',
                'log_source': 'cloudwatch',
                'log_messages': messages,
                'execution_output': output_lines,
                'job_run_id': job_run_id
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'platform': platform
        }

@tool
def fetch_spark_results(s3_output_path: str, max_rows: int = None) -> dict:
    """Fetch results from S3 output path (CSV or Parquet)
    
    Args:
        s3_output_path: S3 path containing results
        max_rows: Maximum rows to return (default from config)
    
    Returns:
        Results data
    """
    import boto3
    import pandas as pd
    from io import StringIO, BytesIO
    from datetime import datetime, timezone, timedelta
    
    config = get_config()
    if max_rows is None:
        max_rows = config['result_preview_rows']
    
    try:
        s3_client = boto3.client('s3', region_name=config['bedrock_region'])
        bucket = s3_output_path.replace('s3://', '').split('/')[0]
        prefix = '/'.join(s3_output_path.replace('s3://', '').split('/')[1:])
        
        # List files modified in last 30 minutes (extended for EMR job time + table processing)
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        
        # Check for CSV files first (most common for Spark output)
        csv_files = [(obj['Key'], obj['LastModified']) for obj in response.get('Contents', []) 
                     if obj['Key'].endswith('.csv') and not obj['Key'].endswith('_SUCCESS')
                     and obj['LastModified'] > cutoff_time]
        
        # Also check for part files (common in distributed Spark output)
        part_files = [(obj['Key'], obj['LastModified']) for obj in response.get('Contents', []) 
                      if 'part-' in obj['Key'] and obj['Key'].endswith('.csv')
                      and obj['LastModified'] > cutoff_time]
        
        # Combine CSV and part files
        all_csv_files = csv_files + part_files
        
        # Fallback to Parquet files if no CSV found
        parquet_files = [(obj['Key'], obj['LastModified']) for obj in response.get('Contents', []) 
                         if obj['Key'].endswith('.parquet') and not obj['Key'].endswith('_SUCCESS')
                         and obj['LastModified'] > cutoff_time]
        
        if all_csv_files:
            # Process CSV file (prefer regular CSV over part files)
            regular_csv = [f for f in all_csv_files if not 'part-' in f[0]]
            files_to_process = regular_csv if regular_csv else all_csv_files
            files_to_process.sort(key=lambda x: x[1], reverse=True)
            most_recent_file = files_to_process[0][0]
            
            obj = s3_client.get_object(Bucket=bucket, Key=most_recent_file)
            csv_content = obj['Body'].read().decode('utf-8')
            
            # Detect headers
            lines = csv_content.strip().split('\n')
            if len(lines) > 1:
                first_row = lines[0].split(',')
                has_headers = any(not val.strip().replace('.', '').replace('-', '').isdigit() 
                                for val in first_row if val.strip())
            else:
                has_headers = False
            
            df = pd.read_csv(StringIO(csv_content)) if has_headers else pd.read_csv(StringIO(csv_content), header=None)
            file_format = 'csv'
            
        elif parquet_files:
            # Process Parquet file
            parquet_files.sort(key=lambda x: x[1], reverse=True)
            most_recent_file = parquet_files[0][0]
            
            obj = s3_client.get_object(Bucket=bucket, Key=most_recent_file)
            parquet_content = obj['Body'].read()
            df = pd.read_parquet(BytesIO(parquet_content))
            file_format = 'parquet'
            
        else:
            return {
                'status': 'success',
                'data': [],
                'row_count': 0,
                'message': 'No recent CSV or Parquet files found in output path'
            }
        
        # Generate presigned URL
        presigned_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': most_recent_file},
            ExpiresIn=config['presigned_url_expiry_hours'] * 3600
        )
        
        return {
            'status': 'success',
            'data': df.head(max_rows).to_dict('records'),
            'row_count': len(df),
            'preview_rows': max_rows,
            'total_files': len(all_csv_files) + len(parquet_files),
            'file_format': file_format,
            'presigned_url': presigned_url,
            's3_path': f"s3://{bucket}/{most_recent_file}"
        }
    except Exception as e:
        return {
            'status': 'error', 
            'error': str(e),
            'data': [],
            'row_count': 0
        }

@tool
def fetch_glue_table_schema(database_name: str, table_name: str) -> dict:
    """Fetch detailed schema for a Glue table
    
    Args:
        database_name: Glue database name
        table_name: Glue table name
    
    Returns:
        Table schema with columns, types, location, and partitions
    """
    import boto3
    
    try:
        glue_client = boto3.client('glue', region_name=AWS_REGION)
        response = glue_client.get_table(DatabaseName=database_name, Name=table_name)
        table = response['Table']
        
        storage_desc = table.get('StorageDescriptor', {})
        columns = [{'name': col['Name'], 'type': col['Type'], 'comment': col.get('Comment', '')} 
                   for col in storage_desc.get('Columns', [])]
        
        partition_keys = [{'name': pk['Name'], 'type': pk['Type']} 
                         for pk in table.get('PartitionKeys', [])]
        
        return {
            'status': 'success',
            'database': database_name,
            'table': table_name,
            'location': storage_desc.get('Location', ''),
            'input_format': storage_desc.get('InputFormat', ''),
            'output_format': storage_desc.get('OutputFormat', ''),
            'columns': columns,
            'partition_keys': partition_keys,
            'table_type': table.get('TableType', ''),
            'parameters': table.get('Parameters', {})
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'database': database_name,
            'table': table_name
        }

@tool
def fetch_postgres_table_schema(jdbc_url: str, secret_arn: str, database: str, schema: str, table: str) -> dict:
    """Fetch schema for a PostgreSQL table by querying information_schema
    
    Args:
        jdbc_url: PostgreSQL JDBC URL
        secret_arn: Secrets Manager ARN for credentials
        database: Database name
        schema: Schema name (e.g., 'public')
        table: Table name
    
    Returns:
        Table schema with columns and types
    """
    import boto3
    import json
    
    try:
        import psycopg2
    except ImportError:
        return {
            'status': 'error',
            'error': 'psycopg2 not installed',
            'database': database,
            'schema': schema,
            'table': table
        }
    
    try:
        # Get credentials from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        secret = secrets_client.get_secret_value(SecretId=secret_arn)
        creds = json.loads(secret['SecretString'])
        
        # Parse JDBC URL to get host and port
        # jdbc:postgresql://host:port/database
        jdbc_parts = jdbc_url.replace('jdbc:postgresql://', '').split('/')
        host_port = jdbc_parts[0].split(':')
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 5432
        
        # Connect and query schema
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=creds['username'],
            password=creds['password']
        )
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_schema = %s AND table_name = %s
            ORDER BY ordinal_position
        """, (schema, table))
        
        columns = [
            {
                'name': row[0],
                'type': row[1],
                'nullable': row[2] == 'YES'
            }
            for row in cursor.fetchall()
        ]
        
        cursor.close()
        conn.close()
        
        return {
            'status': 'success',
            'database': database,
            'schema': schema,
            'table': table,
            'columns': columns,
            'jdbc_url': jdbc_url
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'database': database,
            'schema': schema,
            'table': table
        }

def create_spark_supervisor_agent():
    """Create Spark supervisor agent that orchestrates the full workflow"""
    
    # Get model ID from runtime config, fallback to default
    config = get_config()
    model_id = config.get('model_id') or config.get('bedrock_model')
    
    if not model_id:
        raise ValueError("❌ ERROR: No model_id found in runtime configuration. Please ensure model_id is set in the backend context.")
    
    model = BedrockModel(
        model_id=model_id,
        max_tokens=8000
    )
    
    system_prompt = """You are a Spark code supervisor agent with iterative code refinement.

CRITICAL: Distinguish between two types of requests from backend:

1. GENERATE REQUEST (when skip_generation=False):
   - Generate new code, validate it, and execute it for validation
   - Retry on failures during generation/validation phase
   
2. EXECUTE REQUEST (when skip_generation=True):
   - Execute pre-validated code directly
   - NO retries, NO regeneration, NO validation

GENERATE REQUEST WORKFLOW (up to 3 attempts for generation/validation):

CRITICAL TOOL SELECTION - READ CAREFULLY:
- If "Selected tables: ['database.table']" is in context → Use fetch_glue_table_schema ONLY
- If "Selected PostgreSQL tables: ['table']" is in context → Use fetch_postgres_table_schema ONLY
- NEVER call both tools in the same request
- NEVER call fetch_postgres_table_schema when selected_postgres_tables is None or empty

VALIDATION EXECUTION PLATFORM SELECTION:
- ALWAYS start validation with Lambda (call execute_spark_code_lambda)
- If Lambda fails with resource/memory error: Switch to EMR for remaining validations in this session
- If Lambda fails with code error: Regenerate code and retry on Lambda
- Once switched to EMR, all subsequent validations in session use EMR

FOR GENERIC/CSV/NO-DATASOURCE REQUESTS (when both selected_tables and selected_postgres_tables are None):
1. Call call_code_generation_agent directly with the prompt (no schema fetching needed)
2. Call extract_python_code to clean the code - STORE this as your validated_code variable
3. Call validate_spark_code to check basic requirements
4. Call execute_spark_code_lambda for validation execution (or execute_spark_code_emr if already switched)
5. STOP AND WAIT - Check result.status (Lambda) or result.job_state (EMR)
6. IF execution succeeded:
   - Call extract_execution_logs(execution_result=<dict from step 4>)
   - Call fetch_spark_results to get output data
   - Return final JSON response with validated_code - DONE
7. IF execution failed:
   - Call extract_execution_logs to analyze error
   - IF error is Lambda resource issue AND currently using Lambda:
     * Switch to EMR for next attempt
     * Go back to step 4 with execute_spark_code_emr (do NOT regenerate code)
   - ELSE IF attempts < 3:
     * Go back to step 1 with error feedback to regenerate code

FOR GLUE TABLES (when selected_tables are provided AND selected_postgres_tables is None):
1. Call fetch_glue_table_schema for each table to get detailed schema
2. Call call_code_generation_agent to generate Spark code with table schemas
3. Call extract_python_code to clean the code - STORE this as your validated_code variable
4. Call validate_spark_code to check basic requirements
5. Call execute_spark_code_lambda for validation execution (or execute_spark_code_emr if already switched)
6. STOP AND WAIT - Check result.status (Lambda) or result.job_state (EMR)
   - Lambda SUCCESS: result.status == 'success'
   - EMR SUCCESS: result.job_state == 'SUCCESS'
   - Check for resource errors in logs (memory, timeout, capacity)
7. IF execution succeeded:
   - Call extract_execution_logs(execution_result=<dict from step 5>)
   - Call fetch_spark_results to get output data
   - Return final JSON response with validated_code - DONE
8. IF execution failed:
   - Call extract_execution_logs to analyze error
   - IF error is Lambda resource issue (memory/timeout/capacity) AND currently using Lambda:
     * Switch to EMR for next attempt
     * Go back to step 5 with execute_spark_code_emr (do NOT regenerate code)
   - ELSE IF attempts < 3:
     * Go back to step 2 with error feedback to regenerate code

FOR POSTGRESQL TABLES (when selected_postgres_tables are provided AND selected_tables is None):
1. Call fetch_postgres_table_schema for each table to get detailed schema
2. Call call_code_generation_agent to generate Spark code with table schemas
3. Call extract_python_code to clean the code - STORE this as your validated_code variable
4. Call validate_spark_code to check basic requirements
5. Call execute_spark_code_lambda for validation execution (or execute_spark_code_emr if already switched)
6. STOP AND WAIT - Check result.status (Lambda) or result.job_state (EMR)
   - Lambda SUCCESS: result.status == 'success'
   - EMR SUCCESS: result.job_state == 'SUCCESS'
   - Check for resource errors in logs (memory, timeout, capacity)
7. IF execution succeeded:
   - Call extract_execution_logs to get logs
   - Call fetch_spark_results to get output data
   - Return final JSON response with validated_code - DONE
8. IF execution failed:
   - Call extract_execution_logs to analyze error
   - IF error is Lambda resource issue (memory/timeout/capacity) AND currently using Lambda:
     * Switch to EMR for next attempt
     * Go back to step 5 with execute_spark_code_emr (do NOT regenerate code)
   - ELSE IF attempts < 3:
     * Go back to step 2 with error feedback to regenerate code

CRITICAL EXECUTION RULES:
- NEVER submit multiple EMR jobs concurrently
- ALWAYS wait for execute_spark_code_emr to return a result before proceeding
- Check result.job_state to determine success/failure
- ONLY retry if job_state == 'FAILED' and attempts < 3
- If job_state == 'SUCCESS', proceed to fetch results and return final response

EXECUTE REQUEST WORKFLOW (direct execution, no retries):
1. PLATFORM SELECTION: If execution_platform == 'auto':
   - Call select_execution_platform(s3_input_path, file_size_mb) to determine platform
   - Use returned platform ('lambda' or 'emr') for execution
   - Log: "Auto-selected execution platform: {platform}"
2. Call the appropriate execution tool ONCE based on platform:
   - If platform == 'lambda': Call execute_spark_code_lambda(spark_code, s3_output_path)
   - If platform == 'emr': Call execute_spark_code_emr(spark_code, s3_output_path)
   - This is the final execution
3. Check execution status (no retries):
   - Lambda: Check if result.status == 'success'
   - EMR: Check if result.job_state == 'SUCCESS'
4. MANDATORY FINAL STEPS:
   - Call extract_execution_logs(execution_result=<dict from step 2>) - pass the dict object, not string
   - Call fetch_spark_results to get output data (ALWAYS REQUIRED)
   - Return final JSON response with the ORIGINAL provided spark_code (preserve it exactly)

CRITICAL ERROR HANDLING FOR GENERATE REQUESTS:
- TypeError with Python lists: Fix Spark operations (use col().isin([]), array([lit()]), etc.)
- Derby metastore errors: Ensure Glue catalog configuration is included
- Column not found errors: Use intelligent column matching
- Permission errors: Check S3 paths and IAM roles
- Timeout errors: Optimize query or increase timeout

GLUE TABLE HANDLING:
- When selected_tables are provided in context, fetch schema for each table using fetch_glue_table_schema
- Pass the complete schema information AND S3 bucket location to call_code_generation_agent
- Generated code MUST include Glue catalog configuration (warehouse.dir, factory.class)
- Example: spark.sql("SELECT * FROM database.table WHERE condition")

CRITICAL CODE GENERATION RULE:
- Generated Spark code MUST write final results to S3 using df.write.csv() or df.coalesce(1).write.csv()
- Use the s3_output_path provided in the context
- Code can display data with .show() for logging, but MUST also write to S3
- This ensures results appear in the formatted Outputs section

CRITICAL SUCCESS DETERMINATION:
- For Lambda execution: Check if result.status == 'success'
- For EMR execution: Check if result.job_state == 'SUCCESS' 
- Set execution_result to "success" only if above conditions are met, otherwise "failed"

MANDATORY FETCH RULE - CRITICAL FOR OUTPUT SECTION:
- ALWAYS call fetch_spark_results with the ACTUAL S3 path where the code writes results
- This is REQUIRED for the formatted response in the Output section of Execution result
- Extract the output path from the generated Spark code using this logic:
  1. Search for .write.csv() or .write.parquet() calls in the validated spark_code
  2. Extract the S3 path from the write operation (look for s3:// URLs in quotes)
  3. Use that extracted path as s3_output_path parameter
- If code writes to a subdirectory (e.g., s3://bucket/output/subdir/), use that full path
- If no S3 write path found in code, fall back to base s3_output_path from execute_spark_code result
- This applies to both Lambda and EMR executions, success or failure
- Extract the 'data' field from fetch_spark_results response for actual_results
- If fetch_spark_results returns error or no data field, use empty list []
- WITHOUT calling fetch_spark_results, the Output section will be empty/missing

TOOL CALL LIMIT MANAGEMENT:
- Limit retries to 3 attempts maximum to preserve tool calls for mandatory fetch step
- If hitting tool limits, skip optional log extraction and prioritize fetch_spark_results call
- The fetch_spark_results call is MORE IMPORTANT than extract_execution_logs

PATH EXTRACTION EXAMPLES:
Code: top_10_df.write.csv("s3://bucket/output/top_10_closing/")
Extract: "s3://bucket/output/top_10_closing/"
Call: fetch_spark_results(s3_output_path="s3://bucket/output/top_10_closing/")

Code: .write.mode("overwrite").csv(output_path) where output_path = "s3://bucket/results/"
Extract: "s3://bucket/results/"
Call: fetch_spark_results(s3_output_path="s3://bucket/results/")

CRITICAL CODE PRESERVATION:
- ALWAYS preserve the actual generated Spark code throughout the entire process
- When call_code_generation_agent returns code, store it as the validated_code
- When extract_python_code cleans the code, use that cleaned version as validated_code
- NEVER use placeholder text like "# [Full code as generated - see execution above]"
- The spark_code field in the final JSON MUST contain the complete, actual Python code

CRITICAL: Your final response MUST be a valid JSON object with these exact fields:
- spark_code: The COMPLETE ACTUAL validated Spark code (never use placeholders or comments like "Full code as generated")
- execution_result: "success" or "failed" (based on platform-specific success logic above)
- execution_message: Summary of execution including log details and print output
- execution_output: Array of print statements and output lines from execution_output field
- actual_results: List of data records from fetch_spark_results (always populated, may be empty)
- s3_output_path: S3 path where results are stored

EXAMPLE - ALWAYS include the COMPLETE actual code:
```json
{
  "spark_code": "from pyspark.sql import SparkSession\nfrom pyspark.sql.functions import col, sum, count\n\nspark = SparkSession.builder.appName('Analysis').getOrCreate()\ndf = spark.read.csv('s3://bucket/data.csv', header=True)\nresult = df.groupBy('region').agg(count('*').alias('total'))\nresult.write.mode('overwrite').csv('s3://bucket/output/')\nspark.stop()",
  "execution_result": "success",
  "execution_message": "EMR job completed successfully. Job state: SUCCESS",
  "execution_output": ["Processing data...", "100 rows written"],
  "actual_results": [{"col1": "value1", "col2": "value2"}],
  "s3_output_path": "s3://bucket/output/session-id"
}
```"""
    
    agent = Agent(
        model=model,
        system_prompt=system_prompt,
        tools=[select_execution_platform, fetch_glue_table_schema, call_code_generation_agent, extract_python_code, validate_spark_code, execute_spark_code_lambda, execute_spark_code_emr, extract_execution_logs, fetch_spark_results],
        name="SparkSupervisorAgent"
    )
    
    return agent

@app.entrypoint
def invoke(payload):
    """Main entrypoint for Spark Supervisor Agent"""
    import json
    import re
    global CURRENT_SESSION_ID
    
    # Set runtime configuration if provided
    config = payload.get("config")
    if config:
        set_runtime_config(config)
        print(f"✅ Runtime configuration set: {list(config.keys())}")
    
    agent = create_spark_supervisor_agent()
    
    # Extract parameters
    prompt = payload.get("prompt", "")
    spark_code = payload.get("spark_code")
    skip_generation = payload.get("skip_generation", False)
    session_id = payload.get("session_id", "")
    CURRENT_SESSION_ID = session_id
    s3_input_path = payload.get("s3_input_path")
    s3_output_path = payload.get("s3_output_path")
    selected_tables = payload.get("selected_tables")
    selected_postgres_tables = payload.get("selected_postgres_tables")
    execution_platform = payload.get("execution_platform", "lambda")
    
    # Build context for agent
    if skip_generation and spark_code:
        # Execution-only mode - code is already validated
        context = f"""The Spark code is already validated and ready for execution:

```python
{spark_code}
```

EXECUTE-ONLY MODE: Skip code generation and validation steps.

Execute the code:
- If execution_platform == 'auto': Call select_execution_platform(s3_input_path={s3_input_path or 'None'}, file_size_mb=0) to determine platform
- Otherwise use execution_platform: {execution_platform}
- Call the appropriate execution tool:
  * If platform == 'lambda': Call execute_spark_code_lambda(spark_code, s3_output_path)
  * If platform == 'emr': Call execute_spark_code_emr(spark_code, s3_output_path)
- Output path: {s3_output_path}
- Session ID: {session_id}

Then call extract_execution_logs, fetch_spark_results, and return the JSON response.

DO NOT retry or regenerate code in execute-only mode."""
    else:
        # Full generation + execution mode
        data_sources = []
        
        if s3_input_path:
            data_sources.append(f"S3 CSV file: {s3_input_path}")
        
        if selected_tables:
            tables_info = f"Glue tables: {selected_tables}"
            data_sources.append(tables_info)
            data_sources.append("Fetch schema for each table using fetch_glue_table_schema before generating code.")
        
        if selected_postgres_tables:
            postgres_info = f"PostgreSQL tables: {selected_postgres_tables}"
            data_sources.append(postgres_info)
        
        # CRITICAL: Only allow sample data if NO real data sources provided
        if data_sources:
            data_source = "\n".join(data_sources)
        else:
            data_source = "Generate sample data"
        
        context = f"""User request: {prompt}

Data source: {data_source}
Output path: {s3_output_path}
Selected tables: {selected_tables or 'None'}
Selected PostgreSQL tables: {selected_postgres_tables or 'None'}
Session ID: {session_id}

GENERATE MODE: Generate code, validate it, and execute for validation.

CRITICAL VALIDATION PLATFORM SELECTION:
- ALWAYS start validation with Lambda (call execute_spark_code_lambda)
- If Lambda fails with resource error: Switch to EMR (call execute_spark_code_emr) and stay on EMR
- If Lambda fails with code error: Regenerate code and retry on Lambda
- For code execution (not validation), user selects platform separately

Generate Spark code, validate it, execute it for validation, and return results."""
    
    try:
        # Run agent
        response = agent(context)
        response_text = str(response)
        
        # Initialize variables
        validated_code = None
        execution_status = "success"
        execution_message = ""
        execution_output = []
        actual_results = []
        
        # Try to parse JSON format first
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                result = json.loads(json_match.group(1))
                validated_code = result.get("spark_code")
                execution_status = result.get("execution_result", "success")
                execution_message = result.get("execution_message", "")
                execution_output = result.get("execution_output", [])
                actual_results = result.get("actual_results", [])
            except:
                pass
        
        # Fall back to old VALIDATED_CODE/EXECUTION_RESULT format
        if not validated_code and "VALIDATED_CODE:" in response_text:
            code_start = response_text.find("```python")
            code_end = response_text.find("```", code_start + 9)
            if code_start != -1 and code_end != -1:
                validated_code = response_text[code_start + 9:code_end].strip()
        
        if not execution_message and "EXECUTION_RESULT:" in response_text:
            result_start = response_text.find("EXECUTION_RESULT:") + 17
            execution_message = response_text[result_start:].strip()
        
        # Map to expected backend format
        return json.dumps({
            "spark_code": validated_code,
            "execution_result": execution_status,
            "execution_message": execution_message,
            "execution_output": execution_output,
            "actual_results": actual_results,
            "s3_output_path": s3_output_path
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({
            "spark_code": None,
            "execution_result": f"Error: {str(e)}",
            "execution_output": [],
            "actual_results": [],
            "s3_output_path": s3_output_path
        })

if __name__ == "__main__":
    app.run()

if __name__ == "__main__":
    app.run()
