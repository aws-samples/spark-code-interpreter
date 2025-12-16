import json
import os
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "settings.json"
YAML_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

DEFAULT_CONFIG = {
    "ray_cluster": {
        "private_ip": os.getenv("RAY_PRIVATE_IP", "172.31.80.237"),
        "public_ip": os.getenv("RAY_PUBLIC_IP", "54.173.21.137")
    },
    "s3": {
        "bucket": os.getenv("RAY_DATA_BUCKET", "strands-ray-data")
    },
    "ray": {
        "gateway_url": os.getenv("RAY_GATEWAY_URL", "https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"),
        "supervisor_arn": os.getenv("RAY_SUPERVISOR_ARN", "arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/supervisor_agent-caFwzSALky")
    },
    "global": {
        "bedrock_model": os.getenv("BEDROCK_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
        "code_gen_agent_arn": os.getenv("CODE_GEN_AGENT_ARN", "arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/ray_code_interpreter-oTKmLH9IB9"),
        "bedrock_region": os.getenv("AWS_DEFAULT_REGION", "us-east-1")
    },
    "spark": {
        "s3_bucket": os.getenv("DATA_BUCKET", "spark-data-025523569182-us-east-1"),
        "lambda_function": os.getenv("SPARK_LAMBDA_FUNCTION", "dev-spark-on-lambda"),
        "emr_application_id": os.getenv("EMR_APPLICATION_ID", "00g1k848jaqqjf09"),
        "emr_postgres_application_id": os.getenv("EMR_POSTGRES_APPLICATION_ID", "00g1k848jaqqjf09"),
        "max_retries": 3,
        "file_size_threshold_mb": 100,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "lambda_timeout_seconds": 300,
        "emr_timeout_minutes": 10,
        "supervisor_arn": os.getenv("SPARK_SUPERVISOR_ARN", "arn:aws:bedrock-agentcore:us-east-1:025523569182:runtime/spark_supervisor_agent-EZPQeDGCjR")
    },
    "postgres": {
        "connections": [],
        "default_connection": None,
        "jdbc_driver_path": "s3://spark-data-025523569182-us-east-1/jars/postgresql-42.7.8.jar",
        "secrets_manager_prefix": "spark/postgres/",
        "connection_timeout": 10,
        "query_timeout": 30,
        "use_dedicated_emr": True
    },
    "snowflake": {
        "enabled": os.getenv("SNOWFLAKE_ENABLED", "false").lower() == "true",
        "secret_name": os.getenv("SNOWFLAKE_SECRET_NAME", ""),
        "jdbc_driver_path": "s3://spark-data-025523569182-us-east-1/jars/snowflake-jdbc-3.14.4.jar",
        "connection_timeout": 30,
        "query_timeout": 300,
        "use_dedicated_emr": False  # Reuse existing EMR application
    }
}

def load_config():
    """Load configuration from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged = DEFAULT_CONFIG.copy()
                merged.update(config)
                return merged
        except:
            pass
    return DEFAULT_CONFIG.copy()

def load_ray_config_from_yaml():
    """Load Ray configuration from config.yaml"""
    if YAML_CONFIG_FILE.exists():
        try:
            with open(YAML_CONFIG_FILE, 'r') as f:
                return yaml.safe_load(f)
        except:
            pass
    return {}

def get_default_config():
    """Get default configuration including Ray settings from YAML"""
    config = DEFAULT_CONFIG.copy()
    
    # Load Ray settings from YAML if available and merge with defaults
    yaml_config = load_ray_config_from_yaml()
    if yaml_config and 'ray' in yaml_config:
        if 'ray' not in config:
            config['ray'] = {}
        config['ray'].update(yaml_config['ray'])
    
    return config

def save_config(config):
    """Save configuration to file"""
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_ray_private_ip():
    return load_config()["ray_cluster"]["private_ip"]

def get_ray_public_ip():
    return load_config()["ray_cluster"]["public_ip"]

def get_s3_bucket():
    return load_config()["s3"]["bucket"]

def get_spark_settings():
    return load_config().get("spark", DEFAULT_CONFIG["spark"])

def get_snowflake_settings():
    return load_config().get("snowflake", DEFAULT_CONFIG["snowflake"])
