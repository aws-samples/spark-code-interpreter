"""Spark Supervisor Agent - Orchestrates code generation, validation, and execution

Architecture: Strands GraphBuilder multi-agent system.

Agents (GraphBuilder nodes):
  generate_and_validate_agent - Node 1: generates PySpark code and validates on Lambda using sample CSV
  execution_agent       - Node 2a: executes ready code on Lambda or EMR (no code transformation)
  glue_execution_agent  - Node 2b: rewrites CSV-read code to spark.table() + Glue config, runs on EMR

Non-LLM prepare step (plain Python, runs before the graph):
  prepare_csv_sample    - gets/creates a 100 MB sample CSV, extracts schema, determines is_small
  prepare_glue_sample   - fetches Glue schema + sample, determines is_small

Flow:
  All modes → _prepare_sample → GraphBuilder[generate_and_validate → csv_execution or glue_execution]

  generate_and_validate handles both modes:
    - generate: calls code generation tools, validates on Lambda
    - execute:  spark_code provided in context — skips generation, executes directly

  Conditional edges:
    generate_and_validate → csv_execution:  success AND not is_small AND data_source='csv'
    generate_and_validate → glue_execution: success AND not is_small AND data_source='glue'
    (neither fires)                       : is_small or failed — generate_and_validate result is final
"""

import os
import json
import boto3
from typing import Union
from strands import Agent, tool
from strands.models import BedrockModel
from strands.multiagent import GraphBuilder
from bedrock_agentcore.runtime import BedrockAgentCoreApp

app = BedrockAgentCoreApp()

session = boto3.Session()
AWS_REGION = session.region_name or 'us-east-1'

CURRENT_SESSION_ID = None
ENVIRONMENT = os.environ.get('ENVIRONMENT', '')

DEFAULT_SAMPLE_SIZE_MB = 100


def _get_environment():
    if ENVIRONMENT:
        return ENVIRONMENT
    config = get_config()
    lambda_fn = config.get('lambda_function', '')
    if lambda_fn and '-spark-' in lambda_fn:
        return lambda_fn.split('-spark-')[0]
    return 'dev'


def _invoke_mcp_tool(function_name: str, payload: dict) -> dict:
    """Invoke an MCP tool Lambda directly (hot path)."""
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
    """Call an MCP tool via the internal AgentCore Gateway with IAM auth (cold path)."""
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

    s = boto3.Session()
    credentials = s.get_credentials()
    if credentials:
        frozen = credentials.get_frozen_credentials()
        SigV4Auth(frozen, 'bedrock-agentcore', AWS_REGION).add_auth(aws_request)
    else:
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
        if 'result' in result:
            content = result['result'].get('content', [])
            if content and isinstance(content[0], dict) and 'text' in content[0]:
                parsed = json.loads(content[0]['text'])
                # Unwrap Lambda envelope: {"statusCode": N, "body": "..."}
                if isinstance(parsed, dict) and 'body' in parsed and 'statusCode' in parsed:
                    body = parsed['body']
                    return json.loads(body) if isinstance(body, str) else body
                return parsed
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
    return {}


RUNTIME_CONFIG = None


def set_runtime_config(config):
    global RUNTIME_CONFIG
    RUNTIME_CONFIG = config


def get_config():
    if RUNTIME_CONFIG:
        return RUNTIME_CONFIG
    return load_spark_config()


# ---------------------------------------------------------------------------
# Local pure-logic tools (no external calls)
# ---------------------------------------------------------------------------

@tool
def extract_python_code(text: str) -> str:
    """Extract Python code from markdown-formatted text."""
    import re
    text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL)
    code_match = re.search(r'```python\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    code_match = re.search(r'```\n(.*?)\n```', text, re.DOTALL)
    if code_match:
        return code_match.group(1).strip()
    return text.strip()


@tool
def select_execution_platform(s3_input_path: str = None, file_size_mb: float = 0) -> str:
    """Select execution platform based on file size. Returns 'lambda' or 'emr'."""
    config = get_config()
    threshold = config.get('file_size_threshold_mb', 500)

    if file_size_mb > 0:
        return 'emr' if file_size_mb > threshold else 'lambda'

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

    return 'lambda'


@tool
def validate_spark_code(spark_code: str, s3_input_path: str = None) -> dict:
    """Validate Spark code for correctness and safety."""
    validation_errors = []

    if 'SparkSession' not in spark_code:
        validation_errors.append("Code must create a SparkSession")

    if '/tmp/output.json' not in spark_code:
        validation_errors.append("Code must write results to /tmp/output.json (required by Lambda handler)")

    if 'import json' not in spark_code and '/tmp/output.json' in spark_code:
        validation_errors.append("Code must import json module to write output file")

    if s3_input_path and s3_input_path not in spark_code:
        validation_errors.append(f"Code should read from the provided path: {s3_input_path}")

    if s3_input_path and 'spark.read' not in spark_code:
        validation_errors.append("Code should use spark.read for data input")

    has_display = any(x in spark_code for x in ['.show(', '.printSchema(', 'print('])
    if '.write' not in spark_code and not has_display and '/tmp/output.json' not in spark_code:
        validation_errors.append("Code should write results or display data")

    return {
        'status': 'success' if not validation_errors else 'validation_failed',
        'validated': len(validation_errors) == 0,
        'validation_errors': validation_errors,
        'spark_code': spark_code,
    }


@tool
def ensure_output_file_writing(spark_code: str, s3_output_path: str = None) -> str:
    """Ensure generated Spark code writes /tmp/output.json (safety net for Lambda)."""
    import re

    if '/tmp/output.json' in spark_code:
        return spark_code

    print("⚠️ WARNING: Generated code missing /tmp/output.json - injecting safety net")

    if 'import json' not in spark_code:
        lines = spark_code.split('\n')
        import_index = 0
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_index = i + 1
        lines.insert(import_index, 'import json')
        spark_code = '\n'.join(lines)

    output_code = '''
# Write output to JSON file (required by Lambda handler)
output = {"status": "success", "message": "Execution completed. Check logs for results."}
with open('/tmp/output.json', 'w') as f:
    json.dump(output, f)

'''
    if 'spark.stop()' in spark_code:
        spark_code = spark_code.replace('spark.stop()', output_code + 'spark.stop()')
    else:
        spark_code += '\n' + output_code

    return spark_code


# ---------------------------------------------------------------------------
# MCP tool wrappers (delegates to external Lambda functions)
# ---------------------------------------------------------------------------

@tool
def call_code_generation_agent(prompt: str, s3_input_path: str = None, selected_tables: list = None, s3_output_path: str = None, session_id: str = None) -> str:
    """Call Code Generation Agent to generate PySpark code from a natural language prompt."""
    config = get_config()

    code_gen_agent_arn = config.get('code_gen_agent_arn')
    if not code_gen_agent_arn:
        return "CODE_GEN_ERROR: code_gen_agent_arn not set in config"

    model_id = config.get('model_id') or config.get('bedrock_model')
    if not model_id:
        return "CODE_GEN_ERROR: model_id not set in config"

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
    if s3_output_path:
        data_context += f"\nWrite results to: {s3_output_path}"

    full_prompt = f"{prompt}{data_context}"
    actual_session_id = session_id or CURRENT_SESSION_ID or ''

    payload = {
        'prompt': full_prompt,
        'session_id': actual_session_id,
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
            runtimeSessionId=actual_session_id,
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
        return "CODE_GEN_ERROR: No response from code generation agent"
    except Exception as e:
        return f"CODE_GEN_ERROR: {str(e)}"


@tool
def execute_spark_code_lambda(spark_code: str, s3_output_path: str) -> dict:
    """Execute validated Spark code on AWS Lambda via MCP tool Lambda."""
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
    """Execute validated Spark code on EMR Serverless via Gateway MCP."""
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
    """Extract execution results from Lambda or EMR CloudWatch logs."""
    import boto3
    import time

    if isinstance(execution_result, str):
        try:
            execution_result = json.loads(execution_result.replace("'", '"'))
        except:
            execution_result = eval(execution_result)

    logs_client = boto3.client('logs', region_name=AWS_REGION)
    platform = execution_result.get('execution_platform')

    try:
        if platform == 'lambda':
            function_name = execution_result.get('lambda_function', 'SparkExecutor')
            log_group = f'/aws/lambda/{function_name}'
            end_time = int(time.time() * 1000)
            start_time = end_time - (5 * 60 * 1000)

            query = logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString='fields @message | sort @timestamp desc | limit 100',
                limit=100,
            )
            query_id = query['queryId']
            time.sleep(2)
            result = logs_client.get_query_results(queryId=query_id)
            messages = [r[0]['value'] for r in result.get('results', []) if r]
            output_lines = [
                m for m in messages
                if not any(x in m for x in ['START RequestId', 'END RequestId', 'REPORT RequestId', 'INIT_START'])
                and not ('+--' in m or (m.strip().startswith('|') and m.strip().endswith('|')))
            ]
            return {
                'status': 'success',
                'platform': 'lambda',
                'log_messages': messages,
                'execution_output': output_lines,
                'rows_written': next((m for m in messages if 'rows written' in m.lower() or 'row(s)' in m.lower()), None),
            }

        elif platform == 'emr':
            job_run_id = execution_result.get('job_run_id')
            app_id = execution_result.get('emr_application_id')

            if not job_run_id or not app_id:
                return {'status': 'error', 'error': 'Missing EMR job identifiers'}

            try:
                import gzip
                config = get_config()
                s3_client = boto3.client('s3', region_name=config['bedrock_region'])
                log_prefix = f"logs/emr/applications/{app_id}/jobs/{job_run_id}"
                response = s3_client.list_objects_v2(Bucket=config['s3_bucket'], Prefix=log_prefix)
                output_lines = []
                for obj in response.get('Contents', []):
                    key = obj['Key']
                    if ('SPARK_DRIVER' in key and ('stdout' in key or 'stderr' in key)
                            and not key.endswith('_SUCCESS')):
                        try:
                            log_obj = s3_client.get_object(Bucket=config['s3_bucket'], Key=key)
                            log_data = log_obj['Body'].read()
                            log_content = gzip.decompress(log_data).decode('utf-8') if key.endswith('.gz') else log_data.decode('utf-8')
                            lines = [
                                line.strip() for line in log_content.split('\n')
                                if line.strip() and any(
                                    x in line.lower() for x in
                                    ['print(', 'row(s)', 'rows written', 'completed', 'processing', 'analysis', 'result']
                                ) and not ('+--' in line or (line.startswith('|') and line.endswith('|') and '|' in line[1:-1]))
                            ]
                            output_lines.extend(lines)
                        except Exception as file_error:
                            print(f"Error reading log file {key}: {file_error}")
                if output_lines:
                    return {
                        'status': 'success',
                        'platform': 'emr',
                        'log_source': 's3',
                        'execution_output': output_lines[:50],
                        'log_messages': output_lines,
                        'job_run_id': job_run_id,
                    }
            except Exception as s3_error:
                print(f"S3 log extraction failed: {s3_error}")

            log_group = f'/aws/emr-serverless/{app_id}'
            end_time = int(time.time() * 1000)
            start_time = end_time - (10 * 60 * 1000)
            query = logs_client.start_query(
                logGroupName=log_group,
                startTime=start_time,
                endTime=end_time,
                queryString=f'fields @message | filter @message like /{job_run_id}/ | sort @timestamp desc | limit 100',
                limit=100,
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
                'job_run_id': job_run_id,
            }
    except Exception as e:
        return {'status': 'error', 'error': str(e), 'platform': platform}


@tool
def fetch_spark_results(s3_output_path: str, max_rows: int = None) -> dict:
    """Fetch Spark execution results from S3 output path via MCP tool Lambda."""
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
    """Fetch detailed schema for a Glue table. Also extracts a size-based sample CSV for validation."""
    config = get_config()
    return _invoke_mcp_via_gateway("get-glue-table-schema___get_glue_table_schema", {
        'database_name': database_name,
        'table_name': table_name,
        's3_bucket': config.get('s3_bucket', ''),
        'session_id': CURRENT_SESSION_ID or '',
        'sample_size_mb': config.get('sample_size_mb', DEFAULT_SAMPLE_SIZE_MB),
        'region': AWS_REGION,
    })


# ---------------------------------------------------------------------------
# Prepare nodes (non-LLM, pure Python)
# ---------------------------------------------------------------------------

def _extract_csv_schema(sample_bytes: bytes) -> str:
    """Parse CSV header row from sample bytes and return a schema_context string."""
    try:
        first_line = sample_bytes.split(b'\n')[0].decode('utf-8', errors='replace').strip()
        if first_line:
            columns = [c.strip().strip('"').strip("'") for c in first_line.split(',')]
            if columns:
                return 'Column names: ' + ', '.join(columns)
    except Exception:
        pass
    return ''


def prepare_csv_sample(s3_input_path: str, s3_sample_path: str, file_size_bytes: int, session_id: str) -> dict:
    """Prepare CSV sample for validation. Returns sample_path, is_small, error."""
    config = get_config()
    sample_size_mb = config.get('sample_size_mb', DEFAULT_SAMPLE_SIZE_MB)
    sample_size_bytes = sample_size_mb * 1024 * 1024

    # Case 1: file_size_bytes already known (frontend GUI upload)
    if file_size_bytes is not None and s3_sample_path:
        is_small = (file_size_bytes <= sample_size_bytes)
        print(f"✅ CSV prepare (frontend): file_size={file_size_bytes}B, sample_limit={sample_size_bytes}B, is_small={is_small}")
        # Read the first line of the sample to extract column names
        schema_context = ''
        try:
            s3 = boto3.client('s3', region_name=AWS_REGION)
            sample_bucket = s3_sample_path.replace('s3://', '').split('/')[0]
            sample_key = '/'.join(s3_sample_path.replace('s3://', '').split('/')[1:])
            header_obj = s3.get_object(Bucket=sample_bucket, Key=sample_key, Range='bytes=0-4095')
            schema_context = _extract_csv_schema(header_obj['Body'].read())
        except Exception:
            pass
        return {'sample_path': s3_sample_path, 'full_path': s3_input_path, 'is_small': is_small, 'schema_context': schema_context}

    if not s3_input_path:
        return {'error': 'No s3_input_path provided'}

    s3 = boto3.client('s3', region_name=AWS_REGION)
    bucket = s3_input_path.replace('s3://', '').split('/')[0]
    key = '/'.join(s3_input_path.replace('s3://', '').split('/')[1:])

    # Case 2: sample already exists but no file_size_bytes (wrapper Lambda)
    if s3_sample_path:
        try:
            head = s3.head_object(Bucket=bucket, Key=key)
            file_size = head['ContentLength']
            is_small = (file_size <= sample_size_bytes)
            # Read the first line of the sample to extract column names
            schema_context = ''
            try:
                sample_bucket = s3_sample_path.replace('s3://', '').split('/')[0]
                sample_key_path = '/'.join(s3_sample_path.replace('s3://', '').split('/')[1:])
                header_obj = s3.get_object(Bucket=sample_bucket, Key=sample_key_path, Range='bytes=0-4095')
                schema_context = _extract_csv_schema(header_obj['Body'].read())
            except Exception:
                pass
            print(f"✅ CSV prepare (wrapper): file_size={file_size}B, is_small={is_small}")
            return {'sample_path': s3_sample_path, 'full_path': s3_input_path, 'is_small': is_small, 'schema_context': schema_context}
        except Exception as e:
            return {'error': f'Could not get file size: {str(e)}'}

    # Case 3: no sample — create one
    try:
        s3_bucket_out = config.get('s3_bucket', bucket)
        obj = s3.get_object(Bucket=bucket, Key=key, Range=f'bytes=0-{sample_size_bytes - 1}')
        content = obj['Body'].read()
        bytes_read = len(content)
        is_small = (bytes_read < sample_size_bytes)
        schema_context = _extract_csv_schema(content)

        if len(content) == sample_size_bytes:
            last_newline = content.rfind(b'\n')
            if last_newline > 0:
                content = content[:last_newline + 1]

        sample_key = f'{session_id}/samples/sample.csv'
        s3.put_object(Bucket=s3_bucket_out, Key=sample_key, Body=content, ContentType='text/csv')
        sample_path = f's3://{s3_bucket_out}/{sample_key}'
        print(f"✅ CSV prepare (new sample): bytes_read={bytes_read}, is_small={is_small}, sample={sample_path}")
        return {'sample_path': sample_path, 'full_path': s3_input_path, 'is_small': is_small, 'schema_context': schema_context}
    except Exception as e:
        return {'error': f'Could not create sample: {str(e)}'}


def prepare_glue_sample(selected_tables: list, session_id: str) -> dict:
    """Fetch Glue schema and sample. Returns sample_path, schema_context, is_small, table_refs."""
    config = get_config()
    sample_size_mb = config.get('sample_size_mb', DEFAULT_SAMPLE_SIZE_MB)
    sample_size_bytes = sample_size_mb * 1024 * 1024

    if not selected_tables:
        return {'error': 'No tables selected'}

    schemas = []
    sample_path = None
    data_file_size_bytes = None
    table_refs = []

    for table in selected_tables:
        if isinstance(table, dict):
            db = table.get('database', '')
            tbl = table.get('table', '')
        else:
            parts = str(table).split('.')
            db = parts[0]
            tbl = parts[1] if len(parts) > 1 else parts[0]

        table_refs.append(f'{db}.{tbl}')

        result = fetch_glue_table_schema(db, tbl)

        if result.get('status') != 'success':
            return {'error': f"Could not fetch schema for {db}.{tbl}: {result.get('error', 'unknown')}"}

        columns = result.get('columns', [])
        schema_str = f'Table: {db}.{tbl}\nColumns:\n'
        for col in columns:
            schema_str += f"  - {col['name']} ({col['type']})\n"
        schemas.append(schema_str)

        if not sample_path and result.get('sample_s3_path'):
            sample_path = result['sample_s3_path']

        if data_file_size_bytes is None and result.get('data_file_size_bytes') is not None:
            data_file_size_bytes = result['data_file_size_bytes']

    if not sample_path:
        return {'error': 'No sample data available from Glue tables'}

    is_small = (data_file_size_bytes is not None and data_file_size_bytes <= sample_size_bytes)
    schema_context = '\n'.join(schemas)

    print(f"✅ Glue prepare: data_file_size={data_file_size_bytes}B, is_small={is_small}, sample={sample_path}")
    return {
        'sample_path': sample_path,
        'schema_context': schema_context,
        'is_small': is_small,
        'table_refs': table_refs,
    }


# ---------------------------------------------------------------------------
# Agent factories
# ---------------------------------------------------------------------------

def _get_model():
    config = get_config()
    model_id = config.get('model_id') or config.get('bedrock_model') or 'us.anthropic.claude-sonnet-4-5-20250929-v1:0'
    return BedrockModel(model_id=model_id, max_tokens=8000)


def create_generate_and_validate_agent() -> Agent:
    """Agent 1: generates PySpark code from user prompt and validates it on Lambda using a sample CSV.
    Also handles direct execution when spark_code is already provided (execute mode)."""
    system_prompt = """You are a Spark code generation, validation, and execution agent.

INPUTS provided in your context:
- User request: the data analysis request
- sample_path: S3 path to sample CSV — READ DATA FROM THIS PATH during generation/validation
- s3_input_path: full S3 path to the input dataset
- s3_output_path: where to write results
- execution_platform: "auto", "lambda", or "emr"
- spark_code: (optional) already-validated code — present only in execute mode
- Schema: column names — ALWAYS include verbatim in the code generation prompt

─── IF spark_code IS PROVIDED (execute mode) ────────────────────────────────
Skip steps 1–4. Go directly to step 5 using the provided spark_code.

─── IF spark_code IS NOT PROVIDED (generate mode) ───────────────────────────
WORKFLOW (up to 3 attempts on code errors):
1. Call call_code_generation_agent. The prompt MUST include:
   - The user's original request
   - s3_input_path=sample_path (generated code reads from sample_path)
   - The exact column names from the schema to avoid name mismatches
   Generated code MUST:
   - Read data using spark.read.csv(sample_path) with header=True, inferSchema=True
   - Write results to s3_output_path using df.write.mode("overwrite").csv(s3_output_path)
   - Write /tmp/output.json for the Lambda handler
   - NEVER use spark.table(), NEVER use Hive catalog, NEVER call EMR
2. Call extract_python_code to clean the code
3. Call validate_spark_code(spark_code=<code>, s3_input_path=<sample_path>)
4. Call ensure_output_file_writing if /tmp/output.json is missing

─── STEP 5 (both modes) ─────────────────────────────────────────────────────
5. Execute:
   - If execution_platform is "auto": call select_execution_platform(s3_input_path=<path>) to choose
   - "lambda": call execute_spark_code_lambda(spark_code=<code>, s3_output_path=<path>)
   - "emr":    call execute_spark_code_emr(spark_code=<code>, s3_output_path=<path>)
   - SUCCESS: skip to step 7 immediately — do NOT call extract_execution_logs
   - Code error: call extract_execution_logs to get error details, then retry from step 1 (max 3 total)
   - Resource error (OOM/timeout): mark execution_result as "failed", stop
7. Call fetch_spark_results(s3_output_path=<path>)

SUCCESS CHECK: Lambda → result.status == "success". EMR → result.job_state == "SUCCESS".

CRITICAL: Return a valid JSON object:
{"spark_code": "<complete Python code>", "execution_result": "success" or "failed", "execution_message": "<summary>", "execution_output": ["<print lines>"], "actual_results": [<data>], "s3_output_path": "<path>"}"""

    return Agent(
        model=_get_model(),
        system_prompt=system_prompt,
        tools=[
            call_code_generation_agent,
            extract_python_code,
            validate_spark_code,
            ensure_output_file_writing,
            select_execution_platform,
            execute_spark_code_lambda,
            execute_spark_code_emr,
            extract_execution_logs,
            fetch_spark_results,
        ],
        name="GenerateAndValidateAgent",
    )


def create_execution_agent() -> Agent:
    """Agent 2a: executes ready-to-run PySpark code on Lambda or EMR. No code transformation."""
    system_prompt = """You are a Spark code execution agent. Execute PySpark code on the appropriate platform.

INPUTS provided in your context:
- spark_code: complete, validated PySpark code (from previous validation agent)
- s3_output_path: where results will be written
- s3_input_path: full S3 path to the input file (used for platform selection and path replacement)
- execution_platform: "auto", "lambda", or "emr"

PRE-EXECUTION: Replace any sample path in spark_code with s3_input_path before executing.
  - Find any spark.read.csv("<sample_path>") in the code and replace with spark.read.csv("<s3_input_path>")
  - If sample_path == s3_input_path, no replacement needed.

WORKFLOW (execute once, no retries, no other code changes):
1. Platform selection:
   - If execution_platform is "lambda": use Lambda
   - If execution_platform is "emr": use EMR
   - If execution_platform is "auto": call select_execution_platform(s3_input_path=<path>) and use the result
2. Execute ONCE based on platform:
   - "lambda": call execute_spark_code_lambda(spark_code=<code>, s3_output_path=<path>)
   - "emr": call execute_spark_code_emr(spark_code=<code>, s3_output_path=<path>)
3. SUCCESS: skip extract_execution_logs — go directly to step 4.
   FAILURE: call extract_execution_logs(execution_result=<result>) to capture the error, then return failed.
4. Call fetch_spark_results(s3_output_path=<path>)

SUCCESS CHECK: Lambda success when result.status == "success". EMR success when result.job_state == "SUCCESS".

CRITICAL: Return a valid JSON object:
{"spark_code": "<the spark_code executed>", "execution_result": "success" or "failed", "execution_message": "<summary>", "execution_output": ["<lines>"], "actual_results": [<data>], "s3_output_path": "<path>"}"""

    return Agent(
        model=_get_model(),
        system_prompt=system_prompt,
        tools=[
            select_execution_platform,
            execute_spark_code_lambda,
            execute_spark_code_emr,
            extract_execution_logs,
            fetch_spark_results,
        ],
        name="ExecutionAgent",
    )


def create_glue_execution_agent() -> Agent:
    """Agent 2b: rewrites CSV-read code to use Glue catalog (spark.table), then executes on EMR."""
    system_prompt = """You are a Spark code execution agent for Glue tables. Rewrite validated code to use Glue catalog, then execute on EMR.

INPUTS provided in your context:
- spark_code: validated PySpark code that currently reads from spark.read.csv(sample_path)
- table_refs: list of "database.table" Glue table references
- s3_output_path: where to write results
- warehouse_dir: S3 path for Hive warehouse

WORKFLOW (execute once, no retries):
1. Rewrite spark_code:
   a. In the SparkSession builder, add BEFORE .getOrCreate():
      .config("spark.hadoop.hive.metastore.client.factory.class",
              "com.amazonaws.glue.catalog.metastore.AWSGlueDataCatalogHiveClientFactory")
      .config("spark.sql.warehouse.dir", "<warehouse_dir from context>")
      .enableHiveSupport()
   b. Replace spark.read.csv(sample_path) with spark.table("database.table")
      - Use the table_refs from context to get the correct "database.table" references
      - Use spark.read.option(...).csv() → spark.table("database.table")
      - Ensure the DataFrame variable name stays the same
   c. Keep all transformation logic unchanged
   d. Keep df.write.csv(s3_output_path) unchanged
2. Call execute_spark_code_emr(spark_code=<rewritten_code>, s3_output_path=<path>)
3. SUCCESS (job_state == "SUCCESS"): skip extract_execution_logs — go directly to step 4.
   FAILURE: call extract_execution_logs(execution_result=<result>) to capture the error, then return failed.
4. Call fetch_spark_results(s3_output_path=<path>)

SUCCESS CHECK: EMR success when result.job_state == "SUCCESS".

CRITICAL: Return a valid JSON object:
{"spark_code": "<rewritten code>", "execution_result": "success" or "failed", "execution_message": "<summary>", "execution_output": ["<lines>"], "actual_results": [<data>], "s3_output_path": "<path>"}"""

    return Agent(
        model=_get_model(),
        system_prompt=system_prompt,
        tools=[
            execute_spark_code_emr,
            extract_execution_logs,
            fetch_spark_results,
        ],
        name="GlueExecutionAgent",
    )


# ---------------------------------------------------------------------------
# Context builders
# ---------------------------------------------------------------------------

def _prepare_sample(payload: dict) -> dict:
    """Run the pre-graph sample preparation step. Returns prep dict with sample_path, is_small, etc."""
    selected_tables = payload.get('selected_tables')
    session_id = payload.get('session_id', '')
    if selected_tables:
        return prepare_glue_sample(selected_tables, session_id)
    spark_code = payload.get('spark_code')
    if spark_code:
        # Execute mode: code already provided, no sample needed
        s3_input_path = payload.get('s3_input_path', '')
        return {'sample_path': s3_input_path, 'is_small': True, 'schema_context': '', 'table_refs': []}
    s3_input_path = payload.get('s3_input_path')
    if not s3_input_path:
        # Calculation-only query — no data source, treat as small so no execution node fires
        return {'sample_path': '', 'is_small': True, 'schema_context': '', 'table_refs': []}
    return prepare_csv_sample(
        s3_input_path, payload.get('s3_sample_path'),
        payload.get('file_size_bytes'), session_id,
    )


def _build_task_context(payload: dict, prep: dict) -> str:
    """Build the task context string passed to the generate_and_validate graph node."""
    cfg = get_config()
    warehouse_dir = f's3://{cfg.get("s3_bucket", "")}/warehouse/' if cfg.get('s3_bucket') else 's3://spark-warehouse/'
    schema_context = prep.get('schema_context', '')
    table_refs = prep.get('table_refs', [])
    schema_section = f'\n\nSchema (MUST include in code generation prompt to avoid column name errors):\n{schema_context}' if schema_context else ''
    tables_str = ', '.join(table_refs) if table_refs else 'N/A'
    spark_code = payload.get('spark_code')
    spark_code_section = f'\n\nspark_code (already provided — skip generation, go directly to execution):\n```python\n{spark_code}\n```' if spark_code else ''
    return f"""User request: {payload.get('prompt', '')}

sample_path: {prep.get('sample_path', '')}
s3_input_path: {payload.get('s3_input_path') or prep.get('sample_path', '')}
s3_output_path: {payload.get('s3_output_path', '')}
data_source_type: {'glue' if payload.get('selected_tables') else 'csv'}
execution_platform: {payload.get('execution_platform', 'auto')}
table_refs: {tables_str}
warehouse_dir: {warehouse_dir}{schema_section}{spark_code_section}"""


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def _build_graph(data_source_type: str, is_small: bool):
    """Build the single graph for all modes: generate_and_validate → csv_execution or glue_execution."""
    builder = GraphBuilder()
    builder.add_node(create_generate_and_validate_agent(), node_id="generate_and_validate")
    builder.add_node(create_execution_agent(), node_id="csv_execution")
    builder.add_node(create_glue_execution_agent(), node_id="glue_execution")

    def to_csv_execution(state) -> bool:
        val = state.results.get("generate_and_validate")
        if not val:
            return False
        result = json.loads(_parse_agent_response(str(val.result), ""))
        return result.get("execution_result") == "success" and not is_small and data_source_type == "csv"

    def to_glue_execution(state) -> bool:
        val = state.results.get("generate_and_validate")
        if not val:
            return False
        result = json.loads(_parse_agent_response(str(val.result), ""))
        return result.get("execution_result") == "success" and not is_small and data_source_type == "glue"

    builder.add_edge("generate_and_validate", "csv_execution", condition=to_csv_execution)
    builder.add_edge("generate_and_validate", "glue_execution", condition=to_glue_execution)
    builder.set_entry_point("generate_and_validate")
    return builder.build()


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------

def _parse_agent_response(response_text: str, s3_output_path: str) -> str:
    """Parse JSON from agent response. Returns a JSON string."""
    import re

    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            result = json.loads(json_match.group(1))
            return json.dumps({
                'spark_code': result.get('spark_code'),
                'execution_result': result.get('execution_result', 'success'),
                'execution_message': result.get('execution_message', ''),
                'execution_output': result.get('execution_output', []),
                'actual_results': result.get('actual_results', []),
                's3_output_path': result.get('s3_output_path', s3_output_path),
            })
        except:
            pass

    try:
        start = response_text.find('{')
        end = response_text.rfind('}') + 1
        if start >= 0 and end > start:
            result = json.loads(response_text[start:end])
            if 'spark_code' in result or 'execution_result' in result:
                return json.dumps({
                    'spark_code': result.get('spark_code'),
                    'execution_result': result.get('execution_result', 'success'),
                    'execution_message': result.get('execution_message', ''),
                    'execution_output': result.get('execution_output', []),
                    'actual_results': result.get('actual_results', []),
                    's3_output_path': result.get('s3_output_path', s3_output_path),
                })
    except:
        pass

    return json.dumps({
        'spark_code': None,
        'execution_result': 'failed',
        'execution_message': 'Could not parse agent response',
        'execution_output': [],
        'actual_results': [],
        's3_output_path': s3_output_path,
    })


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

@app.entrypoint
def invoke(payload):
    """Main entrypoint. Routes all execution modes through a single GraphBuilder graph."""
    global CURRENT_SESSION_ID

    if payload.get('config'):
        set_runtime_config(payload['config'])
        print(f"✅ Runtime config set: {list(payload['config'].keys())}")

    # Normalise legacy skip_generation flag
    if payload.get('skip_generation'):
        payload = {**payload, 'mode': 'execute'}

    CURRENT_SESSION_ID = payload.get('session_id', '')
    s3_output_path = payload.get('s3_output_path', '')
    data_source_type = 'glue' if payload.get('selected_tables') else 'csv'

    try:
        prep = _prepare_sample(payload)
        if prep.get('error'):
            return json.dumps({
                'spark_code': None,
                'execution_result': f"failed: {prep['error']}",
                'execution_message': prep['error'],
                'execution_output': [],
                'actual_results': [],
                's3_output_path': s3_output_path,
            })

        print(f"📊 Sample ready: is_small={prep['is_small']}, data_source={data_source_type}")
        graph = _build_graph(data_source_type, prep['is_small'])
        graph_result = graph(task=_build_task_context(payload, prep))

        node_result = None
        for node_id in ("glue_execution", "csv_execution", "generate_and_validate"):
            node_result = graph_result.results.get(node_id)
            if node_result:
                print(f"✅ Result from node: {node_id}")
                break

        result_text = str(node_result.result) if node_result and hasattr(node_result, 'result') else str(node_result)
        return _parse_agent_response(result_text, s3_output_path)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return json.dumps({
            'spark_code': None,
            'execution_result': f'Error: {str(e)}',
            'execution_message': str(e),
            'execution_output': [],
            'actual_results': [],
            's3_output_path': s3_output_path,
        })


if __name__ == "__main__":
    app.run()
