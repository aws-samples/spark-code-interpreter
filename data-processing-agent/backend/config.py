import json
import os
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "settings.json"
YAML_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

DEFAULT_CONFIG = {
    "ray_cluster": {
        "private_ip": "172.31.80.237",
        "public_ip": "54.173.21.137"
    },
    "s3": {
        "bucket": "strands-ray-data"
    },
    "ray": {
        "gateway_url": "https://ray-validation-gateway-e9r35gofyj.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp",
        "supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/supervisor_agent-caFwzSALky"
    },
    "global": {
        "bedrock_model": "us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        "code_gen_agent_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/ray_code_interpreter-oTKmLH9IB9",
        "bedrock_region": "us-east-1"
    },
    "spark": {
        "s3_bucket": "spark-data-260005718447-us-east-1",
        "lambda_function": "sparkOnLambda-spark-code-interpreter",
        "emr_application_id": "00fv6g7rptsov009",
        "emr_postgres_application_id": "00g0oddl52n83r09",
        "max_retries": 3,
        "file_size_threshold_mb": 100,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "lambda_timeout_seconds": 300,
        "emr_timeout_minutes": 10,
        "supervisor_arn": "arn:aws:bedrock-agentcore:us-east-1:260005718447:runtime/spark_supervisor_agent-EZPQeDGCjR"
    },
    "postgres": {
        "connections": [
            {
                "name": "aurora-prod",
                "secret_arn": "arn:aws:secretsmanager:us-east-1:260005718447:secret:spark/postgres/aurora-prod-ltLn9I",
                "description": "Production Aurora PostgreSQL 16.8",
                "enabled": True
            }
        ],
        "default_connection": "aurora-prod",
        "jdbc_driver_path": "s3://spark-data-260005718447-us-east-1/jars/postgresql-42.7.8.jar",
        "secrets_manager_prefix": "spark/postgres/",
        "connection_timeout": 10,
        "query_timeout": 30,
        "use_dedicated_emr": True
    }
}

def load_config():
    """Load configuration from file or return defaults"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
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
        # Merge YAML ray config with default ray config
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
