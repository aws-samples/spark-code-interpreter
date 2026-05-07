"""Spark Code Interpreter - FastAPI Backend

Provides REST API for the React frontend to generate, execute, and manage
PySpark code via the Spark Supervisor Agent on AgentCore.
"""

import json
import time
import os
import logging
import uuid
from typing import Optional, List, Dict
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import boto3
import asyncio
from concurrent.futures import ThreadPoolExecutor
from config import load_config, save_config, get_spark_settings, get_s3_bucket

logger = logging.getLogger(__name__)

app = FastAPI(title="Spark Code Interpreter API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session storage
sessions: Dict[str, dict] = {}

# Thread pool for blocking boto3 calls
executor = ThreadPoolExecutor(max_workers=4)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    s3_input_path: Optional[str] = None
    s3_sample_path: Optional[str] = None
    selected_tables: Optional[List[dict]] = None
    selected_postgres_tables: Optional[List[dict]] = None
    execution_engine: Optional[str] = "auto"


class ExecuteRequest(BaseModel):
    spark_code: str
    session_id: Optional[str] = None
    s3_output_path: Optional[str] = None
    execution_platform: Optional[str] = "lambda"


class CsvUploadRequest(BaseModel):
    filename: str
    content: str
    session_id: Optional[str] = None


class TableSelectionRequest(BaseModel):
    tables: List[dict]


class PostgresConnectionRequest(BaseModel):
    name: str
    secret_arn: str
    description: Optional[str] = ""
    auth_method: Optional[str] = "secrets_manager"
    host: Optional[str] = None
    port: Optional[int] = 5432


# ---------------------------------------------------------------------------
# Helper: invoke Spark Supervisor Agent
# ---------------------------------------------------------------------------

def _invoke_spark_agent(payload: dict, session_id: str) -> dict:
    """Synchronous call to the Spark Supervisor Agent on AgentCore."""
    config = load_config()
    supervisor_arn = config.get("spark", {}).get("supervisor_arn")
    if not supervisor_arn:
        return {"success": False, "error": "Spark supervisor agent not configured"}

    client = boto3.client(
        "bedrock-agentcore",
        region_name=config.get("global", {}).get("bedrock_region", "us-east-1"),
        config=boto3.session.Config(read_timeout=1200, connect_timeout=30, retries={"max_attempts": 0}),
    )

    response = client.invoke_agent_runtime(
        agentRuntimeArn=supervisor_arn,
        qualifier="DEFAULT",
        runtimeSessionId=session_id,
        payload=json.dumps(payload),
    )

    body = response["response"].read().decode("utf-8")
    if not body:
        return {"success": False, "error": "Empty response from agent"}

    result = json.loads(body)
    while isinstance(result, str):
        try:
            result = json.loads(result)
        except Exception:
            break

    if not isinstance(result, dict):
        return {"success": False, "error": f"Unexpected response type: {type(result)}"}

    return {"success": True, "result": result}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/generate")
async def generate_code(request: GenerateRequest):
    """Generate, validate, and execute Spark code via the Supervisor Agent."""
    config = load_config()
    spark = config.get("spark", {})
    s3_bucket = spark.get("s3_bucket", "")

    session_id = request.session_id or f"spark-{uuid.uuid4().hex}"
    if len(session_id) < 33:
        session_id = f"spark-session-{uuid.uuid4().hex}"
    s3_output_path = f"s3://{s3_bucket}/{session_id}/output/"

    payload = {
        "prompt": request.prompt,
        "session_id": session_id,
        "s3_input_path": request.s3_input_path,
        "s3_sample_path": request.s3_sample_path,
        "s3_output_path": s3_output_path,
        "selected_tables": request.selected_tables,
        "selected_postgres_tables": request.selected_postgres_tables,
        "execution_platform": request.execution_engine or "auto",
        "config": {
            "model_id": config.get("global", {}).get("bedrock_model"),
            "bedrock_model": config.get("global", {}).get("bedrock_model"),
            "bedrock_region": config.get("global", {}).get("bedrock_region", "us-east-1"),
            "lambda_function": spark.get("lambda_function"),
            "lambda_arn": f"arn:aws:lambda:us-east-1:{_get_account_id()}:function:{spark.get('lambda_function', '')}",
            "s3_bucket": s3_bucket,
            "s3_output_path": s3_output_path,
            "code_gen_agent_arn": spark.get("code_gen_agent_arn") or config.get("global", {}).get("code_gen_agent_arn"),
            "internal_gateway_url": spark.get("internal_gateway_url", ""),
            "emr_application_id": spark.get("emr_application_id", ""),
            "emr_execution_role_arn": spark.get("emr_execution_role_arn", ""),
            "region": config.get("global", {}).get("bedrock_region", "us-east-1"),
            "result_preview_rows": spark.get("result_preview_rows", 100),
            "presigned_url_expiry_hours": spark.get("presigned_url_expiry_hours", 24),
            "emr_timeout_minutes": spark.get("emr_timeout_minutes", 10),
            "spark_config": {
                "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
                "spark.hadoop.fs.s3.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
                "spark.hadoop.fs.s3a.aws.credentials.provider": "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
            },
        },
    }

    # Add PostgreSQL config if tables selected
    postgres_config = config.get("postgres", {})
    if request.selected_postgres_tables and postgres_config.get("jdbc_driver_path"):
        payload["config"]["jdbc_driver_path"] = postgres_config["jdbc_driver_path"]

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(executor, _invoke_spark_agent, payload, session_id)
        result["execution_platform"] = request.execution_engine

        # Save to session history
        if result.get("success") and result.get("result"):
            agent_result = result["result"]
            sess = sessions.setdefault(session_id, {"conversation_history": [], "execution_results": []})
            sess["conversation_history"].append({
                "type": "generation",
                "prompt": request.prompt,
                "generated_code": agent_result.get("spark_code", ""),
                "execution_result": agent_result.get("execution_result", ""),
                "execution_message": agent_result.get("execution_message", ""),
                "actual_results": agent_result.get("actual_results", []),
                "s3_output_path": agent_result.get("s3_output_path", ""),
                "timestamp": time.time(),
            })
            if agent_result.get("execution_result") == "success":
                sess["execution_results"].append({
                    "code": agent_result.get("spark_code", ""),
                    "result": agent_result.get("execution_message", ""),
                    "data": agent_result.get("actual_results", []),
                    "success": True,
                    "timestamp": time.time(),
                })

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/execute")
async def execute_code(request: ExecuteRequest):
    """Execute pre-validated Spark code (skip generation)."""
    config = load_config()
    spark = config.get("spark", {})
    s3_bucket = spark.get("s3_bucket", "")

    session_id = request.session_id or f"spark-{uuid.uuid4().hex}"
    if len(session_id) < 33:
        session_id = f"spark-session-{uuid.uuid4().hex}"
    s3_output_path = request.s3_output_path or f"s3://{s3_bucket}/{session_id}/output/"

    payload = {
        "prompt": "",
        "spark_code": request.spark_code,
        "skip_generation": True,
        "session_id": session_id,
        "s3_output_path": s3_output_path,
        "execution_platform": request.execution_platform or "lambda",
        "config": {
            "model_id": config.get("global", {}).get("bedrock_model"),
            "bedrock_model": config.get("global", {}).get("bedrock_model"),
            "bedrock_region": config.get("global", {}).get("bedrock_region", "us-east-1"),
            "lambda_function": spark.get("lambda_function"),
            "s3_bucket": s3_bucket,
            "s3_output_path": s3_output_path,
            "code_gen_agent_arn": spark.get("code_gen_agent_arn") or config.get("global", {}).get("code_gen_agent_arn"),
            "internal_gateway_url": spark.get("internal_gateway_url", ""),
            "emr_application_id": spark.get("emr_application_id", ""),
            "emr_execution_role_arn": spark.get("emr_execution_role_arn", ""),
            "region": config.get("global", {}).get("bedrock_region", "us-east-1"),
            "result_preview_rows": spark.get("result_preview_rows", 100),
            "presigned_url_expiry_hours": spark.get("presigned_url_expiry_hours", 24),
            "emr_timeout_minutes": spark.get("emr_timeout_minutes", 10),
            "spark_config": {
                "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
                "spark.hadoop.fs.s3.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
                "spark.hadoop.fs.s3a.aws.credentials.provider": "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
            },
        },
    }

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(executor, _invoke_spark_agent, payload, session_id)
        result["execution_platform"] = request.execution_platform

        # Save to session history
        if result.get("success") and result.get("result"):
            agent_result = result["result"]
            sess = sessions.setdefault(session_id, {"conversation_history": [], "execution_results": []})
            sess["conversation_history"].append({
                "type": "execution",
                "code": request.spark_code,
                "execution_result": agent_result.get("execution_result", ""),
                "execution_message": agent_result.get("execution_message", ""),
                "actual_results": agent_result.get("actual_results", []),
                "s3_output_path": agent_result.get("s3_output_path", ""),
                "timestamp": time.time(),
            })
            if agent_result.get("execution_result") == "success":
                sess["execution_results"].append({
                    "code": request.spark_code,
                    "result": agent_result.get("execution_message", ""),
                    "data": agent_result.get("actual_results", []),
                    "success": True,
                    "timestamp": time.time(),
                })

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/upload-csv")
async def upload_csv(request: CsvUploadRequest):
    """Upload a CSV file to S3 and extract a 200-row sample for fast validation."""
    config = load_config()
    s3_bucket = config.get("spark", {}).get("s3_bucket", "")
    session_id = request.session_id or str(uuid.uuid4())

    s3_key = f"{session_id}/{request.filename}"
    s3_path = f"s3://{s3_bucket}/{s3_key}"

    s3 = boto3.client("s3", region_name=config.get("global", {}).get("bedrock_region", "us-east-1"))

    # Save full file
    s3.put_object(Bucket=s3_bucket, Key=s3_key, Body=request.content.encode("utf-8"))

    # Extract sample (header + 200 rows)
    lines = request.content.strip().split("\n")
    sample_lines = lines[:201]  # header + 200 data rows
    sample_content = "\n".join(sample_lines)
    sample_key = f"{session_id}/samples/{request.filename}"
    s3.put_object(Bucket=s3_bucket, Key=sample_key, Body=sample_content.encode("utf-8"))
    s3_sample_path = f"s3://{s3_bucket}/{sample_key}"

    # Preview (first 5 lines)
    preview = "\n".join(lines[:6])

    return {
        "success": True,
        "s3_path": s3_path,
        "s3_sample_path": s3_sample_path,
        "preview": preview,
        "filename": request.filename,
        "total_rows": len(lines) - 1,
        "sample_rows": min(200, len(lines) - 1),
    }


# ---------------------------------------------------------------------------
# Glue endpoints
# ---------------------------------------------------------------------------

@app.get("/glue/databases")
async def list_databases():
    config = load_config()
    try:
        glue = boto3.client("glue", region_name=config.get("global", {}).get("bedrock_region", "us-east-1"))
        response = glue.get_databases()
        return {"databases": [db["Name"] for db in response.get("DatabaseList", [])]}
    except Exception as e:
        return {"databases": [], "error": str(e)}


@app.get("/glue/tables/{database}")
async def list_tables(database: str):
    config = load_config()
    try:
        glue = boto3.client("glue", region_name=config.get("global", {}).get("bedrock_region", "us-east-1"))
        response = glue.get_tables(DatabaseName=database)
        tables = []
        for t in response.get("TableList", []):
            tables.append({
                "name": t["Name"],
                "database": database,
                "columns": [{"name": c["Name"], "type": c["Type"]} for c in t.get("StorageDescriptor", {}).get("Columns", [])],
                "location": t.get("StorageDescriptor", {}).get("Location", ""),
            })
        return {"tables": tables}
    except Exception as e:
        return {"tables": [], "error": str(e)}


@app.post("/sessions/{session_id}/select-tables")
async def select_tables(session_id: str, request: TableSelectionRequest):
    sessions.setdefault(session_id, {})["selected_tables"] = request.tables
    return {"success": True, "selected": len(request.tables)}


# ---------------------------------------------------------------------------
# PostgreSQL endpoints
# ---------------------------------------------------------------------------

@app.post("/postgres/test-connection")
async def test_postgres_connection(request: PostgresConnectionRequest):
    config = load_config()
    region = config.get("global", {}).get("bedrock_region", "us-east-1")
    try:
        secrets = boto3.client("secretsmanager", region_name=region)
        secret = secrets.get_secret_value(SecretId=request.secret_arn)
        creds = json.loads(secret["SecretString"])
        return {"success": True, "message": f"Connection to {request.name} verified", "username": creds.get("username", "")}
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/postgres/connections")
async def save_postgres_connection(request: PostgresConnectionRequest):
    config = load_config()
    connections = config.get("postgres", {}).get("connections", [])
    conn = request.dict()
    existing = next((i for i, c in enumerate(connections) if c["name"] == conn["name"]), None)
    if existing is not None:
        connections[existing] = conn
    else:
        connections.append(conn)
    config.setdefault("postgres", {})["connections"] = connections
    save_config(config)
    return {"success": True, "connection": conn}


@app.get("/postgres/connections")
async def list_postgres_connections():
    config = load_config()
    return {"connections": config.get("postgres", {}).get("connections", [])}


@app.get("/postgres/{connection_name}/databases")
async def list_postgres_databases(connection_name: str):
    config = load_config()
    conn = _find_postgres_connection(config, connection_name)
    if not conn:
        return {"error": f"Connection '{connection_name}' not found"}
    try:
        import psycopg2
        creds = _get_postgres_creds(config, conn["secret_arn"])
        host, port = _parse_jdbc_url(conn.get("jdbc_url", ""))
        db = psycopg2.connect(host=host, port=port, database="postgres", user=creds["username"], password=creds["password"])
        cur = db.cursor()
        cur.execute("SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname")
        databases = [row[0] for row in cur.fetchall()]
        cur.close()
        db.close()
        return {"databases": databases}
    except Exception as e:
        return {"error": str(e)}


@app.get("/postgres/{connection_name}/schemas/{database}")
async def list_postgres_schemas(connection_name: str, database: str):
    config = load_config()
    conn = _find_postgres_connection(config, connection_name)
    if not conn:
        return {"error": f"Connection '{connection_name}' not found"}
    try:
        import psycopg2
        creds = _get_postgres_creds(config, conn["secret_arn"])
        host, port = _parse_jdbc_url(conn.get("jdbc_url", ""))
        db = psycopg2.connect(host=host, port=port, database=database, user=creds["username"], password=creds["password"])
        cur = db.cursor()
        cur.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT IN ('pg_catalog','information_schema') ORDER BY schema_name")
        schemas = [row[0] for row in cur.fetchall()]
        cur.close()
        db.close()
        return {"schemas": schemas}
    except Exception as e:
        return {"error": str(e)}


@app.get("/postgres/{connection_name}/tables/{database}/{schema}")
async def list_postgres_tables(connection_name: str, database: str, schema: str):
    config = load_config()
    conn = _find_postgres_connection(config, connection_name)
    if not conn:
        return {"error": f"Connection '{connection_name}' not found"}
    try:
        import psycopg2
        creds = _get_postgres_creds(config, conn["secret_arn"])
        host, port = _parse_jdbc_url(conn.get("jdbc_url", ""))
        db = psycopg2.connect(host=host, port=port, database=database, user=creds["username"], password=creds["password"])
        cur = db.cursor()
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = %s ORDER BY table_name", (schema,))
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        db.close()
        return {"tables": tables}
    except Exception as e:
        return {"error": str(e)}


@app.post("/sessions/{session_id}/select-postgres-tables")
async def select_postgres_tables(session_id: str, request: TableSelectionRequest):
    sessions.setdefault(session_id, {})["selected_postgres_tables"] = request.tables
    return {"success": True, "selected": len(request.tables)}


def _find_postgres_connection(config, name):
    for c in config.get("postgres", {}).get("connections", []):
        if c["name"] == name:
            return c
    return None


def _get_postgres_creds(config, secret_arn):
    region = config.get("global", {}).get("bedrock_region", "us-east-1")
    secrets = boto3.client("secretsmanager", region_name=region)
    secret = secrets.get_secret_value(SecretId=secret_arn)
    return json.loads(secret["SecretString"])


def _parse_jdbc_url(jdbc_url):
    parts = jdbc_url.replace("jdbc:postgresql://", "").split("/")
    hp = parts[0].split(":")
    return hp[0], int(hp[1]) if len(hp) > 1 else 5432


# ---------------------------------------------------------------------------
# Settings & status
# ---------------------------------------------------------------------------

@app.get("/settings")
async def get_settings():
    return load_config()


@app.post("/settings")
async def update_settings(settings: dict):
    save_config(settings)
    return {"success": True}


@app.get("/status")
async def spark_status():
    config = load_config()
    spark = config.get("spark", {})
    return {
        "lambda_status": "ready" if spark.get("lambda_function") else "not_configured",
        "emr_status": "ready" if spark.get("emr_application_id") else "not_configured",
        "supervisor_arn": spark.get("supervisor_arn", ""),
        "s3_bucket": spark.get("s3_bucket", ""),
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "framework": "spark"}


@app.get("/progress/{session_id}")
async def get_progress(session_id: str):
    """Get real-time progress for a running generation/execution."""
    config = load_config()
    s3_bucket = config.get("spark", {}).get("s3_bucket", "")
    if not s3_bucket:
        return {"stages": [], "current_stage": None}

    try:
        s3 = boto3.client("s3", region_name=config.get("global", {}).get("bedrock_region", "us-east-1"))
        obj = s3.get_object(Bucket=s3_bucket, Key=f"{session_id}/progress.json")
        progress = json.loads(obj["Body"].read().decode("utf-8"))
        return progress
    except s3.exceptions.NoSuchKey:
        return {"stages": [], "current_stage": None}
    except Exception:
        return {"stages": [], "current_stage": None}


@app.get("/history/{session_id}")
async def get_history(session_id: str):
    return sessions.get(session_id, {"conversation_history": [], "execution_results": []})


@app.get("/claude-models")
async def list_models():
    return {
        "models": [
            {"id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0", "name": "Claude Sonnet 4.5"},
            {"id": "us.anthropic.claude-3-5-sonnet-20241022-v2:0", "name": "Claude 3.5 Sonnet v2"},
            {"id": "us.anthropic.claude-3-haiku-20240307-v1:0", "name": "Claude 3 Haiku"},
        ]
    }


# Cache account ID
_account_id = None

def _get_account_id():
    global _account_id
    if not _account_id:
        _account_id = boto3.client("sts").get_caller_identity()["Account"]
    return _account_id


@app.get("/")
async def root():
    return {"service": "Spark Code Interpreter", "version": "3.0.0", "status": "running"}
