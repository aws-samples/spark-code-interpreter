#!/bin/bash
# Deploy Supervisor Agent from backend folder

echo "🚀 Deploying Supervisor Agent from backend"
echo "   Entrypoint: supervisor_agents.py"
echo "   Config: .bedrock_agentcore_supervisor.yaml"
echo "   Requirements: requirements_supervisor.txt"

cd "$(dirname "$0")"

# Deploy using agentcore CLI
agentcore launch --config .bedrock_agentcore_supervisor.yaml
