"""Spark Supervisor Agent - Orchestrates code generation, validation, and execution

Tools are split into:
- MCP tools: External operations delegated to individual Lambda functions
- Local tools: Pure logic kept in this file (no external calls)
"""

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

# Environment prefix for MCP tool Lambda names — derived from runtime config
ENVIRONMENT = os.environ.get('ENVIRONMENT', '')


def _get_environment():
    """Get environment prefix from config or env var."""
    if ENVIRONMENT:
        return ENVIRONMENT
    config = get_config()
    # Derive from lambda_function name: "dev-spark-on-lambda" → "dev"
    lambda_fn = config.get('lambda_function', '')
    if lambda_fn and '-spark-' in lambda_fn:
        return lambda_fn.split('-spark-')[0]
    return 'dev'


def _invoke_mcp_tool(function_name: str, payload: dict) -> dict:
    """Invoke an MCP tool Lambda directly (hot path — low latency)."""
    from botocore.config import Config

    lambda_client = boto3.client(
        'lambda',
        region_name=AWS_REGION,
        config=Config(read_timeout=900, connect_timeout=10),
    )
    response = lambda_client.invoke(
        FunctionName=function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps(payload),
    )
    result = json.loads(response['Payload'].read())
    if 'body' in result:
        return json.loads(result['body']) if isinstance(result['body'], str) else result['body']
    return result


def _invoke_mcp_via_gateway(tool_name: str, params: dict) -> dict:
    """Call an MCP tool via the internal AgentCore Gateway with IAM auth (cold path).

    Used for infrequent operations: EMR execution, Glue schema, PostgreSQL schema.
    """
    import urllib.request
    import urllib.error
    from botocore.auth import SigV4Auth
    from botocore.awsrequest import AWSRequest

    config = get_config()
    gateway_url = config.get('internal_gateway_url', '')
    
    print(f"🔍 _invoke_mcp_via_gateway: tool={tool_name}")
    print(f"🔍 gateway_url={gateway_url[:80] if gateway_url else 'EMPTY'}")
    
    if not gateway_url:
        print("❌ internal_gateway_url not set in config")
        print(f"🔍 Config keys: {list(config.keys())}")
        return {'status': 'error', 'error': 'internal_gateway_url not set in config'}

    body = json.dumps({
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": tool_name, "arguments": params},
        "id": 1,
    })

    aws_request = AWSRequest(
        method='POST',
        url=gateway_url,
        data=body,
        headers={'Content-Type': 'application/json'},
    )

    session = boto3.Session()
    credentials = session.get_credentials()
    if credentials:
        frozen = credentials.get_frozen_credentials()
        print(f"🔍 Credentials: access_key={frozen.access_key[:8]}..., has_token={bool(frozen.token)}")
        SigV4Auth(frozen, 'bedrock-agentcore', AWS_REGION).add_auth(aws_request)
    else:
        print("❌ No credentials available")
        return {'status': 'error', 'error': 'No AWS credentials available in runtime'}

    req = urllib.request.Request(
        aws_request.url,
        data=body.encode('utf-8'),
        headers=dict(aws_request.headers),
        method='POST',
    )

    try:
        resp = urllib.request.urlopen(req, timeout=900)
        result = json.loads(resp.read().decode('utf-8'))
        print(f"✅ Gateway call succeeded for {tool_name}")
        # MCP response: {"jsonrpc": "2.0", "result": {"content": [...]}, "id": 1}
        if 'result' in result:
            content = result['result'].get('content', [])
            if content and isinstance(content[0], dict) and 'text' in content[0]:
                return json.loads(content[0]['text'])
            return result['result']
        if 'error' in result:
            return {'status': 'error', 'error': result['error'].get('message', str(result['error']))}
        return result
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8') if e.fp else str(e)
        print(f"❌ Gateway HTTP {e.code}: {error_body[:200]}")
        return {'status': 'error', 'error': f"Gateway HTTP {e.code}: {error_body[:500]}"}
    except Exception as e:
        print(f"❌ Gateway call failed: {str(e)}")
        return {'status': 'error', 'error': f"Gateway call failed: {str(e)}"}

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
    """Call Code Generation Agent directly on AgentCore Runtime to generate Spark code"""
    config = get_config()

    code_gen_agent_arn = config.get('code_gen_agent_arn')
    if not code_gen_agent_arn:
        return "CODE_GEN_ERROR: code_gen_agent_arn not set in config"

    model_id = config.get('model_id') or config.get('bedrock_model')
    if not model_id:
        return "CODE_GEN_ERROR: model_id not set in config"

    # Build data context
    data_context = ""
    if s3_input_path:
        data_context += f"\nS3 CSV file: {s3_input_path}"
    if selected_tables:
        if isinstance(selected_tables[0], dict):
            table_names = [f"{t['database']}.{t['table']}" for t in selected_tables]
            data_context += f"\nGlue tables: {', '.join(table_names)}"
            if selected_tables[0].get('location'):
                data_context += f"\nS3 bucket for warehouse: {selected_tables[0]['location']}"
        else:
            data_context += f"\nGlue tables: {', '.join(selected_tables)}"
    if selected_postgres_tables:
        pg_ctx = "\n\nPostgreSQL tables:\n"
        for pg in selected_postgres_tables:
            pg_ctx += f"- {pg.get('database','')}.{pg.get('schema','')}.{pg.get('table','')}\n"
            pg_ctx += f"  JDBC URL: {pg.get('jdbc_url','')}\n"
            pg_ctx += f"  Auth Method: {pg.get('auth_method','secrets_manager')}\n"
            pg_ctx += f"  Secret ARN: {pg.get('secret_arn','')}\n"
        data_context += pg_ctx
        jdbc_driver = config.get('jdbc_driver_path')
        if jdbc_driver:
            data_context += f"\nJDBC Driver: {jdbc_driver}\n"
    if s3_output_path:
        data_context += f"\nWrite results to: {s3_output_path}"

    full_prompt = f"{prompt}{data_context}"

    payload = {
        'prompt': full_prompt,
        'session_id': session_id,
        'model_id': model_id,
    }

    try:
        agentcore_client = boto3.client(
            'bedrock-agentcore',
            region_name=config.get('region', AWS_REGION),
            config=boto3.session.Config(read_timeout=300, connect_timeout=60),
        )

        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=code_gen_agent_arn,
            runtimeSessionId=session_id,
            qualifier='DEFAULT',
            payload=json.dumps(payload),
        )

        if 'response' in response:
            code = response['response'].read().decode('utf-8')
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
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0, selected_tables: list = None) -> str:
    """Intelligently select execution platform based on data source and size.
    
    Args:
        s3_input_path: S3 path to input file (optional, for size detection)
        file_size_mb: File size in MB if known
        selected_tables: List of Glue table dicts (always routes to EMR)
    
    Returns:
        Selected platform: 'lambda' or 'emr'
    """
    import boto3
    config = get_config()
    threshold = config.get('file_size_threshold_mb', 500)
    
    # Glue tables ALWAYS go to EMR (Lambda doesn't have Glue catalog support)
    if selected_tables:
        return 'emr'
    
    # If file size provided, use it
    if file_size_mb > 0:
        return 'emr' if file_size_mb > threshold else 'lambda'
    
    # Try to detect file size from S3 path
    if s3_input_path and s3_input_path.startswith('s3://'):
        try:
            s3_client = boto3.client('s3', region_name=config.get('bedrock_region', AWS_REGION))
            bucket = s3_input_path.replace('s3://', '').split('/')[0]
            key = '/'.join(s3_input_path.replace('s3://', '').split('/')[1:])
            
            response = s3_client.head_object(Bucket=bucket, Key=key)
            size_mb = response['ContentLength'] / (1024 * 1024)
            return 'emr' if size_mb > threshold else 'lambda'
        except:
            pass
    
    # Default to lambda for unknown sizes (CSV queries, calculations)
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
    
    # CRITICAL: Output file validation
    if '/tmp/output.json' not in spark_code:
        validation_errors.append("Code must write results to /tmp/output.json (MANDATORY for Lambda execution)")
    
    if 'import json' not in spark_code and '/tmp/output.json' in spark_code:
        validation_errors.append("Code must import json module to write output file")
    
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
    if '.write' not in spark_code and not has_display and '/tmp/output.json' not in spark_code:
        validation_errors.append("Code should write results to S3, display data, or write output file")
    
    return {
        'status': 'success' if not validation_errors else 'validation_failed',
        'validated': len(validation_errors) == 0,
        'validation_errors': validation_errors,
        'spark_code': spark_code
    }

@tool
def ensure_output_file_writing(spark_code: str, s3_output_path: str = None) -> str:
    """Ensure generated Spark code writes /tmp/output.json (Safety net)
    
    This is a fallback tool that injects output file writing if the code generation
    agent forgot to include it. Ideally, the agent should generate correct code,
    but this provides a safety net.
    
    Args:
        spark_code: Generated Spark code
        s3_output_path: S3 output path (optional)
    
    Returns:
        Modified code with output file writing guaranteed
    """
    import re
    
    # Check if code already writes output.json
    if '/tmp/output.json' in spark_code:
        return spark_code  # Already has output writing
    
    print("⚠️ WARNING: Generated code missing /tmp/output.json - injecting safety net")
    
    # Ensure json import exists
    if 'import json' not in spark_code:
        # Add after other imports
        lines = spark_code.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        lines.insert(import_index, 'import json')
        spark_code = '\n'.join(lines)
    
    # Find where to inject output code (before spark.stop())
    if 'spark.stop()' in spark_code:
        # Inject before spark.stop()
        output_code = '''
# SAFETY NET: Write output to JSON file (required by Lambda handler)
output = {
    "status": "success",
    "message": "Execution completed. Check logs for results."
}
with open('/tmp/output.json', 'w') as f:
    json.dump(output, f)

'''
        spark_code = spark_code.replace('spark.stop()', output_code + 'spark.stop()')
    else:
        # Append at end
        output_code = '''
# SAFETY NET: Write output to JSON file (required by Lambda handler)
output = {
    "status": "success",
    "message": "Execution completed. Check logs for results."
}
with open('/tmp/output.json', 'w') as f:
    json.dump(output, f)
'''
        spark_code += '\n' + output_code
    
    return spark_code

@tool
def execute_spark_code_lambda(spark_code: str, s3_output_path: str) -> dict:
    """Execute validated Spark code on AWS Lambda via MCP tool Lambda"""
    config = get_config()
    return _invoke_mcp_tool(f"{_get_environment()}-spark-tool-execute-spark-on-lambda", {
        'spark_code': spark_code,
        's3_output_path': s3_output_path,
        'lambda_function': config.get('lambda_function', ''),
        's3_bucket': config.get('s3_bucket', ''),
        'session_id': CURRENT_SESSION_ID or '',
        'spark_config': config.get('spark_config', {}),
        'region': config.get('bedrock_region', AWS_REGION),
    })

@tool
def execute_spark_code_emr(spark_code: str, s3_output_path: str) -> dict:
    """Execute validated Spark code on EMR Serverless via Gateway MCP"""
    config = get_config()
    return _invoke_mcp_via_gateway("execute-spark-on-emr___execute_spark_on_emr", {
        'spark_code': spark_code,
        's3_output_path': s3_output_path,
        's3_bucket': config.get('s3_bucket', ''),
        'session_id': CURRENT_SESSION_ID or '',
        'emr_application_id': config.get('emr_postgres_application_id') or config.get('emr_application_id', ''),
        'emr_execution_role_arn': config.get('emr_execution_role_arn', ''),
        'emr_timeout_minutes': config.get('emr_timeout_minutes', 15),
        'jdbc_driver_path': config.get('jdbc_driver_path', ''),
        'region': config.get('bedrock_region', AWS_REGION),
    })

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
    """Fetch Spark execution results from S3 output path via MCP tool Lambda"""
    config = get_config()
    return _invoke_mcp_tool(f"{_get_environment()}-spark-tool-fetch-spark-results", {
        's3_output_path': s3_output_path,
        's3_bucket': config.get('s3_bucket', ''),
        'session_id': CURRENT_SESSION_ID or '',
        'max_rows': max_rows or config.get('result_preview_rows', 100),
        'presigned_url_expiry_hours': config.get('presigned_url_expiry_hours', 24),
        'region': config.get('bedrock_region', AWS_REGION),
    })

@tool
def fetch_glue_table_schema(database_name: str, table_name: str) -> dict:
    """Fetch detailed schema for a Glue table via Gateway MCP. Also extracts a 200-row sample CSV for validation."""
    config = get_config()
    return _invoke_mcp_via_gateway("get-glue-table-schema___get_glue_table_schema", {
        'database_name': database_name,
        'table_name': table_name,
        's3_bucket': config.get('s3_bucket', ''),
        'session_id': CURRENT_SESSION_ID or '',
        'region': AWS_REGION,
    })

@tool
def fetch_postgres_table_schema(jdbc_url: str, secret_arn: str, database: str, schema: str, table: str) -> dict:
    """Fetch schema for a PostgreSQL table via Gateway MCP"""
    return _invoke_mcp_via_gateway("get-postgres-table-schema___get_postgres_table_schema", {
        'jdbc_url': jdbc_url,
        'secret_arn': secret_arn,
        'database': database,
        'schema': schema,
        'table': table,
        'region': AWS_REGION,
    })


def create_spark_supervisor_agent():
    """Create Spark supervisor agent that orchestrates the full workflow"""
    
    # Get model ID from runtime config, fallback to default
    config = get_config()
    model_id = config.get('model_id') or config.get('bedrock_model')
    
    # Use Claude Sonnet 4.5 as default if not provided
    if not model_id:
        model_id = 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
        print(f"ℹ️  No model_id provided, using default: {model_id}")
    
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

GLUE TABLE DETECTION FROM PROMPT:
- If the user prompt mentions a table in "database.table" or "database_name.table_name" format
  (e.g., "spark_test_db.sample_sales", "my_db.orders")
  AND "Selected tables:" is NOT in context (i.e., selected_tables is None):
  → Extract the database name and table name from the prompt
  → Call fetch_glue_table_schema(database_name="...", table_name="...")
  → Use the returned schema to generate code with proper Glue catalog configuration
  → Then call select_execution_platform with selected_tables to determine platform (will route to EMR)
- This enables Glue table queries via MCP Gateway or CLI without requiring UI table selection
- If fetch_glue_table_schema returns an error, inform the user the table was not found

VALIDATION EXECUTION PLATFORM SELECTION:
- ALWAYS start validation with Lambda (call execute_spark_code_lambda)
- If Lambda fails with resource/memory error: Switch to EMR for remaining validations in this session
- If Lambda fails with code error: Regenerate code and retry on Lambda
- Once switched to EMR, all subsequent validations in session use EMR

FOR GENERIC/CSV/NO-DATASOURCE REQUESTS (when both selected_tables and selected_postgres_tables are None):

IF s3_sample_path IS PROVIDED (2-phase execution for CSV files):
  PHASE 1 - FAST VALIDATION (using sample, on Lambda):
  1. Call call_code_generation_agent with the prompt, using s3_sample_path as the data source
  2. Call extract_python_code to clean the code
  3. Call validate_spark_code to check basic requirements
  4. Call execute_spark_code_lambda for fast validation (~10s with 200 rows)
  5. IF validation succeeds → code logic is correct, proceed to Phase 2
  6. IF validation fails with code error → regenerate (up to 3 attempts)

  PHASE 2 - PRODUCTION EXECUTION (using full file, right platform):
  7. Rewrite the validated code: replace s3_sample_path with s3_input_path (full file)
  8. Call select_execution_platform(s3_input_path) to determine Lambda vs EMR
  9. Execute on the selected platform (Lambda for <500MB, EMR for >500MB)
  10. Call extract_execution_logs and fetch_spark_results
  11. Return final JSON response with the PRODUCTION code (using full path)

IF s3_sample_path IS NOT PROVIDED (direct execution):
  1. Call call_code_generation_agent directly with the prompt
  2. Call extract_python_code to clean the code
  3. Call validate_spark_code to check basic requirements
  4. Call execute_spark_code_lambda for execution
  5. IF execution succeeded:
     - Call extract_execution_logs and fetch_spark_results
     - Return final JSON response - DONE
  6. IF execution failed:
     - IF Lambda resource issue → switch to EMR
     - ELSE IF attempts < 3 → regenerate code

FOR GLUE TABLES (when selected_tables are provided AND selected_postgres_tables is None):
1. Call fetch_glue_table_schema for each table to get detailed schema AND sample_s3_path
2. VALIDATION PHASE: Generate code using spark.read.csv(sample_s3_path) to validate logic on Lambda
   - The sample_s3_path contains 200 rows extracted from the Glue table
   - Use spark.read.option("header", "true").option("inferSchema", "true").csv(sample_s3_path)
   - This avoids Glue catalog dependency on Lambda
3. Call extract_python_code to clean the code
4. Call validate_spark_code to check basic requirements
5. Call execute_spark_code_lambda for validation with sample data
6. IF validation succeeds:
   - PRODUCTION PHASE: Rewrite the validated code to use spark.table("database.table")
   - Add Glue catalog configuration (warehouse.dir, factory.class, enableHiveSupport)
   - Call execute_spark_code_emr for production execution with full data
7. Call extract_execution_logs and fetch_spark_results
8. Return final JSON response

IMPORTANT FOR GLUE VALIDATION:
- During validation (step 2-5): Use spark.read.csv(sample_s3_path) — works on Lambda
- During production (step 6): Use spark.table("database.table") with Glue config — works on EMR
- The sample_s3_path is returned by fetch_glue_table_schema in the response
- If sample_s3_path is not available, skip validation and go directly to EMR

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
        tools=[select_execution_platform, fetch_glue_table_schema, call_code_generation_agent, extract_python_code, validate_spark_code, ensure_output_file_writing, execute_spark_code_lambda, execute_spark_code_emr, extract_execution_logs, fetch_spark_results],
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
    s3_sample_path = payload.get("s3_sample_path")
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
            data_sources.append(f"S3 CSV file (full): {s3_input_path}")
            if s3_sample_path:
                data_sources.append(f"S3 CSV sample (200 rows): {s3_sample_path}")
                data_sources.append("USE THE SAMPLE PATH for validation (fast). USE THE FULL PATH for production execution.")
        
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
