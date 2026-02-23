from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from config import load_config, save_config

boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "spark_supervisor_agent"

response = agentcore_runtime.configure(
    entrypoint="spark_supervisor_agent.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)

print("Configuration response:")
print(response)

launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)

print("\nLaunch result:")
print(launch_result)

# Update config with the deployed ARN
agent_arn = launch_result.agent_arn if hasattr(launch_result, 'agent_arn') else None

if agent_arn:
    config = load_config()
    if 'spark' not in config:
        config['spark'] = {}
    config['spark']['supervisor_arn'] = agent_arn
    save_config(config)
    print(f"\n✅ Spark Supervisor Agent deployed successfully!")
    print(f"ARN: {agent_arn}")
    print(f"✅ Updated config with Spark supervisor ARN: {agent_arn}")
else:
    print("\n⚠️ Could not retrieve agent ARN")
