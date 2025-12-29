#!/usr/bin/env python3
"""Deploy Supervisor Agent from backend folder"""

from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session

if __name__ == "__main__":
    print("🚀 Deploying Ray Supervisor Agent from backend")
    print("   Entrypoint: supervisor_agents.py")
    print("   Config: .bedrock_agentcore_supervisor.yaml")
    print("   Requirements: requirements_supervisor.txt")
    
    boto_session = Session()
    region = boto_session.region_name
    
    agentcore_runtime = Runtime()
    agent_name = "supervisor_agent"
    
    response = agentcore_runtime.configure(
        entrypoint="supervisor_agents.py",
        auto_create_execution_role=True,
        auto_create_ecr=True,
        requirements_file="requirements_supervisor.txt",
        region=region,
        agent_name=agent_name
    )
    
    print("Configuration response:")
    print(response)
    
    launch_result = agentcore_runtime.launch(auto_update_on_conflict=True)
    
    print("\nLaunch result:")
    print(launch_result)
    
    # Extract and display the ARN
    agent_arn = launch_result.agent_arn if hasattr(launch_result, 'agent_arn') else None
    
    if agent_arn:
        print(f"\n✅ Ray Supervisor Agent deployed successfully!")
        print(f"ARN: {agent_arn}")
        print(f"\n📋 Save this ARN for updating your CloudFormation stack!")
    else:
        print("\n⚠️ Could not retrieve agent ARN")
