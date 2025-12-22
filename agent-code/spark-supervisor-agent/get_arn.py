from bedrock_agentcore_starter_toolkit import Runtime

runtime = Runtime()
runtime.configure(
    entrypoint="spark_supervisor_agent.py",
    auto_create_execution_role=True,
    auto_create_ecr=True,
    requirements_file="requirements.txt",
    region="us-east-1",
    agent_name="spark_supervisor_agent"
)

status = runtime.status()
if status.endpoint:
    arn = status.endpoint.get('arn', '')
    print(f"\nSpark Supervisor Agent ARN:")
    print(arn)
    print(f"\nUpdate backend/main.py with:")
    print(f"SPARK_SUPERVISOR_ARN = '{arn}'")
else:
    print("Agent not deployed yet")
