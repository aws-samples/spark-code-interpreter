import json
import time
import os
import logging
from typing import Optional, List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import requests
import asyncio
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
from datetime import datetime, timezone
try:
    from .config import load_config, save_config, get_ray_private_ip, get_ray_public_ip, get_s3_bucket, get_default_config
except ImportError:
    from config import load_config, save_config, get_ray_private_ip, get_ray_public_ip, get_s3_bucket, get_default_config

logger = logging.getLogger(__name__)

# Framework configuration
FRAMEWORK_RAY = "ray"
FRAMEWORK_SPARK = "spark"

# Agent ARNs
CODE_GEN_AGENT_ARN = 'arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/code_generation_agent-xyz'  # Shared

# Gateway URLs
MCP_GATEWAY_URL = 'https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp'

print(f"✅ Unified FastAPI backend for Ray and Spark")
print(f"✓ Ray Private IP: {get_ray_private_ip()}")
print(f"✓ Ray Public IP: {get_ray_public_ip()}")
print(f"✓ S3 Bucket: {get_s3_bucket()}")
print(f"✓ MCP Gateway: {MCP_GATEWAY_URL}")

app = FastAPI(title="Ray Code Interpreter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Track which IP is working
_working_ray_ip = None

def get_ray_dashboard_url():
    """Get Ray dashboard URL with IP fallback"""
    global _working_ray_ip
    if _working_ray_ip:
        return f"http://{_working_ray_ip}:8265"
    # Default to private IP first
    return f"http://{get_ray_private_ip()}:8265"

def make_ray_request(endpoint, method='GET', timeout=5, **kwargs):
    """Make request to Ray cluster with automatic IP fallback"""
    import requests
    global _working_ray_ip
    
    private_ip = get_ray_private_ip()
    public_ip = get_ray_public_ip()
    
    # If we have a working IP, try ONLY that one first
    if _working_ray_ip:
        try:
            url = f"http://{_working_ray_ip}:8265{endpoint}"
            if method == 'GET':
                response = requests.get(url, timeout=timeout, **kwargs)
            else:
                response = requests.post(url, timeout=timeout, **kwargs)
            
            if response.status_code == 200:
                return response
        except Exception:
            # Working IP failed, try the other one
            other_ip = public_ip if _working_ray_ip == private_ip else private_ip
            if other_ip:
                try:
                    url = f"http://{other_ip}:8265{endpoint}"
                    if method == 'GET':
                        response = requests.get(url, timeout=timeout, **kwargs)
                    else:
                        response = requests.post(url, timeout=timeout, **kwargs)
                    
                    if response.status_code == 200:
                        _working_ray_ip = other_ip
                        return response
                except Exception:
                    pass
            return None
    
    # No known working IP, try both
    for ip in [private_ip, public_ip]:
        if not ip:
            continue
        try:
            url = f"http://{ip}:8265{endpoint}"
            if method == 'GET':
                response = requests.get(url, timeout=timeout, **kwargs)
            else:
                response = requests.post(url, timeout=timeout, **kwargs)
            
            if response.status_code == 200:
                _working_ray_ip = ip
                return response
        except Exception:
            continue
    
    return None

# Session management class
class SessionManager:
    def __init__(self, session_id: str):
        self.session_id = session_id
        self.conversation_history = []
        self.execution_results = []
        self.uploaded_csv = None
        self.selected_tables = []

# Session storage
sessions = {}

# Session history storage (in-memory) - keeping for backward compatibility
session_history = {}

# Session data sources storage (for code generation agent)
prompt_sessions = {}

# AgentCore client
agentcore_client = boto3.client(
    'bedrock-agentcore', 
    region_name='us-east-1',
    config=boto3.session.Config(
        read_timeout=300,
        connect_timeout=60,
        retries={'max_attempts': 3}
    )
)

class CodeRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None

class ExecuteRequest(BaseModel):
    code: str
    session_id: Optional[str] = None
    interactive: Optional[bool] = False
    inputs: Optional[list] = None

class SettingsRequest(BaseModel):
    ray_private_ip: str
    ray_public_ip: str
    s3_bucket: str
    ray_gateway_url: str
    ray_supervisor_arn: str
    global_bedrock_model: str
    global_code_gen_agent_arn: str
    global_bedrock_region: str
    spark_s3_bucket: str
    spark_lambda_function: str
    spark_emr_application_id: str
    spark_max_retries: int
    spark_file_size_threshold_mb: int
    spark_result_preview_rows: int
    spark_presigned_url_expiry_hours: int
    spark_lambda_timeout_seconds: int
    spark_emr_timeout_minutes: int
    spark_supervisor_arn: str

class CsvUploadRequest(BaseModel):
    filename: str
    content: str
    session_id: Optional[str] = None

class CodeResponse(BaseModel):
    success: bool
    code: Optional[str] = None
    error: Optional[str] = None
    session_id: str
    iterations: Optional[int] = None

class ExecuteResponse(BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    session_id: str
    job_id: Optional[str] = None

def make_signed_mcp_request(payload):
    """Make signed request to MCP Gateway"""
    session = boto3.Session()
    credentials = session.get_credentials()
    
    request = AWSRequest(
        method='POST',
        url=MCP_GATEWAY_URL,
        data=json.dumps(payload),
        headers={
            'Content-Type': 'application/json',
            'X-Amz-Date': datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        }
    )
    
    SigV4Auth(credentials, 'bedrock-agentcore', 'us-east-1').add_auth(request)
    
    response = requests.post(
        MCP_GATEWAY_URL,
        data=request.body,
        headers=dict(request.headers),
        timeout=60
    )
    
    return response

def extract_ray_code(response_text: str) -> str:
    """Extract Ray code from response"""
    import re
    
    # Look for code blocks
    code_block_match = re.search(r'```python\n(.*?)\n```', response_text, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()
    
    # Look for import ray statements
    lines = response_text.split('\n')
    code_lines = []
    in_code = False
    
    for line in lines:
        if 'import ray' in line:
            in_code = True
        if in_code:
            if line.strip() and not line.startswith('#') and not line.startswith('This code'):
                code_lines.append(line)
            elif not line.strip() and code_lines and len(code_lines) > 3:
                break
    
    return '\n'.join(code_lines) if code_lines else response_text

@app.post("/generate", response_model=CodeResponse)
async def generate_code(request: CodeRequest):
    """Generate Ray code using Supervisor Agent Runtime"""
    
    try:
        import uuid
        # Ensure session ID is at least 33 characters
        if request.session_id and len(request.session_id) >= 33:
            session_id = request.session_id
        else:
            session_id = f"fastapi-session-{uuid.uuid4().hex}"  # 48 chars total
        
        print(f"🚀 Processing request via Supervisor Agent Runtime")
        print(f"   Session ID: {session_id}")
        print(f"   Prompt: {request.prompt}")
        
        # Get session data sources if available
        csv_data = None
        tables_data = []
        if session_id in prompt_sessions:
            csv_data = prompt_sessions[session_id].get('csv')
            tables_data = prompt_sessions[session_id].get('tables', [])
            print(f"   CSV: {csv_data['filename'] if csv_data else 'None'}")
            print(f"   Tables: {len(tables_data)} selected")
        
        # Build prompt with data sources embedded (agent can't import from main.py)
        prompt_parts = [f"Session ID: {session_id}"]
        
        if csv_data:
            prompt_parts.append(f"\nAvailable CSV file:")
            prompt_parts.append(f"  - Filename: {csv_data['filename']}")
            prompt_parts.append(f"  - S3 Path: {csv_data['s3_path']}")
            if 'preview' in csv_data:
                prompt_parts.append(f"  - Schema/Preview (first 5 lines):")
                prompt_parts.append(f"```\n{csv_data['preview']}\n```")
        
        if tables_data:
            prompt_parts.append(f"\nAvailable Glue tables:")
            for table in tables_data:
                prompt_parts.append(f"  - {table['database']}.{table['table']} at {table['location']}")
        
        prompt_parts.append(f"\n{request.prompt}")
        prompt_with_context = "\n".join(prompt_parts)
        
        # Get configuration values
        config = load_config()
        model_id = config.get("global", {}).get("bedrock_model")
        gateway_url = config.get("ray", {}).get("gateway_url")
        code_gen_agent_arn = config.get("global", {}).get("code_gen_agent_arn")
        ray_supervisor_arn = config.get("ray", {}).get("supervisor_arn")
        
        payload = {
            "prompt": prompt_with_context,
            "ray_cluster_ip": get_ray_private_ip(),
            "model_id": model_id,
            "gateway_url": gateway_url,
            "code_gen_agent_arn": code_gen_agent_arn
        }
        
        # Call Supervisor Agent Runtime using boto3
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=ray_supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Extract response content
        response_body = response["response"].read()
        if response_body:
            try:
                result = json.loads(response_body.decode("utf-8"))
                if isinstance(result, str):
                    result = result
                else:
                    result = str(result)
            except json.JSONDecodeError:
                result = response_body.decode("utf-8")
        else:
            result = "No response"
        
        # Extract clean Ray code from response
        code = extract_ray_code(result)
        
        print(f"✅ Supervisor Agent completed successfully")
        print(f"   Generated code length: {len(code)} characters")
        
        # Store in session history
        if session_id not in sessions:
            sessions[session_id] = SessionManager(session_id)
        
        session = sessions[session_id]
        
        # Store conversation history
        session.conversation_history.append({
            'type': 'generation',
            'prompt': request.prompt,
            'generated_code': code,
            'timestamp': time.time(),
            'framework': 'ray'
        })
        
        # Keep old format for backward compatibility
        if session_id not in session_history:
            session_history[session_id] = []
        session_history[session_id].append({
            'type': 'generation',
            'prompt': request.prompt,
            'code': code,
            'timestamp': time.time(),
            'success': True
        })
        
        return CodeResponse(
            success=True,
            code=code,
            session_id=session_id,
            iterations=1
        )
        
    except Exception as e:
        error_msg = f"Code generation failed: {str(e)}"
        print(f"❌ Error: {error_msg}")
        
        return CodeResponse(
            success=False,
            error=error_msg,
            session_id=session_id or "unknown"
        )

@app.post("/execute", response_model=ExecuteResponse)
async def execute_code(request: ExecuteRequest):
    """Execute Ray code using Supervisor Agent"""
    
    try:
        import uuid
        # Ensure session ID is at least 33 characters
        if request.session_id and len(request.session_id) >= 33:
            session_id = request.session_id
        else:
            session_id = f"exec-session-{uuid.uuid4().hex}"
        
        print(f"🧪 Executing code via Supervisor Agent")
        print(f"   Session ID: {session_id}")
        print(f"   Code length: {len(request.code)} characters")
        
        # Prepare payload for Supervisor Agent with execution instruction
        config = load_config()
        payload = {
            "prompt": f"EXECUTE_ONLY: Run this code and return the execution output:\n\n{request.code}",
            "ray_cluster_ip": get_ray_private_ip(),
            "model_id": config.get("global", {}).get("bedrock_model"),
            "gateway_url": config.get("ray", {}).get("gateway_url"),
            "code_gen_agent_arn": config.get("global", {}).get("code_gen_agent_arn")
        }
        
        # Get Ray supervisor ARN from config
        ray_supervisor_arn = config.get("ray", {}).get("supervisor_arn")
        
        # Call Supervisor Agent Runtime
        response = agentcore_client.invoke_agent_runtime(
            agentRuntimeArn=ray_supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        # Extract response
        response_body = response["response"].read()
        if response_body:
            try:
                # Try to parse as JSON first
                result = json.loads(response_body.decode("utf-8"))
                # If it's a dict, look for common output keys
                if isinstance(result, dict):
                    output = result.get('output') or result.get('result') or str(result)
                else:
                    output = str(result)
            except json.JSONDecodeError:
                # Not JSON, use as plain text
                output = response_body.decode("utf-8")
        else:
            output = "No response"
        
        # Unescape newlines if they're escaped
        if '\\n' in output and '\n' not in output:
            output = output.replace('\\n', '\n').replace('\\t', '\t')
        
        # Filter Ray internal logs and thinking tags - keep only user output
        output_lines = []
        skip_thinking = False
        
        for line in output.split('\n'):
            # Skip thinking blocks - check closing tag FIRST
            if '</thinking>' in line:
                skip_thinking = False
                continue
            if '<thinking>' in line:
                skip_thinking = True
                continue
            if skip_thinking:
                continue
            
            stripped = line.strip()
            
            # Skip empty lines
            if not stripped:
                continue
            
            # Check if line contains Ray internal log patterns (anywhere in the line, not just at start)
            is_internal_log = any(pattern in line for pattern in [
                'INFO job_manager', 'INFO worker.py', 
                'Runtime env is setting up', 'Connecting to existing Ray',
                'View the dashboard at', 'Registered dataset logger',
                'Starting execution of Dataset', 'Execution plan of Dataset',
                'Full logs are in', 'object store is configured',
                'Ray Data performance', 'Running 0:', 'Sort Sample',
                'Shuffle Map', 'Shuffle Reduce'
            ])
            
            if is_internal_log:
                continue
            
            # Skip lines that are ONLY progress bars or ANSI codes
            if 'row [00:00' in line and 'row/s]' in line and ':' not in line.split('row/s]')[0].split('row [00:00')[0]:
                continue
            
            # Skip lines with only ANSI escape codes and no actual content
            clean_line = line.replace('\u001b[', '').replace('\x1b[', '').replace('[0m', '').replace('[1m', '').replace('[32m', '').replace('[36m', '').replace('[39m', '').replace('[22m', '').replace('[2m', '')
            if not clean_line.strip() or clean_line.strip() in ['', 'A', 'AA', 'AAA', 'AAAA']:
                continue
            
            # Skip Dataset execution finished messages (but keep user output)
            if 'Dataset execution finished' in line and 'row/s]' in line:
                continue
                
            output_lines.append(line)
        
        clean_output = '\n'.join(output_lines).strip()
        if not clean_output:
            clean_output = "Code executed successfully (no output)"
        
        print(f"✅ Code executed successfully")
        print(f"   Output: {clean_output[:200]}...")  # Log first 200 chars
        
        # Store in session history
        if session_id not in sessions:
            sessions[session_id] = SessionManager(session_id)
        
        session = sessions[session_id]
        
        # Store execution results
        session.execution_results.append({
            'code': request.code,
            'result': clean_output,
            'timestamp': time.time(),
            'success': True,
            'framework': 'ray'
        })
        
        # Keep old format for backward compatibility
        if session_id not in session_history:
            session_history[session_id] = []
        session_history[session_id].append({
            'type': 'execution',
            'code': request.code,
            'output': clean_output,
            'timestamp': time.time(),
            'success': True
        })
        
        return ExecuteResponse(
            success=True,
            output=clean_output,
            session_id=session_id
        )
        
    except Exception as e:
        error_msg = f"Execution failed: {str(e)}"
        print(f"❌ Error: {error_msg}")
        
        return ExecuteResponse(
            success=False,
            error=error_msg,
            session_id=session_id
        )

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    config = load_config()
    ray_supervisor_arn = config.get("ray", {}).get("supervisor_arn", "not configured")
    
    return {
        "status": "healthy",
        "supervisor_agent_arn": ray_supervisor_arn,
        "ray_private_ip": get_ray_private_ip(),
        "ray_public_ip": get_ray_public_ip(),
        "s3_bucket": get_s3_bucket(),
        "mcp_gateway_url": MCP_GATEWAY_URL,
        "timestamp": time.time()
    }

@app.get("/ray/status")
async def ray_status():
    """Ray cluster status endpoint with retry logic"""
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = make_ray_request("/api/version", timeout=5)
            if response:
                version_info = response.json()
                return {
                    "status": "connected",
                    "ray_version": version_info.get('ray_version'),
                    "dashboard_url": get_ray_dashboard_url()
                }
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(1)  # Wait 1 second before retry
                continue
            print(f"Ray status check failed after {max_retries} attempts: {e}")
    
    return {
        "status": "disconnected",
        "dashboard_url": get_ray_dashboard_url()
    }

@app.get("/ray/jobs")
async def ray_jobs():
    """Ray jobs endpoint with IP fallback"""
    try:
        response = make_ray_request("/api/jobs/", timeout=5)
        if response:
            data = response.json()
            # Ray API returns array directly
            if isinstance(data, list):
                return {"success": True, "jobs": data}
            elif isinstance(data, dict) and "jobs" in data:
                return {"success": True, "jobs": data["jobs"]}
            return {"success": True, "jobs": []}
    except Exception as e:
        print(f"Failed to get Ray jobs: {e}")
    return {"success": False, "jobs": []}

@app.post("/ray/jobs/{job_id}/stop")
async def stop_ray_job(job_id: str):
    """Stop Ray job endpoint"""
    try:
        response = make_ray_request(f"/api/jobs/{job_id}/stop", method='POST', timeout=5)
        return {"success": response is not None and response.status_code == 200}
    except:
        return {"success": False}

@app.post("/sessions/{session_id}/reset")
async def reset_session(session_id: str):
    """Reset session data sources"""
    if session_id in prompt_sessions:
        prompt_sessions[session_id] = {'csv': None, 'tables': [], 'postgres_tables': []}
        print(f"✅ Reset session data sources for {session_id}")
    return {"success": True, "message": "Session reset"}

@app.post("/upload-csv")
async def upload_csv(request: CsvUploadRequest):
    """Upload CSV file to S3 bucket"""
    try:
        import base64
        
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket = get_s3_bucket()
        session_id = request.session_id or "default"
        
        # Create S3 key with session prefix
        s3_key = f"sessions/{session_id}/csv/{request.filename}"
        
        # Upload to S3
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=request.content.encode('utf-8'),
            ContentType='text/csv'
        )
        
        s3_uri = f"s3://{bucket}/{s3_key}"
        
        # Get preview (first 5 lines)
        lines = request.content.split('\n')[:5]
        preview = '\n'.join(lines)
        
        # Store in prompt_sessions for code generation agent
        if session_id not in prompt_sessions:
            prompt_sessions[session_id] = {'csv': None, 'tables': [], 'postgres_tables': []}
        
        prompt_sessions[session_id]['csv'] = {
            'filename': request.filename,
            's3_path': s3_uri,
            'preview': preview
        }
        
        print(f"✅ CSV uploaded to {s3_uri}")
        print(f"   Stored in session {session_id}")
        
        return {
            "success": True,
            "s3_uri": s3_uri,
            "bucket": bucket,
            "key": s3_key,
            "preview": preview
        }
    except Exception as e:
        print(f"❌ CSV upload failed: {e}")
        return {
            "success": False,
            "error": str(e)
        }

@app.get("/history/{session_id}")
async def get_session_history(session_id: str):
    """Get session history"""
    try:
        if session_id in sessions:
            session = sessions[session_id]
            return {
                "success": True,
                "session_id": session_id,
                "conversation_history": session.conversation_history,
                "execution_results": session.execution_results
            }
        
        # Return empty history for new sessions
        return {
            "success": True,
            "session_id": session_id,
            "conversation_history": [],
            "execution_results": []
        }
    except Exception as e:
        print(f"Failed to get session history: {e}")
        return {
            "success": False,
            "session_id": session_id,
            "conversation_history": [],
            "execution_results": [],
            "error": str(e)
        }


@app.get("/glue/databases")
async def list_databases():
    """List all Glue databases"""
    try:
        glue_client = boto3.client('glue', region_name='us-east-1')
        response = glue_client.get_databases()
        databases = [db['Name'] for db in response.get('DatabaseList', [])]
        return {"success": True, "databases": databases}
    except Exception as e:
        print(f"Failed to list databases: {e}")
        return {"success": False, "error": str(e), "databases": []}

@app.get("/glue/tables/{database}")
async def list_tables(database: str):
    """List tables in a Glue database"""
    try:
        glue_client = boto3.client('glue', region_name='us-east-1')
        response = glue_client.get_tables(DatabaseName=database)
        tables = []
        for table in response.get('TableList', []):
            tables.append({
                "name": table['Name'],
                "location": table.get('StorageDescriptor', {}).get('Location', ''),
                "columns": [
                    {"name": col['Name'], "type": col['Type']}
                    for col in table.get('StorageDescriptor', {}).get('Columns', [])[:5]
                ]
            })
        return {"success": True, "tables": tables}
    except Exception as e:
        print(f"Failed to list tables: {e}")
        return {"success": False, "error": str(e), "tables": []}

class TableSelectionRequest(BaseModel):
    tables: List[Dict[str, str]]
    session_id: str

@app.post("/sessions/{session_id}/select-tables")
async def select_tables(session_id: str, request: TableSelectionRequest):
    """Set selected tables for session"""
    try:
        glue_client = boto3.client('glue', region_name='us-east-1')
        selected_tables = []
        for table_ref in request.tables:
            try:
                response = glue_client.get_table(
                    DatabaseName=table_ref['database'],
                    Name=table_ref['table']
                )
                table = response['Table']
                selected_tables.append({
                    'database': table_ref['database'],
                    'table': table_ref['table'],
                    'location': table.get('StorageDescriptor', {}).get('Location', '')
                })
            except Exception as e:
                print(f"Error getting table {table_ref['database']}.{table_ref['table']}: {e}")
        
        # Initialize session if new
        if session_id not in prompt_sessions:
            prompt_sessions[session_id] = {'csv': None, 'tables': [], 'postgres_tables': []}
        
        # Update only Glue tables (preserve postgres_tables)
        prompt_sessions[session_id]['tables'] = selected_tables
        
        print(f"✅ Selected {len(selected_tables)} Glue tables for session {session_id}")
        for t in selected_tables:
            print(f"   • {t['database']}.{t['table']} → {t['location']}")
        
        return {"success": True, "selected_tables": selected_tables}
    except Exception as e:
        print(f"Failed to select tables: {e}")
        return {"success": False, "error": str(e)}

# PostgreSQL endpoints
class PostgresConnectionRequest(BaseModel):
    name: str
    host: str
    port: int = 5432
    database: str = "postgres"
    auth_method: str  # 'secrets_manager', 'iam', 'user_password'
    secret_arn: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

class PostgresTestConnectionRequest(BaseModel):
    host: str
    port: int = 5432
    database: str = "postgres"
    auth_method: str
    secret_arn: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None

@app.post("/postgres/test-connection")
async def test_postgres_connection(request: PostgresTestConnectionRequest):
    """Test PostgreSQL connection"""
    try:
        import psycopg2
        
        if request.auth_method == 'secrets_manager':
            if not request.secret_arn:
                return {"success": False, "message": "Secret ARN required"}
            
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            secret = secrets_client.get_secret_value(SecretId=request.secret_arn)
            creds = json.loads(secret['SecretString'])
            
            conn = psycopg2.connect(
                host=creds['host'],
                port=creds['port'],
                database=creds['database'],
                user=creds['username'],
                password=creds['password'],
                connect_timeout=10
            )
            
        elif request.auth_method == 'iam':
            rds_client = boto3.client('rds', region_name='us-east-1')
            token = rds_client.generate_db_auth_token(
                DBHostname=request.host,
                Port=request.port,
                DBUsername=request.username or 'postgres',
                Region='us-east-1'
            )
            
            conn = psycopg2.connect(
                host=request.host,
                port=request.port,
                database=request.database,
                user=request.username or 'postgres',
                password=token,
                connect_timeout=10,
                sslmode='require'
            )
            
        elif request.auth_method == 'user_password':
            if not request.username or not request.password:
                return {"success": False, "message": "Username and password required"}
            
            conn = psycopg2.connect(
                host=request.host,
                port=request.port,
                database=request.database,
                user=request.username,
                password=request.password,
                connect_timeout=10
            )
        
        # Test query
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return {
            "success": True,
            "message": f"Connection successful! {version.split(',')[0]}"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Connection failed: {str(e)}"
        }

@app.post("/postgres/connections")
async def create_postgres_connection(request: PostgresConnectionRequest):
    """Create a new PostgreSQL connection"""
    try:
        import uuid
        config = load_config()
        
        # Validate auth method
        if request.auth_method not in ['secrets_manager', 'iam', 'user_password']:
            return {"success": False, "error": "Invalid authentication method"}
        
        # Handle different auth methods
        if request.auth_method == 'secrets_manager':
            if not request.secret_arn:
                return {"success": False, "error": "Secret ARN required for Secrets Manager auth"}
            secret_arn = request.secret_arn
            
        elif request.auth_method == 'user_password':
            if not request.username or not request.password:
                return {"success": False, "error": "Username and password required"}
            
            # Create secret in Secrets Manager for secure storage
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            secret_name = f"spark/postgres/{request.name}-{uuid.uuid4().hex[:8]}"
            
            secret_value = {
                "connection_name": request.name,
                "host": request.host,
                "port": request.port,
                "database": request.database,
                "username": request.username,
                "password": request.password,
                "jdbc_url": f"jdbc:postgresql://{request.host}:{request.port}/{request.database}"
            }
            
            response = secrets_client.create_secret(
                Name=secret_name,
                Description=f"PostgreSQL connection for {request.name}",
                SecretString=json.dumps(secret_value)
            )
            secret_arn = response['ARN']
            
        elif request.auth_method == 'iam':
            # For IAM auth, create a secret with connection details but no password
            secrets_client = boto3.client('secretsmanager', region_name='us-east-1')
            secret_name = f"spark/postgres/{request.name}-{uuid.uuid4().hex[:8]}"
            
            secret_value = {
                "connection_name": request.name,
                "host": request.host,
                "port": request.port,
                "database": request.database,
                "username": request.username or "postgres",
                "auth_method": "iam",
                "jdbc_url": f"jdbc:postgresql://{request.host}:{request.port}/{request.database}"
            }
            
            response = secrets_client.create_secret(
                Name=secret_name,
                Description=f"PostgreSQL connection for {request.name} (IAM auth)",
                SecretString=json.dumps(secret_value)
            )
            secret_arn = response['ARN']
        
        # Add connection to config
        new_connection = {
            "name": request.name,
            "secret_arn": secret_arn,
            "description": f"{request.host}:{request.port}/{request.database}",
            "enabled": True,
            "auth_method": request.auth_method,
            "host": request.host,
            "port": request.port,
            "database": request.database
        }
        
        if 'postgres' not in config:
            config['postgres'] = {'connections': []}
        if 'connections' not in config['postgres']:
            config['postgres']['connections'] = []
        
        config['postgres']['connections'].append(new_connection)
        save_config(config)
        
        return {
            "success": True,
            "connection": {
                "name": new_connection['name'],
                "description": new_connection['description'],
                "enabled": True,
                "host": request.host,
                "port": request.port,
                "database": request.database,
                "auth_method": request.auth_method,
                "secret_arn": secret_arn
            }
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/postgres/connections")
async def list_postgres_connections():
    """List all configured PostgreSQL connections"""
    try:
        from postgres_metadata import get_postgres_metadata_fetcher
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        return {
            "success": True,
            "connections": [
                {
                    "name": c['name'],
                    "description": c.get('description', ''),
                    "enabled": c.get('enabled', True)
                }
                for c in connections if c.get('enabled', True)
            ]
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/postgres/{connection_name}/databases")
async def list_postgres_databases(connection_name: str):
    """List all databases in a PostgreSQL connection"""
    try:
        from postgres_metadata import get_postgres_metadata_fetcher
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        databases = fetcher.list_databases(conn['secret_arn'])
        
        return {"success": True, "databases": databases}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/postgres/{connection_name}/schemas/{database}")
async def list_postgres_schemas(connection_name: str, database: str):
    """List schemas in a database"""
    try:
        from postgres_metadata import get_postgres_metadata_fetcher
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        schemas = fetcher.list_schemas(conn['secret_arn'], database)
        
        return {"success": True, "schemas": schemas}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/postgres/{connection_name}/tables/{database}/{schema}")
async def list_postgres_tables(connection_name: str, database: str, schema: str):
    """List tables with column metadata"""
    try:
        from postgres_metadata import get_postgres_metadata_fetcher
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        tables = fetcher.list_tables(conn['secret_arn'], database, schema)
        
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "error": str(e)}

class PostgresTableSelectionRequest(BaseModel):
    connection_name: str
    tables: List[Dict[str, str]]

@app.post("/sessions/{session_id}/select-postgres-tables")
async def select_postgres_tables(session_id: str, request: PostgresTableSelectionRequest):
    """Store selected PostgreSQL tables in session"""
    try:
        from postgres_metadata import get_postgres_metadata_fetcher
        config = load_config()
        connections = config.get('postgres', {}).get('connections', [])
        conn = next((c for c in connections if c['name'] == request.connection_name), None)
        
        if not conn:
            return {"success": False, "error": "Connection not found"}
        
        fetcher = get_postgres_metadata_fetcher()
        selected_tables = []
        
        for table_ref in request.tables:
            schema_info = fetcher.get_table_schema(
                conn['secret_arn'],
                table_ref['database'],
                table_ref['schema'],
                table_ref['table']
            )
            selected_tables.append({
                'connection_name': request.connection_name,
                'secret_arn': conn['secret_arn'],
                'auth_method': conn.get('auth_method', 'secrets_manager'),
                'host': conn.get('host'),
                'port': conn.get('port'),
                'database': table_ref['database'],
                **schema_info
            })
        
        # Initialize session if new
        if session_id not in prompt_sessions:
            prompt_sessions[session_id] = {'csv': None, 'tables': [], 'postgres_tables': []}
        
        # Update only PostgreSQL tables (preserve Glue tables)
        prompt_sessions[session_id]['postgres_tables'] = selected_tables
        
        print(f"✅ Selected {len(selected_tables)} PostgreSQL tables for session {session_id}")
        for t in selected_tables:
            print(f"   • {t.get('schema', '')}.{t.get('table', '')}")
        
        return {"success": True, "selected_tables": selected_tables}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/settings")
async def get_settings():
    """Get current settings"""
    config = load_config()
    return {
        "ray_cluster": config.get("ray_cluster", {}),
        "s3": config.get("s3", {}),
        "global": config.get("global", {}),
        "spark": config.get("spark", {}),
        "ray": config.get("ray", {})
    }

@app.post("/settings")
async def update_settings(settings: SettingsRequest):
    """Update settings"""
    try:
        config = load_config()
        config["ray_cluster"]["private_ip"] = settings.ray_private_ip
        config["ray_cluster"]["public_ip"] = settings.ray_public_ip
        config["s3"]["bucket"] = settings.s3_bucket
        
        # Update Ray settings
        if "ray" not in config:
            config["ray"] = {}
        config["ray"]["gateway_url"] = settings.ray_gateway_url
        config["ray"]["supervisor_arn"] = settings.ray_supervisor_arn
        
        # Update global settings
        if "global" not in config:
            config["global"] = {}
        config["global"]["bedrock_model"] = settings.global_bedrock_model
        config["global"]["code_gen_agent_arn"] = settings.global_code_gen_agent_arn
        config["global"]["bedrock_region"] = settings.global_bedrock_region
        
        # Update Spark settings
        if "spark" not in config:
            config["spark"] = {}
        config["spark"]["s3_bucket"] = settings.spark_s3_bucket
        config["spark"]["lambda_function"] = settings.spark_lambda_function
        config["spark"]["emr_application_id"] = settings.spark_emr_application_id
        config["spark"]["max_retries"] = settings.spark_max_retries
        config["spark"]["file_size_threshold_mb"] = settings.spark_file_size_threshold_mb
        config["spark"]["result_preview_rows"] = settings.spark_result_preview_rows
        config["spark"]["presigned_url_expiry_hours"] = settings.spark_presigned_url_expiry_hours
        config["spark"]["lambda_timeout_seconds"] = settings.spark_lambda_timeout_seconds
        config["spark"]["emr_timeout_minutes"] = settings.spark_emr_timeout_minutes
        config["spark"]["supervisor_arn"] = settings.spark_supervisor_arn
        
        save_config(config)
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/claude-models")
async def get_claude_models():
    """Get available Claude and Nova models using cross-region inference profiles"""
    return {
        "models": [
            {"id": "us.anthropic.claude-haiku-4-5-20251001-v1:0", "name": "Claude 4.5 Haiku"},
            {"id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "name": "Claude 4.5 Sonnet"},
            {"id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0", "name": "Claude 3.7 Sonnet"},
            {"id": "us.anthropic.claude-3-5-haiku-20241022-v1:0", "name": "Claude 3.5 Haiku"},
            {"id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet v2"},
            {"id": "us.anthropic.claude-3-5-sonnet-20240620-v1:0", "name": "Claude 3.5 Sonnet v1"},
            {"id": "us.anthropic.claude-3-opus-20240229-v1:0", "name": "Claude 3 Opus"},
            {"id": "us.anthropic.claude-3-sonnet-20240229-v1:0", "name": "Claude 3 Sonnet"},
            {"id": "us.anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku"},
            {"id": "us.amazon.nova-pro-v1:0", "name": "Amazon Nova Pro"},
            {"id": "us.amazon.nova-lite-v1:0", "name": "Amazon Nova Lite"},
            {"id": "us.amazon.nova-micro-v1:0", "name": "Amazon Nova Micro"}
        ]
    }

@app.post("/settings/restore-defaults")
async def restore_default_settings():
    """Restore default settings"""
    try:
        default_config = get_default_config()
        save_config(default_config)
        return {"success": True, "message": "Settings restored to defaults"}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Ray Code Interpreter API with Supervisor Agent Runtime + MCP Gateway",
        "architecture": "User → FastAPI → Supervisor Runtime → Code Gen Runtime + MCP Gateway → Ray Cluster",
        "endpoints": {
            "/generate": "POST - Generate Ray code via Supervisor Agent",
            "/execute": "POST - Execute Ray code via MCP Gateway", 
            "/ray/status": "GET - Ray cluster status and dashboard URL",
            "/ray/jobs": "GET - List Ray jobs",
            "/ray/jobs/{job_id}/stop": "POST - Stop Ray job",
            "/sessions/{session_id}/reset": "POST - Reset session data",
            "/upload-csv": "POST - Upload CSV file to S3",
            "/history/{session_id}": "GET - Get session history",
            "/settings": "GET/POST - Get/Update settings",
            "/health": "GET - Health check",
            "/": "GET - API information"
        },
        "supervisor_agent_arn": load_config().get("ray", {}).get("supervisor_arn", "not configured"),
        "ray_private_ip": get_ray_private_ip(),
        "ray_public_ip": get_ray_public_ip(),
        "s3_bucket": get_s3_bucket(),
        "mcp_gateway_url": MCP_GATEWAY_URL
    }

# ============================================================================
# SPARK FRAMEWORK ENDPOINTS
# ============================================================================

class TableReference(BaseModel):
    database: str
    table: str

class SparkGenerateRequest(BaseModel):
    prompt: str
    session_id: str
    framework: str = FRAMEWORK_SPARK
    s3_input_path: Optional[str] = None
    s3_output_path: Optional[str] = None
    selected_tables: Optional[List[TableReference]] = None
    selected_postgres_tables: Optional[List[dict]] = None
    execution_platform: str = "lambda"
    execution_engine: str = "auto"

@app.post("/spark/generate")
async def generate_spark_code(request: SparkGenerateRequest):
    """Generate, validate, and execute Spark code via Spark Supervisor Agent"""
    print(f"🔵 Received Spark generate request: {request.prompt[:50]}...")
    print(f"🔍 DEBUG - Full request: {request.dict()}", flush=True)
    import sys
    print(f"🔍 DEBUG - Full request: {request.dict()}", file=sys.stderr, flush=True)
    import time
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def invoke_spark_agent(payload_data, session_id_val, attempt_num):
        """Synchronous function to invoke agent"""
        try:
            # Create client with aligned timeouts (boto3 < asyncio)
            # EMR Serverless cold start + job execution can take 15-20 minutes
            spark_client = boto3.client(
                'bedrock-agentcore',
                region_name='us-east-1',
                config=boto3.session.Config(
                    read_timeout=1200,  # 20 minutes - allows for EMR cold start + execution
                    connect_timeout=30,
                    retries={'max_attempts': 0}
                )
            )
            
            print(f"🔵 Invoking Spark agent (attempt {attempt_num + 1})")
            
            # Get Spark supervisor ARN from config
            config = load_config()
            spark_supervisor_arn = config.get("spark", {}).get("supervisor_arn")
            
            response = spark_client.invoke_agent_runtime(
                agentRuntimeArn=spark_supervisor_arn,
                qualifier="DEFAULT",
                runtimeSessionId=session_id_val,
                payload=json.dumps(payload_data)
            )
            
            print(f"🔵 Reading agent response...")
            # Read the streaming response body
            response_body = response["response"].read()
            print(f"🔵 Response received: {len(response_body)} bytes")
            
            if not response_body:
                return {"success": False, "error": "No response from agent"}
            
            # Parse JSON response from agent
            try:
                result_text = response_body.decode('utf-8')
                agent_result = json.loads(result_text)
                
                # Handle multiple levels of JSON encoding
                while isinstance(agent_result, str):
                    try:
                        agent_result = json.loads(agent_result)
                    except:
                        break
                
                # Ensure agent_result is a dict
                if not isinstance(agent_result, dict):
                    return {"success": False, "error": f"Agent returned non-dict: {type(agent_result)}, value: {str(agent_result)[:200]}"}
                
                # Agent returns: {"validated_code": ..., "execution_result": ..., "data": ..., "s3_output_path": ...}
                
                # Store in session history
                if session_id_val not in sessions:
                    sessions[session_id_val] = SessionManager(session_id_val)
                
                session = sessions[session_id_val]
                
                # Store conversation history
                session.conversation_history.append({
                    'type': 'generation',
                    'prompt': payload_data.get('prompt', ''),
                    'generated_code': agent_result.get('spark_code', ''),
                    'timestamp': time.time(),
                    'framework': 'spark'
                })
                
                # Store execution results if execution was performed
                if agent_result.get('execution_result') == 'success':
                    session.execution_results.append({
                        'code': agent_result.get('spark_code', ''),
                        'result': agent_result.get('execution_message', ''),
                        'timestamp': time.time(),
                        'success': True,
                        'framework': 'spark'
                    })
                
                return {
                    "success": True,
                    "result": agent_result,
                    "framework": FRAMEWORK_SPARK,
                    "execution_platform": execution_platform
                }
            except json.JSONDecodeError as json_err:
                # Fallback: return error
                return {"success": False, "error": f"JSON decode error: {str(json_err)}, text: {result_text[:200]}"}
        except Exception as e:
            error_str = str(e)
            if "throttlingException" in error_str or "ThrottlingException" in error_str:
                return {"throttled": True, "attempt": attempt_num}
            raise
    
    try:
        config = load_config()
        spark_supervisor_arn = config.get("spark", {}).get("supervisor_arn")
        if not spark_supervisor_arn:
            return {"success": False, "error": "Spark supervisor not configured"}
        
        import uuid
        if request.session_id and len(request.session_id) >= 33:
            session_id = request.session_id
        else:
            session_id = f"spark-session-{uuid.uuid4().hex}"
        
        # Set output path to session-specific location from config
        config = load_config()
        s3_bucket = config.get("spark", {}).get("s3_bucket", "spark-data-260005718447-us-east-1")
        s3_output_path = request.s3_output_path or f"s3://{s3_bucket}/output/{session_id}"
        
        # Convert selected_tables from objects to "database.table" strings
        selected_tables_list = None
        if request.selected_tables:
            selected_tables_list = [f"{t.database}.{t.table}" for t in request.selected_tables]
        
        # Get PostgreSQL tables from request or session
        selected_postgres_tables = request.selected_postgres_tables
        if not selected_postgres_tables and session_id in prompt_sessions:
            selected_postgres_tables = prompt_sessions[session_id].get('postgres_tables')
        
        print(f"🔍 DEBUG - selected_postgres_tables: {selected_postgres_tables}")
        print(f"🔍 DEBUG - selected_tables_list: {selected_tables_list}")
        
        # Determine execution platform
        if selected_postgres_tables:
            # PostgreSQL requires EMR with VPC access
            execution_platform = 'emr'
            print(f"🔍 DEBUG - Routing to EMR for PostgreSQL")
        elif selected_tables_list:
            # Glue tables use EMR for Glue Data Catalog access
            execution_platform = 'emr'
            print(f"🔍 DEBUG - Routing to EMR for Glue tables")
        else:
            execution_platform = request.execution_engine if request.execution_engine != 'auto' else request.execution_platform
            print(f"🔍 DEBUG - Routing to {execution_platform}")
        
        # Merge global and spark settings for the payload
        config = load_config()
        spark_config = config.get("spark", {}).copy()
        global_config = config.get("global", {})
        
        # Add global settings to spark config
        if "bedrock_model" in global_config:
            spark_config["model_id"] = global_config["bedrock_model"]  # Use model_id key for agents
        if "code_gen_agent_arn" in global_config:
            spark_config["code_gen_agent_arn"] = global_config["code_gen_agent_arn"]
        if "bedrock_region" in global_config:
            spark_config["bedrock_region"] = global_config["bedrock_region"]
        
        # Backend determines which EMR application to use
        if selected_postgres_tables:
            # Use PostgreSQL-enabled EMR for VPC access
            spark_config["emr_application_id"] = spark_config.get("emr_postgres_application_id")
            spark_config["jdbc_driver_path"] = config.get("postgres", {}).get("jdbc_driver_path")
            print(f"🔍 DEBUG - Using PostgreSQL EMR app: {spark_config['emr_application_id']}")
        elif selected_tables_list:
            # Explicitly use default EMR application for Glue tables (no VPC, no JDBC)
            spark_config["emr_application_id"] = config.get("spark", {}).get("emr_application_id")
            spark_config.pop("jdbc_driver_path", None)  # Remove JDBC driver if present
            print(f"🔍 DEBUG - Using Glue EMR app: {spark_config['emr_application_id']}")
        # else: use default emr_application_id for CSV/generic requests
        
        payload = {
            "prompt": request.prompt,
            "session_id": session_id,
            "s3_input_path": request.s3_input_path,
            "s3_output_path": s3_output_path,
            "selected_tables": selected_tables_list,
            "selected_postgres_tables": selected_postgres_tables,
            "execution_platform": execution_platform,
            "skip_generation": False,
            "config": spark_config
        }
        
        # Retry logic for throttling
        max_retries = 3
        for attempt in range(max_retries):
            print(f"🔵 Spark agent attempt {attempt + 1}/{max_retries}")
            
            try:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, invoke_spark_agent, payload, session_id, attempt
                    ),
                    timeout=1260  # 21 minute timeout (boto3 times out first at 20 min)
                )
            except asyncio.TimeoutError:
                print(f"⏱️ Attempt {attempt + 1} timed out")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2)
                    continue
                return {"success": False, "error": "Agent timed out"}
            
            if result.get("throttled"):
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) + 1
                    print(f"⏳ Throttled, retrying in {wait_time}s (attempt {attempt + 1}/{max_retries})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    return {"success": False, "error": "Request throttled after retries"}
            
            return result
            
    except Exception as e:
        print(f"❌ Spark generation failed: {e}")
        return {"success": False, "error": str(e)}

class SparkExecuteRequest(BaseModel):
    spark_code: str
    session_id: str
    s3_output_path: Optional[str] = None
    execution_platform: str = "lambda"
    execution_engine: str = "auto"

@app.post("/spark/execute")
async def execute_spark_code_endpoint(request: SparkExecuteRequest):
    """Execute Spark code via Spark Supervisor Agent"""
    import asyncio
    
    try:
        config = load_config()
        spark_supervisor_arn = config.get("spark", {}).get("supervisor_arn")
        if not spark_supervisor_arn:
            return {"success": False, "error": "Spark supervisor not configured"}
        
        import uuid
        session_id = request.session_id if (request.session_id and len(request.session_id) >= 33) else f"spark-exec-{uuid.uuid4().hex}"
        
        # Determine execution platform
        execution_platform = request.execution_platform if request.execution_platform != 'auto' else 'lambda'
        
        s3_bucket = config.get("spark", {}).get("s3_bucket", "spark-data-260005718447-us-east-1")
        s3_output_path = request.s3_output_path or f"s3://{s3_bucket}/output/{session_id}"
        
        # Merge global and spark settings for the payload (same as generate endpoint)
        config = load_config()
        spark_config = config.get("spark", {}).copy()
        global_config = config.get("global", {})
        
        # Add global settings to spark config
        if "bedrock_model" in global_config:
            spark_config["model_id"] = global_config["bedrock_model"]  # Use model_id key for agents
        if "code_gen_agent_arn" in global_config:
            spark_config["code_gen_agent_arn"] = global_config["code_gen_agent_arn"]
        if "bedrock_region" in global_config:
            spark_config["bedrock_region"] = global_config["bedrock_region"]
        
        # Create payload for execution only (skip code generation)
        payload = {
            "spark_code": request.spark_code,
            "session_id": session_id,
            "s3_output_path": s3_output_path,
            "execution_platform": execution_platform,
            "skip_generation": True,
            "config": spark_config
        }
        
        # Invoke agent
        spark_client = boto3.client(
            'bedrock-agentcore',
            region_name='us-east-1',
            config=boto3.session.Config(
                read_timeout=1200,  # 20 minutes for EMR workloads
                connect_timeout=30,
                retries={'max_attempts': 0}
            )
        )
        
        response = spark_client.invoke_agent_runtime(
            agentRuntimeArn=spark_supervisor_arn,
            qualifier="DEFAULT",
            runtimeSessionId=session_id,
            payload=json.dumps(payload)
        )
        
        response_body = response["response"].read()
        if not response_body:
            return {"success": False, "error": "No response from agent"}
        
        # Parse response
        result_text = response_body.decode('utf-8')
        agent_result = json.loads(result_text)
        
        # Handle multiple levels of JSON encoding
        while isinstance(agent_result, str):
            try:
                agent_result = json.loads(agent_result)
            except:
                break
        
        if not isinstance(agent_result, dict):
            return {"success": False, "error": f"Invalid response format"}
        
        # Store in session history
        if session_id not in sessions:
            sessions[session_id] = SessionManager(session_id)
        
        session = sessions[session_id]
        
        # Store execution results
        session.execution_results.append({
            'code': request.spark_code,
            'result': agent_result.get('execution_message', ''),
            'timestamp': time.time(),
            'success': agent_result.get('execution_result') == 'success',
            'framework': 'spark'
        })
        
        return {
            "success": True,
            "result": agent_result,
            "framework": FRAMEWORK_SPARK
        }
        
    except Exception as e:
        print(f"❌ Spark execution failed: {e}")
        return {"success": False, "error": str(e)}

@app.get("/spark/config")
async def get_spark_config():
    """Get Spark configuration"""
    return {
        "s3_bucket": "spark-data-260005718447-us-east-1",
        "lambda_function": "sparkOnLambda-spark-code-interpreter",
        "emr_application_id": "00fv6g7rptsov009",
        "bedrock_region": "us-east-1",
        "bedrock_model": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "max_retries": 5,
        "file_size_threshold_mb": 500,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "lambda_timeout_seconds": 300,
        "emr_timeout_minutes": 60
    }

@app.get("/spark/status")
async def spark_status():
    """Check Spark Lambda and EMR status"""
    lambda_status = "unknown"
    emr_status = "unknown"
    
    try:
        # Check Lambda function
        lambda_client = boto3.client('lambda', region_name='us-east-1')
        lambda_response = lambda_client.get_function(
            FunctionName='sparkOnLambda-spark-code-interpreter'
        )
        lambda_status = "ready" if lambda_response['Configuration']['State'] == 'Active' else "not_ready"
    except Exception as e:
        lambda_status = "error"
    
    try:
        # Check EMR Serverless application
        emr_client = boto3.client('emr-serverless', region_name='us-east-1')
        emr_response = emr_client.get_application(
            applicationId='00fv6g7rptsov009'
        )
        app = emr_response['application']
        state = app['state']
        auto_start = app.get('autoStartConfiguration', {}).get('enabled', False)
        
        # Ready if state is CREATED/STARTED/STOPPED and autoStart is enabled
        emr_status = "ready" if state in ['CREATED', 'STARTED', 'STOPPED'] and auto_start else "not ready"
    except Exception as e:
        emr_status = "error"
    
    return {
        "lambda_status": lambda_status,
        "emr_status": emr_status,
        "lambda_function": "sparkOnLambda-spark-code-interpreter",
        "emr_application_id": "00fv6g7rptsov009"
    }

@app.post("/spark/upload-csv")
async def upload_spark_csv(request: CsvUploadRequest):
    """Upload CSV file to Spark S3 bucket"""
    try:
        s3_client = boto3.client('s3', region_name='us-east-1')
        bucket = "spark-data-260005718447-us-east-1"
        
        # Upload to root of Spark bucket
        s3_key = request.filename
        
        s3_client.put_object(
            Bucket=bucket,
            Key=s3_key,
            Body=request.content.encode('utf-8'),
            ContentType='text/csv'
        )
        
        s3_uri = f"s3://{bucket}/{s3_key}"
        
        # Get preview
        lines = request.content.split('\n')[:5]
        preview = '\n'.join(lines)
        
        return {
            "success": True,
            "s3_path": s3_uri,
            "filename": request.filename,
            "preview": preview
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

