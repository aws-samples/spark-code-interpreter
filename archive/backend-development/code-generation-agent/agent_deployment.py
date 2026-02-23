from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import load_config, save_config

boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "ray_code_interpreter"
response = agentcore_runtime.configure(
    entrypoint="agents.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)
response

launch_result = agentcore_runtime.launch()

print(launch_result)

# Update config with the deployed ARN
if hasattr(launch_result, 'agent_arn') and launch_result.agent_arn:
    config = load_config()
    if 'global' not in config:
        config['global'] = {}
    config['global']['code_gen_agent_arn'] = launch_result.agent_arn
    save_config(config)
    print(f"✅ Updated config with Code Generation Agent ARN: {launch_result.agent_arn}")
else:
    print("⚠️ Could not extract agent ARN from launch result")