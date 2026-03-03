#!/usr/bin/env python3
"""Deploy Supervisor Agent from backend folder"""

from bedrock_agentcore.deployment import runtime

if __name__ == "__main__":
    print("🚀 Deploying Supervisor Agent from backend")
    print("   Entrypoint: supervisor_agents.py")
    print("   Config: .bedrock_agentcore_supervisor.yaml")
    print("   Requirements: requirements_supervisor.txt")
    
    # Load and deploy
    rt = runtime.load(
        entrypoint="supervisor_agents.py",
        config_path=".bedrock_agentcore_supervisor.yaml"
    )
    rt.launch()
