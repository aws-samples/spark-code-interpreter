import json
import os
import yaml
from pathlib import Path

CONFIG_FILE = Path(__file__).parent / "settings.json"
YAML_CONFIG_FILE = Path(__file__).parent.parent / "config.yaml"

DEFAULT_CONFIG = {
    "ray_cluster": {
        "private_ip": os.getenv("RAY_PRIVATE_IP", ""),
        "public_ip": os.getenv("RAY_PUBLIC_IP", "")
    },
    "s3": {
        "bucket": os.getenv("DATA_BUCKET", "")
    },
    "ray": {
        "gateway_url": os.getenv("RAY_GATEWAY_URL", ""),
        "supervisor_arn": os.getenv("RAY_SUPERVISOR_ARN", "")
    },
    "global": {
        "bedrock_model": os.getenv("BEDROCK_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0"),
        "code_gen_agent_arn": os.getenv("RAY_CODE_GEN_AGENT_ARN", ""),
        "bedrock_region": os.getenv("AWS_DEFAULT_REGION", "us-west-2")
    },
    "spark": {
        "s3_bucket": os.getenv("DATA_BUCKET", ""),
        "lambda_function": os.getenv("SPARK_LAMBDA_FUNCTION", ""),
        "emr_application_id": os.getenv("EMR_APPLICATION_ID", ""),
        "emr_postgres_application_id": os.getenv("EMR_POSTGRES_APPLICATION_ID", ""),
        "max_retries": 3,
        "file_size_threshold_mb": 100,
        "result_preview_rows": 100,
        "presigned_url_expiry_hours": 24,
        "lambda_timeout_seconds": 300,
        "emr_timeout_minutes": 10,
        "supervisor_arn": os.getenv("SPARK_SUPERVISOR_ARN", "")
    },
    "postgres": {
        "connections": [],
        "default_connection": None,
        "jdbc_driver_path": "",
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
