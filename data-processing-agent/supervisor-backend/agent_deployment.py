from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session
boto_session = Session()
region = boto_session.region_name

agentcore_runtime = Runtime()
agent_name = "supervisor_agent"
response = agentcore_runtime.configure(
    entrypoint="supervisor_agents.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region=region,
    agent_name=agent_name
)
response

launch_result = agentcore_runtime.launch()

print(launch_result)
