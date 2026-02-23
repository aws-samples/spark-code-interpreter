#!/bin/bash

echo "🚀 Deploying Spark Supervisor Agent to AgentCore Runtime..."

cd "$(dirname "$0")"

# Deploy using bedrock-agentcore CLI
bedrock-agentcore deploy

echo "✅ Deployment complete!"
echo "📝 Update SPARK_SUPERVISOR_ARN in backend/main.py with the ARN from deployment output"
